"""The table change feed and the /ws/ change sockets (docs/architecture.md section 13, "Live updates").

A PostgreSQL trigger sends a `table_change` notification with the table name after each statement that changes a
watched table (migration a3f9d2c7e514). So each writer is seen: the Web process, the backtest child process, the
forward-test worker, and the assistant port. The Web process listens on one connection and wakes each socket that
watches the table. The socket sends `{"type": "changed"}`, and the page reads the changed data again over HTTP.
Nothing reads on a timer: a socket without changes sends only its heartbeat.
"""

import logging
from collections.abc import Callable, Coroutine, Generator, Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal

import anyio
import psycopg
from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

from atrade.foundation.socket_push import HEARTBEAT_INTERVAL_SECONDS, HeartbeatMessage, serve_until_disconnect

NOTIFICATION_CHANNEL = "table_change"
RECONNECT_DELAY_SECONDS = 1.0

logger = logging.getLogger("atrade.table_changes")


class ChangedMessage(BaseModel):
    """A watched table of the socket changed. The page reads its data again."""

    type: Literal["changed"] = "changed"


# The messages of each change socket. The OpenAPI document adds their JSON Schema for the frontend types.
CHANGE_SOCKET_MESSAGE_MODELS: list[type[BaseModel]] = [ChangedMessage, HeartbeatMessage]


@dataclass(frozen=True)
class ChangeSocket:
    """The /ws/ path of a capability and the tables whose changes it pushes. Each table needs the trigger."""

    path: str
    tables: frozenset[str]


class ChangeSignal:
    """The changes of some tables for one socket. Changes before a wait are kept, so none is lost."""

    def __init__(self, tables: frozenset[str]) -> None:
        self.tables = tables
        self.event = anyio.Event()

    def set(self) -> None:
        self.event.set()

    async def wait(self) -> None:
        await self.event.wait()
        self.event = anyio.Event()


class TableChangeFeed:
    """One LISTEN connection of the Web process. `keep_listening` runs in the lifespan."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.signals: list[ChangeSignal] = []

    @contextmanager
    def subscribe(self, tables: frozenset[str]) -> Generator[ChangeSignal]:
        signal = ChangeSignal(tables)
        self.signals.append(signal)
        try:
            yield signal
        finally:
            self.signals.remove(signal)

    def receive(self, table: str | None) -> None:
        """`None`: all tables, because changes can be lost while the connection is lost."""
        for signal in self.signals:
            if table is None or table in signal.tables:
                signal.set()

    async def keep_listening(self) -> None:
        while True:
            try:
                async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
                    await connection.execute(f"LISTEN {NOTIFICATION_CHANNEL}")
                    self.receive(None)
                    async for notification in connection.notifies():
                        self.receive(notification.payload)
            except psycopg.OperationalError as error:
                logger.warning("The table change connection is lost. It connects again. %s", error)
            await anyio.sleep(RECONNECT_DELAY_SECONDS)


async def push_table_changes(
    websocket: WebSocket, feed: TableChangeFeed, tables: frozenset[str], heartbeat_interval_seconds: float
) -> None:
    with feed.subscribe(tables) as signal:
        while True:
            message: BaseModel = ChangedMessage()
            with anyio.move_on_after(heartbeat_interval_seconds) as wait_scope:
                await signal.wait()
            if wait_scope.cancelled_caught:
                message = HeartbeatMessage()
            await websocket.send_text(message.model_dump_json())


def create_change_socket_router(
    feed: TableChangeFeed,
    sockets: Iterable[ChangeSocket],
    *,
    heartbeat_interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS,
) -> APIRouter:
    router = APIRouter()

    def create_endpoint(tables: frozenset[str]) -> Callable[[WebSocket], Coroutine[Any, Any, None]]:
        async def stream_changes(websocket: WebSocket) -> None:
            await serve_until_disconnect(
                websocket, lambda: push_table_changes(websocket, feed, tables, heartbeat_interval_seconds)
            )

        return stream_changes

    for socket in sockets:
        router.add_api_websocket_route(socket.path, create_endpoint(socket.tables))
    return router
