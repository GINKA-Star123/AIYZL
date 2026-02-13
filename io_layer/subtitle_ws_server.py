import asyncio
import websockets
from sutitle_window import ws_clients


async def handler(websocket):
    """处理每个OBS客户端连接"""
    ws_clients.add(websocket)
    print(f"✅ OBS客户端已连接 (总数: {len(ws_clients)})")
    
    try:
        # 保持连接，等待数据
        async for _ in websocket:
            pass
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
