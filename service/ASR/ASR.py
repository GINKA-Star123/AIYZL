from faster_whisper import WhisperModel
from webrtcvad import Vad
import numpy as np
import pyaudio
import logging
import torch
import time

import sys
import os
# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from service.TTS.GPTSOVITS import *
from service.OBS.sutitle_window import *

from agent.LLM.AILLM import *
from character.character import *
from memory.memory import MemoryManager

class OptimizedASR:
    """
    OptimizedASR : 修复版流式语音识别系统
    关键修复: 音频缓冲区管理 + 状态机 + 中文优化
    """

    def __init__(self, 
                 model_size="medium",    # 必须为medium
                 compute_type="int8",    # 必须INT8量化
                 sample_rate=16000,      # 16kHz标准采样率
                 vad_mode=3,             # VAD敏感度(3=最高)
                 silence_duration=0.8,
                 memory_file = r'knowledge\Personal\memory.json'):  # 0.8秒静音判定（中文优化）
                
        #硬件检测
        self._hardware_check()

        #配置VAD参数
        self.sample_rate = sample_rate
        self.silence_duration = silence_duration
        self.chunk_size = int(0.03 * sample_rate)  # 30ms
        self.vad = Vad(vad_mode)
        
        #显存保护设置
        self.max_gpu_memory = 3.5*1024**3  # 3.5GB
        self.last_cleanup = 0

        # 状态管理
        self.is_listening = False
        self.audio_buffer = []
        self.last_speech_time = 0
        self.speech_start_time = 0
        
        # 音频缓冲区限制
        self.max_buffer_size = sample_rate * 10  # 10秒最大缓冲
        

       
        #初始化Faster Whisper模型
        logging.info("正在初始化ASR模型")
        try:
            # 🔥 修复: 确保模型目录存在
            model_root = "data/models/faster-whisper"
            os.makedirs(model_root, exist_ok=True)
            
            self.model = WhisperModel(
                model_size,
                device="cuda",
                compute_type=compute_type,
                cpu_threads=12,
                num_workers=4,
                download_root=model_root
            )
        except Exception as e:
            logging.error(f"ASR模型初始化失败: {e}")
            raise e
        logging.info("ASR模型初始化完成")
        logging.info(f"GPU显存:{torch.cuda.memory_allocated()/1024**3:.2f}GB")

        # 记忆管理器
        self.memory = MemoryManager(memory_file=memory_file)
        logging.info("记忆管理器初始化完成")

    def _hardware_check(self):
        """硬件检测函数"""
        #检查GPU可用性
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "无GPU"
        logging.info(f"检测到的GPU: {gpu_name}")
        #检查CUDA版本
        cuda_version = torch.version.cuda if torch.cuda.is_available() else "无CUDA"
        logging.info(f"CUDA版本: {cuda_version}")
        #检查显存
        total_mem = torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else 0
        logging.info(f"GPU总显存: {total_mem/1024**3:.2f}GB")
        
    def _memory_guard(self):
        """显存保护函数"""
        #定期清理显存
        current = torch.cuda.memory_allocated()
        if current > self.max_gpu_memory :
            logging.warning(f"⚠️ 显存超限! 当前: {current/1024**3:.1f}GB > 限制: 3.5GB")
            torch.cuda.empty_cache()
            self.last_cleanup = time.time()
            logging.info("已清理显存")
            return True
        return False
        
    def _is_speech(self, audio_chunk):
        """使用VAD检测音频块中是否有语音"""
        #强制转换为16位PCM格式
        if audio_chunk.dtype != np.int16:
            audio_chunk = (audio_chunk * 32767).astype(np.int16)
        rms = np.sqrt(np.mean(np.square(audio_chunk.astype(np.float32))))
        if rms < 0.008:  # 静音阈值
            return False
        # 仅当块大小匹配时使用WebRTC VAD
        chunk_len = len(audio_chunk)
        if chunk_len in [480, 960, 1440]:
            return self.vad.is_speech(audio_chunk.tobytes(), self.sample_rate)
        return True

    #处理累积的音频缓冲区
    def transcribe_buffer(self, audio_buffer):
        """处理累积的完整音频缓冲区"""
        if not audio_buffer:
            return ""
        
        # 1. 合并音频数据
        audio_data = np.concatenate(audio_buffer)
        audio_duration = len(audio_data) / self.sample_rate
        
        # 2. 长度过滤
        if audio_duration < 0.4:  # 400ms最小（中文优化）
            logging.warning(f"⚠️ 音频过短 ({audio_duration:.2f}s < 0.4s)，跳过识别")
            return ""
        
        # 3. 显存保护
        if time.time() - self.last_cleanup > 0.2:
            self._memory_guard()
        
        logging.info(f"🎤 处理有效语音: {audio_duration:.2f}s")
        
        # 4. 语音识别
        try:
            segments, info = self.model.transcribe(
                audio_data.astype(np.float32)/32768.0, #归一化到[-1,1]
                beam_size=4, #beam search
                language="zh", #强制中文识别
                condition_on_previous_text=False, #上下文不关联
                without_timestamps=True, #不需要时间戳
                temperature=0.0, #确定性输出
                vad_filter=True, #启用内置VAD
                vad_parameters=dict(
                    threshold=0.35,  # 降低阈值（中文优化）
                    min_silence_duration_ms=600,  # 600ms静音
                    min_speech_duration_ms=250,  # 250ms最小语音
                    max_speech_duration_s=30.0,  # 30秒最大
                )
            )
            
            # 5. 拼接结果文本
            text = " ".join([segment.text for segment in segments]).strip()
            
            # 6. 内容过滤
            if len(text) < 2:  # 过滤单字结果
                logging.info(f"🗑️ 识别结果过短: '{text}'，丢弃")
                return ""
            
            elapsed = time.time() - self.speech_start_time
            logging.info(f"✅ 识别完成: '{text}' (时长: {audio_duration:.2f}s, 用时: {elapsed:.2f}s)")
            return text
            
        except Exception as e:
            logging.error(f"❌ 识别出错: {e}")
            torch.cuda.empty_cache()
            return ""

    def start_listening(self):
        """开始监听语音"""
        self.is_listening = True
        self.audio_buffer = []
        self.speech_start_time = time.time()
        logging.info("🎧 开始监听语音...")

    def stop_listening(self):
        """停止监听并处理缓冲区"""
        self.is_listening = False
        if self.audio_buffer:
            result = self.transcribe_buffer(self.audio_buffer.copy())
            self.audio_buffer = []
            return result
        return ""

    def process_audio_chunk(self, audio_chunk):
        """
        处理单个音频块，返回识别结果（如果有）
        :return: 识别结果 or None（无结果）
        """
        current_time = time.time()
        
        # 1. VAD检测
        is_speech = self._is_speech(audio_chunk)
        
        # 2. 语音活动处理
        if is_speech:
            # 首次检测到语音
            if not self.audio_buffer:
                self.speech_start_time = current_time
                logging.debug("🗣️ 语音开始")
            
            self.audio_buffer.append(audio_chunk)
            self.last_speech_time = current_time
            
            # 防止缓冲区溢出
            if len(self.audio_buffer) * self.chunk_size > self.max_buffer_size:
                self.audio_buffer = self.audio_buffer[-int(self.max_buffer_size/self.chunk_size):]
                logging.warning("⚠️ 音频缓冲区溢出，保留最近数据")
        
        # 3. 静音检测
        elif self.audio_buffer:
            silence_duration = current_time - self.last_speech_time
            
            if silence_duration > self.silence_duration:
                logging.info(f"⏹️ 语音结束 (静音: {silence_duration:.2f}s)")
                result = self.transcribe_buffer(self.audio_buffer.copy())
                self.audio_buffer = []
                return result
        
        # 4. 超时保护 (8秒)
        if self.audio_buffer and (current_time - self.speech_start_time) > 8.0:
            logging.warning("⏰ 语音超时 (8秒)，强制结束")
            result = self.transcribe_buffer(self.audio_buffer.copy())
            self.audio_buffer = []
            return result
        
        return None

    def transcribe_file(self, file_path):
        """
        识别音频文件（测试用）
        :param file_path: WAV/MP3文件路径
        :return: 识别结果字符串
        """
        segments, info = self.model.transcribe(
            file_path,
            beam_size=4,
            language="zh",
            without_timestamps=True,
        )
        text = "".join([segment.text for segment in segments]).strip()
        return text

    def benchmark(self, duration=10.0):
        """
        硬件基准测试
        :param duration: 测试时长（秒）
        """
        logging.info("开始硬件基准测试")

        #生成随机音频数据
        sample_rate = 16000
        t = np.linspace(0, duration, int(sample_rate*duration))
        audio = (np.sin(2*np.pi*1000*t)*32767).astype(np.int16)

        #分块模拟流式输入
        chunk_size = self.chunk_size
        chunks = [audio[i:i+chunk_size] for i in range(0, len(audio), chunk_size)]

        start_time = time.time()

        # 模拟实时语音输入
        self.start_listening()
        result = ""
        
        for chunk in chunks:
            # 模拟语音段
            if 1.0 <= (time.time() - start_time) <= 3.5:
                res = self.process_audio_chunk(chunk)
                if res:
                    result += res + " "
            time.sleep(0.001)  # 模拟实时流延迟
        
        # 强制处理剩余缓冲区
        result += self.stop_listening() or ""
        
        total_time = time.time() - start_time

        gpu_mem = torch.cuda.memory_allocated()/1024**3
        logging.info(f"📊 基准测试结果:")
        logging.info(f"   - 处理时长: {duration:.1f}s 音频")
        logging.info(f"   - 总耗时: {total_time:.2f}s (RTF: {total_time/duration:.2f})")
        logging.info(f"   - GPU显存峰值: {gpu_mem:.1f}GB")
        logging.info(f"  识别结果: '{result}'")
    
    def should_store_memory(self, text: str) -> bool:
        """判断是否应将识别结果存入记忆"""
        keywords = ["喜欢", "记得我", "重要", "告诉你", "分享"]
        for kw in keywords:
            if kw in text:
                return True
        return False

    def close(self):
        """释放资源"""
        logging.info("正在释放ASR资源")
        if hasattr(self, 'model'):
            del self.model
        torch.cuda.empty_cache()
        logging.info("ASR资源已释放")

