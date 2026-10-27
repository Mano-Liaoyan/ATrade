"""Shared parts of the /ws/ routes that push messages to the browser (docs/architecture.md section 13).

Each socket sends a "heartbeat" message after a fixed time without another message, so that the browser can see a
dead connection and connect again. The browser sends nothing that the server needs.
"""

from collections.abc import Callable, Coroutine
from typing import Any, Literal

import anyio
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

HEARTBEAT_INTERVAL_SECONDS = 10.0


class HeartbeatMessage(BaseModel):
    type: Literal["heartbeat"] = "heartbeat"


class ChangedMessageSender:
    """Sends a message only when its text is different from the last sent message of the same model.

    `wait` sleeps and then sends a heartbeat when no message went out for the heartbeat interval.
    """

    def __init__(self, websocket: WebSocket, *, heartbeat_interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS) -> None:
        self.websocket = websocket
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.last_sent_texts: dict[type[BaseModel], str] = {}
        self.seconds_since_last_message = 0.0

    async def send_if_changed(self, message: BaseModel) -> None:
        text = message.model_dump_json()
        if self.last_sent_texts.get(type(message)) == text:
            return
        await self.websocket.send_text(text)
        self.last_sent_texts[type(message)] = text
        self.seconds_since_last_message = 0.0

    async def wait(self, seconds: float) -> None:
        await anyio.sleep(seconds)
        self.seconds_since_last_message += seconds
        if self.seconds_since_last_message >= self.heartbeat_interval_seconds:
            await self.websocket.send_text(HeartbeatMessage().model_dump_json())
            self.seconds_since_last_message = 0.0


async def wait_for_disconnect(websocket: WebSocket) -> None:
    """Reads the socket until the browser leaves."""
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


async def serve_until_disconnect(websocket: WebSocket, push: Callable[[], Coroutine[Any, Any, None]]) -> None:
    """Accepts the socket and runs `push` until the browser leaves."""
    await websocket.accept()
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(push)
        await wait_for_disconnect(websocket)
        task_group.cancel_scope.cancel()
