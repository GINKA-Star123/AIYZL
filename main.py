import threading
import asyncio
import time
import json
from bilibili_api import Credential,live,sync
from config import *

from service.TTS.GPTSOVITS import *
from service.ASR.ASR import *
#from service.OBS.sutitle_window import *
#from service.OBS.subtitle_ws_server import start_ws_server, set_message_handler
from agent.LLM.AILLM import *
from character.character import *

# 导入相关ID以及charactercag
charactercag = characterCAG(r"knowledge\Personal\YZL.txt")
"""打印charactercag的相关内容，确定是否导入成功"""
print(charactercag.character_name)
print(charactercag.plan_style)

# 导入相关ID以及CAG
#CAG = sentenceSimilarityTest(model="BAAI/bge-small-zh-v1.5")
#"""打印CAG的相关内容，确定是否导入成功"""
#print(CAG.model)
#print(CAG.similarity_threshold)
#print(CAG.cache_size)
#print(CAG.ttl_hours)

#直播设置方面
credential = Credential(sessdata=SESSDATA,bili_jct=bili_jct,buvid3=BUVID3)
room = live.LiveDanmaku(BILIBILI_ROOM_ID)

# 弹幕监听事件
@room.on("DANMU_MSG")
async def on_danmaku(event):
    #收到弹幕
    user = event["data"]["info"][2][1]
    msg = event["data"]["info"][1]
    print(f"用户{event["data"]["info"][2][1]}发送消息: {event["data"]["info"][1]}")
    start_time = time.time()
    # 查询缓存
    LLM_text = await get_response(prompt = "活力十足的16岁女高中生，乐正集团的大小姐。个性活泼元气，一天中有很多时间都在跑来跑去。喜欢音乐和巨大的好捏的毛绒绒的东西。在自己组建的乐队中担当主唱、吉他，兼职作曲，与洛天依是很好的朋友，喜欢在一起玩耍、喜欢和天依一起唱歌。",text = msg)
    print(LLM_text)
    if "喜欢" or "记得我" in msg:
        charactercag.memory.add_memory(content=f"{user}说：{msg}",users=user,importance=0.9)
    if user:
        TTS_text = await charactercag.apply_personal(user_input= msg , LLM_input= LLM_text,user_name=user)
        #CAG.add(msg,TTS_text)
        #打印输出
        print (TTS_text)
        #播放TTS
        await speak_streaming(TTS_text)
    else :
        TTS_text = await charactercag.apply_personal(user_input= msg , LLM_input= LLM_text)
        #CAG.add(msg,TTS_text)
        #打印输出
        print (TTS_text)
        #播放TTS
        await speak_streaming(TTS_text)
def start_asr():
    asyncio.run(get_asr_instance())

def start_bili():
    print("📡 B站弹幕监听已启动")
    sync(room.connect())

def start_subtitle():
    asyncio.run(subtitle_writer())


async def ws_incoming_handler(data, websocket=None):
    """处理来自前端或其它客户端通过 WS 发来的弹幕数据。
    期望格式: {"type":"danmaku", "user": "name", "msg": "文本"}
    如果 websocket 可用，会把 AI 的回复直接回写给发送方。"""
    try:
        if isinstance(data, dict) and data.get('type') == 'danmaku':
            user = data.get('user') or 'web'
            msg = data.get('msg') or data.get('text') or ''
        else:
            # 兼容纯文本或其他格式
            user = 'web'
            msg = data if isinstance(data, str) else str(data)

        if not msg or not str(msg).strip():
            return

        print(f"WS incoming danmaku from {user}: {msg}")

        LLM_text = await get_response(prompt = "活力十足的16岁女高中生，乐正集团的大小姐。个性活泼元气，一天中有很多时间都在跑来跑去。喜欢音乐和巨大的好捏的毛绒绒的东西。在自己组建的乐队中担当主唱、吉他，兼职作曲，与洛天依是很好的朋友，喜欢在一起玩耍、喜欢和天依一起唱歌。",text = msg)

        if "喜欢" or "记得我" in msg:
            charactercag.memory.add_memory(content=f"{user}说：{msg}",users=user,importance=0.9)

        if user:
            TTS_text = await charactercag.apply_personal(user_input= msg , LLM_input= LLM_text,user_name=user)
        else:
            TTS_text = await charactercag.apply_personal(user_input= msg , LLM_input= LLM_text)

        print('AI reply:', TTS_text)
        # 播放TTS
        await speak_streaming(TTS_text)

        # 若 websocket 可回写，则把回复发送回去，方便前端展示
        if websocket is not None:
            try:
                await websocket.send(json.dumps({'type': 'reply', 'reply': TTS_text}))
            except Exception as e:
                print('Failed to send reply over websocket', e)
    except Exception as e:
        print('ws_incoming_handler error', e)

if __name__ == "__main__":

    # 🌐 WebSocket 服务器（必须先启动）
    # threading.Thread(
    #     target=start_ws_server,
    #     daemon=True
    # ).start()
    # time.sleep(1)  # 等待WS服务器启动
    # # 注册 WS 消息处理器，让前端发送的弹幕能进入 AIYZL 的处理流程
    # try:
    #     set_message_handler(ws_incoming_handler)
    #     print('✅ WS message handler registered')
    # except Exception as e:
    #     print('⚠️ Failed to register WS handler', e)

    # 🔊 ASR
    threading.Thread(
        target=start_asr,
        daemon=True
    ).start()

    # # 🪟 实时字幕（WebSocket）
    # threading.Thread(
    #     target=start_subtitle,
    #     daemon=True
    # ).start()

    # 📺 B站弹幕
    threading.Thread(
        target=start_bili,
        daemon=True
    ).start()

    # 启动live2D模型
    #threading.Thread(
    #    target=start_live2d_display,
    #    daemon=True
    #).start()
    
    
    print("✅ 系统已启动")
    #print("   WebSocket 服务器运行中 (ws://0.0.0.0:8765)")
    print("   ASR 监听中")
    print("   💬 B站弹幕监听中")
    #print("   📝 WebSocket 实时字幕运行中")
    #print("   🕺 Live2D 模型运行中")
    print("   Ctrl+C 退出")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 系统已安全退出")