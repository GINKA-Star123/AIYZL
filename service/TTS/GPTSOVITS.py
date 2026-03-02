import time
import aiohttp
import pygame
import queue
import threading
import uuid
import re
from service.OBS.sutitle_window import *
import requests
import logging

def clean_text(text):
    # 去掉各种括号内容
    text = re.sub(r'（.*?）', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\{.*?\}', '', text)
    # 去除星号内容
    text = re.sub(r'\*.*?\*', '', text)
    return text.strip()

def split_text_streaming(text, max_length=60):
    """
    先按强语义标点切，再保证长度
    """
    strong_punc = "。！？!?"
    weak_punc = "，,；;"

    segments = []
    buf = ""

    for ch in text:
        buf += ch

        # 强标点，直接切
        if ch in strong_punc:
            segments.append(buf.strip())
            buf = ""
            continue

        # 弱标点 + 长度接近上限
        if ch in weak_punc and len(buf) >= max_length * 0.7:
            segments.append(buf.strip())
            buf = ""

        # 兜底：过长强制切（但尽量少发生）
        if len(buf) >= max_length:
            segments.append(buf.strip())
            buf = ""

    if buf.strip():
        segments.append(buf.strip())

    return segments


url = "http://127.0.0.1:9880/tts"

pygame.mixer.init()
audio_queue = queue.Queue()

def player_worker():
    while True:
        path = audio_queue.get()
        if path is None:
            break
        
        audio_path , subtitle = path    
        data = {
            "type": "speak",
            "speech_path": rf"F:\AIYZL\{audio_path}" # 修改为你的语音音频路径
        }
        print(audio_path)
        res = requests.post(url=url,json =data)
        logging.info(f"正在播放: {subtitle}")
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        
        #等待播放完
        while pygame.mixer.music.get_busy():
            time.sleep(0.01)
        time.sleep(0.3)  # 播放间隔

threading.Thread(target=player_worker, daemon=True).start()


async def tts_segment(text):
    text = clean_text(text)
    payload = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": r"F:\GPT_SoVITS\123.wav",
        "prompt_lang": "zh",
        "prompt_text": "既有大家都很熟悉的经典歌曲，也有为今天准备的全新舞台",
        "text_split_method": "cut0",
        "batch_size": 10,
        "media_type": "wav",
        "streaming_mode": False,
        "parallel_infer": False,
        "seed": -1,
        
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as r:
                if r.status != 200:
                    print("TTS 请求失败", await r.text())
                    return
            
                data = await r.read()

                # 避免同名覆盖
                path = f"{uuid.uuid4().hex}.wav"
                with open(path, "wb") as f:
                    f.write(data)
                
                sound = pygame.mixer.Sound(path)
                duration = sound.get_length()
                return path, duration
        except Exception as e:
            print(e,"请求在TTS中失败")
            
async def speak_streaming(text):
    text = clean_text(text)
    segments = split_text_streaming(text)

    for seg in segments:
        result = await tts_segment(seg) # type: ignore
        if result:  # 检查是否为None
            path, duration = result
            subtitle_queue.put((seg, duration))
            audio_queue.put((path, seg))
        else:
            print(f"⚠️ TTS 生成失败: {seg}")
    subtitle_queue.put(("__END__", 0))