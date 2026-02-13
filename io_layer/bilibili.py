import sys
import os
import threading
import asyncio
import time
from bilibili_api import Credential,live,sync
from config import *
from GPTSOVITS import *
from ASR import *
from sutitle_window import *
from subtitle_ws_server import start_ws_server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from CORE.AILLM import *
from CORE.character import *
from CORE.CAG import *

# 导入相关ID以及charactercag
charactercag = characterCAG(r"knowledge\Personal\YZL.txt")
"""打印charactercag的相关内容，确定是否导入成功"""
print(charactercag.character_name)
print(charactercag.plan_style)

# 导入相关ID以及CAG
CAG = sentenceSimilarityTest(model="BAAI/bge-small-zh-v1.5")
"""打印CAG的相关内容，确定是否导入成功"""
print(CAG.model)
print(CAG.similarity_threshold)
print(CAG.cache_size)
print(CAG.ttl_hours)

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
    hit, response, sim_score = CAG.query_cache(msg)
    if hit:
        print(f"命中缓存: {response}")
        TTS_text = response
        await speak_streaming(TTS_text)
    else:
        LLM_text = await get_response(prompt = "活力十足的16岁女高中生，乐正集团的大小姐。个性活泼元气，一天中有很多时间都在跑来跑去。喜欢音乐和巨大的好捏的毛绒绒的东西。在自己组建的乐队中担当主唱、吉他，兼职作曲，与洛天依是很好的朋友，喜欢在一起玩耍、喜欢和天依一起唱歌。",text = msg)
        print(LLM_text)
        if "喜欢" or "记得我" in msg:
            charactercag.memory.add_memory(content=f"{user}说：{msg}",users=user,importance=0.9)
        if user:
            TTS_text = await charactercag.apply_personal(user_input= msg , LLM_input= LLM_text,user_name=user)
            CAG.add(msg,TTS_text)
            #打印输出
            print (TTS_text)
            #播放TTS
            await speak_streaming(TTS_text)
        else :
            TTS_text = await charactercag.apply_personal(user_input= msg , LLM_input= LLM_text)
            CAG.add(msg,TTS_text)
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

if __name__ == "__main__":

    # 🌐 WebSocket 服务器（必须先启动）
    threading.Thread(
        target=start_ws_server,
        daemon=True
    ).start()
    time.sleep(1)  # 等待WS服务器启动

    # 🔊 ASR
    threading.Thread(
        target=start_asr,
        daemon=True
    ).start()

    # 🪟 实时字幕（WebSocket）
    threading.Thread(
        target=start_subtitle,
        daemon=True
    ).start()

    # 📺 B站弹幕
    threading.Thread(
        target=start_bili,
        daemon=True
    ).start()

    print("✅ 系统已启动")
    print("   WebSocket 服务器运行中 (ws://0.0.0.0:8765)")
    print("   ASR 监听中")
    print("   💬 B站弹幕监听中")
    print("   📝 WebSocket 实时字幕运行中")
    print("   Ctrl+C 退出")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 系统已安全退出")