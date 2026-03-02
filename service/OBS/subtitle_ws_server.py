import asyncio
import websockets
import json
from sutitle_window import ws_clients

# 外部可以通过 set_message_handler 注入一个 async 函数来处理收到的消息
message_handler = None

def set_message_handler(fn):
    global message_handler
    message_handler = fn


async def handler(websocket):
    """处理每个OBS客户端连接"""
    ws_clients.add(websocket)
    print(f"✅ OBS客户端已连接 (总数: {len(ws_clients)})")
    
    try:
        # 保持连接，等待数据
        async for msg in websocket:
            # 支持客户端向AIYZL发送消息（例如来自前端的弹幕）
            try:
                data = json.loads(msg)
            except Exception:
                data = msg

            # 如果外部注册了处理函数，则调用它（可用于让 AIYZL 产生回复）
            try:
                if message_handler and asyncio.iscoroutinefunction(message_handler):
                    # 如果处理函数接受 websocket 参数，则传入以便可以回写回复
                    try:
                        await message_handler(data, websocket)
                    except TypeError:
                        await message_handler(data)
            except Exception as e:
                print('subtitle_ws_server handler message processing error', e)
            # 否则忽略接收的数据（此 WS 主要用于推送字幕到 OBS）
            
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        ws_clients.discard(websocket)
        print(f"❌ OBS客户端已断开 (剩余: {len(ws_clients)})")


async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("🟢 Subtitle WebSocket 服务器运行中: ws://0.0.0.0:8765")
        print("   等待OBS客户端连接...")
        await asyncio.Future()  # run forever

def start_ws_server():
    """供外部调用的函数"""
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
