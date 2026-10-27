"""foundation/socket_push: a /ws/ route sends each changed message once and a heartbeat when it has nothing new."""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Literal

import anyio
import httpx
import pytest
from fastapi import FastAPI, WebSocket
from httpx_ws import AsyncWebSocketSession, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from pydantic import BaseModel

from atrade.foundation.socket_push import ChangedMessageSender, HeartbeatMessage, serve_until_disconnect

SHORT_HEARTBEAT_SECONDS = 0.2
PUSH_INTERVAL_SECONDS = 0.05
MESSAGE_WAIT_SECONDS = 5


class CountMessage(BaseModel):
    type: Literal["count"] = "count"
    count: int


class NameMessage(BaseModel):
    type: Literal["name"] = "name"
    name: str


def make_app(counts: list[int]) -> FastAPI:
    """The route sends the counts in order, each one on a new push, and a fixed name message on every push."""
    app = FastAPI()

    @app.websocket("/ws/test")
    async def stream(websocket: WebSocket) -> None:  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        async def push() -> None:
            sender = ChangedMessageSender(websocket, heartbeat_interval_seconds=SHORT_HEARTBEAT_SECONDS)
            for count in counts:
                await sender.send_if_changed(CountMessage(count=count))
                await sender.send_if_changed(NameMessage(name="same"))
                await sender.wait(PUSH_INTERVAL_SECONDS)
            while True:
                await sender.wait(PUSH_INTERVAL_SECONDS)

        await serve_until_disconnect(websocket, push)

    return app


@asynccontextmanager
async def open_socket(app: FastAPI) -> AsyncGenerator[AsyncWebSocketSession]:
    async with (
        httpx.AsyncClient(transport=ASGIWebSocketTransport(app=app), base_url="http://test") as client,
        aconnect_ws("/ws/test", client) as socket,
    ):
        yield socket


async def receive_types(socket: AsyncWebSocketSession, number: int) -> list[str]:
    types: list[str] = []
    with anyio.fail_after(MESSAGE_WAIT_SECONDS):
        for _ in range(number):
            message = json.loads(await socket.receive_text())
            types.append(f"{message['type']}:{message.get('count', message.get('name', ''))}")
    return types


@pytest.mark.anyio
async def test_sends_each_changed_message_once_then_a_heartbeat() -> None:
    async with open_socket(make_app([1, 1, 2])) as socket:
        types = await receive_types(socket, 4)

    assert types == ["count:1", "name:same", "count:2", "heartbeat:"]


def test_heartbeat_message_has_the_type_heartbeat() -> None:
    assert HeartbeatMessage().model_dump_json() == '{"type":"heartbeat"}'
