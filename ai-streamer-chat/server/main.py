import json
from fastapi import FastAPI, WebSocket,WebSocketDisconnect
from typing import List
import uvicorn

app = FastAPI()


# WebSocket 连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"用户连接: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"用户断开连接: {websocket.client}")
    
    async def broadcast(self, data:dict):
        msg = json.dumps(data)

        dead_connections = []

        for conn in self.active_connections:
            try:
                await conn.send_text(msg)
            except WebSocketDisconnect:
                print(f"用户断开连接: {conn.client}")
                dead_connections.append(conn)
        for d in dead_connections:
            self.disconnect(d)

manager = ConnectionManager()

#====== WebSocket聊天室 ====
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            print(f"收到消息: {data} 来自 {websocket.client}")

            if data["type"] == "chat":
                # 直接广播给所有连接的客户端
                user =data["user"]
                msg = data["msg"] 

                print(f"用户 {user} 发送消息: {msg}")

                await manager.broadcast({"type": "chat", "user": user, "msg": msg})

                # 这里可以调用 AI 模型生成回复，并广播回去
                # reply = generate_ai_reply(msg)
                # await manager.broadcast({"type": "reply", "user": "AI", "msg": reply})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000,reload=False,workers=1)