# === 使用案例 ===
if __name__ == "__main__":
    # 1.配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    # 2.初始化ASR
    try:
        asr = OptimizedASR(
            model_size="medium",
            compute_type="int8",
            vad_mode=3,
            silence_duration=0.8  # 0.8秒静音（中文优化）
        )
    except Exception as e:
        logging.error(f"ASR初始化失败，退出程序: {e}")
        exit(1)
    
    # 3.运行基准测试(可选)
    asr.benchmark(duration=5.0)
    
    # 4. 配置音频流（麦克风输入）
    audio = pyaudio.PyAudio()
    
    #选择默认麦克风
    default_device = audio.get_default_input_device_info()
    logging.info(f"🎤 使用麦克风: {default_device['name']}")
    
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=asr.chunk_size,
        input_device_index=default_device['index']  # 使用默认设备 # type: ignore
    )

    logging.info("🔊 麦克风准备就绪，开始实时语音识别...")
    logging.info("   💡 请说话，停顿0.8秒后自动识别")
    logging.info("   💡 按 Ctrl+C 停止程序\n")

    # 5. 重构主循环 - 状态机驱动
    try:
        while True:
            # 5.1 从麦克风读取音频块
            data = stream.read(
                asr.chunk_size, 
                exception_on_overflow=False
            )
            audio_chunk = np.frombuffer(data, dtype=np.int16)
            
            # 5.2 处理音频块
            result = asr.process_audio_chunk(audio_chunk)
            
            # 5.3 处理识别结果
            if result:
                print(f"\n{'='*50}")
                print(f"🔤 识别结果: {result}")
                print(f"{'='*50}\n")
            
            # 5.4 降低CPU占用
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        logging.info("\n🛑 停止语音识别")
        
        # 5.5 处理剩余缓冲区
        final_result = asr.stop_listening()
        if final_result:
            print(f"\n{'='*50}")
            print(f"🔤 最终识别结果: {final_result}")
            print(f"{'='*50}\n")
    finally:
        # 6.释放资源
        stream.stop_stream()
        stream.close()
        audio.terminate()
        asr.close()
        logging.info("👋 程序已安全退出")

