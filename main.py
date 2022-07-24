from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import os
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from dataclasses import dataclass
import uuid
from typing import List, Dict
from datetime import datetime


@dataclass
class Message:
    text: str
    timestamp: int = int(datetime.timestamp(datetime.now()) * 1000)


class ChatSession:
    def __init__(self):
        self.online_users: Dict[str, WebSocket] = dict()
        self.messages: List[Message] = list()

    def connect(self, user_id: str, websocket: WebSocket):
        self.online_users[user_id] = websocket
        print(self.online_users.keys())

    async def send_message(self, message: Dict):
        self.messages.append(Message(message.get("text")))
        for user_socket in self.online_users.values():
            await user_socket.send_json(message)

    def disconnect(self, user_id: str):
        self.online_users.pop(user_id)


def get_application():
    _app = FastAPI(title="Simple Chat", debug=True)

    if not os.path.exists("static"):
        os.makedirs("static")

    _app.mount("/static", StaticFiles(directory="static"), name="static")

    return _app


app = get_application()
templates = Jinja2Templates(directory="templates")
session = ChatSession()


@app.get("/", response_class=HTMLResponse)
def index_route(request: Request):
    def get_timestamp(element):
        return element.timestamp

    messages = sorted(session.messages, reverse=True, key=get_timestamp)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "messages": messages,
        },
    )


@app.websocket("/ws/chat")
async def websocket_route(websocket: WebSocket):
    await websocket.accept()
    user_id = str(uuid.uuid4())
    session.connect(user_id, websocket)
    try:
        while True:
            received_text = await websocket.receive_text()
            await session.send_message(
                {"text": received_text}
            )
    except WebSocketDisconnect:
        session.disconnect(user_id)
