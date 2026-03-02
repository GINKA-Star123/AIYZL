import queue
import time
import asyncio
import websockets

SUBTITLE_FILE = "subtitle.txt"

subtitle_queue = queue.Queue()
ws_clients = set()  # 存储所有连接的OBS客户端

async def broadcast_subtitle(text):
    """广播字幕给所有连接的OBS客户端"""
    if not ws_clients:
        return
    
    # 同时发送给所有客户端
    tasks = []
    for ws in list(ws_clients):
        try:
            tasks.append(ws.send(text))
        except Exception as e:
            print(f"⚠️ 发送失败: {e}")
    
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def subtitle_writer():
    """监听队列并广播字幕 - 整个文本完全显示后才清空"""
    buffer = ""
    print("📝 字幕处理器已启动（监听队列）")

    while True:
        # 获取队列中的数据
        try:
            item = await asyncio.to_thread(subtitle_queue.get, timeout=1)
        except queue.Empty:
            continue
        
        if item is None:
            break

        text, duration = item

        # 检查终止信号
        if text == "__END__":
            # 整个文本已完全显示，现在才清空
            print(f"📝 完整文本显示完毕: '{buffer}'")
            await asyncio.sleep(1.5)  # 停留1.5秒让用户看清楚
            buffer = ""
            await broadcast_subtitle("")
            print("📝 字幕已清空")
            continue

        if not text.strip():
            continue

        chars = list(text)
        interval = max(duration / len(chars), 0.05) if len(chars) > 0 else 0.05

        # 逐字发送 - 不清空buffer，继续拼接
        print(f"📋 处理段落: '{text}'")
        for ch in chars:
            buffer += ch
            await broadcast_subtitle(buffer)
            await asyncio.sleep(interval)
        
        # 段落完毕但不清空，等待下一个段落或 __END__ 信号
        print(f"  ✓ 段落显示完毕，累积buffer: '{buffer}'")