# 远程调用
async def get_asr_instance():
    # 导入相关ID以及CAG
    charactercag = characterCAG(r"knowledge\Personal\YZL.txt")

     # 1.配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    # 2.初始化ASR
    try:
        asr = OptimizedASR(
            model_size="medium",
            compute_type="int8",
            vad_mode=3,
            silence_duration=0.8  # 0.8秒静音（中文优化）
        )
    except Exception as e:
        logging.error(f"ASR初始化失败，退出程序: {e}")
        exit(1)
    
    # 3.运行基准测试(可选)
    asr.benchmark(duration=5.0)
    
    # 4. 配置音频流（麦克风输入）
    audio = pyaudio.PyAudio()
    
    #选择默认麦克风
    default_device = audio.get_default_input_device_info()
    logging.info(f"🎤 使用麦克风: {default_device['name']}")
    
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=asr.chunk_size,
        input_device_index=default_device['index']  # 使用默认设备 # type: ignore
    )

    logging.info("🔊 麦克风准备就绪，开始实时语音识别...")
    logging.info("   💡 请说话，停顿0.8秒后自动识别")
    logging.info("   💡 按 Ctrl+C 停止程序\n")

    # 5. 重构主循环 - 状态机驱动
    try:
        while True:
            # 5.1 从麦克风读取音频块
            data = stream.read(
                asr.chunk_size, 
                exception_on_overflow=False
            )
            audio_chunk = np.frombuffer(data, dtype=np.int16)
            
            # 5.2 处理音频块
            result = asr.process_audio_chunk(audio_chunk)
            
            # 5.3 处理识别结果
            if result:
                text = result
                if asr.should_store_memory(text):
                    charactercag.memory.add_memory(
                    users="银花",
                    content=text,
                    importance=0.6
        )
                print(f"\n{'='*50}")
                print(f"🔤 识别结果: {result}")
                print(f"{'='*50}\n")
            
            # 5.4 降低CPU占用
            time.sleep(0.01)
            
            #5.5 将识别结果传给API生成回复
            msg = result
            if msg :

                LLM_text = await get_response(prompt = "活力十足的16岁女高中生，乐正集团的大小姐。个性活泼元气，一天中有很多时间都在跑来跑去。喜欢音乐和巨大的好捏的毛绒绒的东西。在自己组建的乐队中担当主唱、吉他，兼职作曲，与洛天依是很好的朋友，喜欢在一起玩耍、喜欢和天依一起唱歌。",text = msg)
                TTS_text = await charactercag.apply_personal(user_input= msg , LLM_input= LLM_text)
                #CAG.add(msg,TTS_text)
                print(msg,TTS_text)
                #打印输出
                print (TTS_text)
                #播放TTS
                await speak_streaming(TTS_text)
            else:
                continue
    except KeyboardInterrupt:
        logging.info("\n🛑 停止语音识别")
        
        # 5.5 处理剩余缓冲区
        final_result = asr.stop_listening()
        if final_result:
            print(f"\n{'='*50}")
            print(f"🔤 最终识别结果: {final_result}")
            print(f"{'='*50}\n")
    finally:
        # 6.释放资源
        stream.stop_stream()
        stream.close()
        audio.terminate()
        asr.close()
        logging.info("👋 程序已安全退出")
