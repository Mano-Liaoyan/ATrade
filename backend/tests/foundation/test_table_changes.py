"""foundation/table_changes: a change socket sends "changed" after a change of its tables, from any connection."""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import LiteralString

import anyio
import httpx
import psycopg
import pytest
from fastapi import FastAPI
from httpx_ws import AsyncWebSocketSession, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from atrade.backtest import BACKTEST_CHANGE_SOCKET, SWEEP_CHANGE_SOCKET
from atrade.forward_test import FORWARD_TEST_CHANGE_SOCKET
from atrade.foundation.table_changes import ChangeSocket, TableChangeFeed, create_change_socket_router
from atrade.market_data import CUSTOM_INDICATOR_CHANGE_SOCKET
from atrade.screen import SCREEN_CHANGE_SOCKET
from atrade.strategy import STRATEGY_CHANGE_SOCKET
from atrade.watchlist import WATCHLIST_CHANGE_SOCKET

SHORT_HEARTBEAT_SECONDS = 0.5
MESSAGE_WAIT_SECONDS = 5
TEST_SOCKET = ChangeSocket(path="/ws/test", tables=frozenset({"watchlist_instrument"}))
APP_CHANGE_SOCKETS = [
    BACKTEST_CHANGE_SOCKET,
    SWEEP_CHANGE_SOCKET,
    STRATEGY_CHANGE_SOCKET,
    SCREEN_CHANGE_SOCKET,
    CUSTOM_INDICATOR_CHANGE_SOCKET,
    WATCHLIST_CHANGE_SOCKET,
    FORWARD_TEST_CHANGE_SOCKET,
]
NEW_FILL: LiteralString = (
    "INSERT INTO owner_ledger_entry (owner_kind, entry_kind, time_utc, account, symbol, exchange, currency, "
    "quantity_change, price, cash_change, ibkr_execution_id) "
    "VALUES ('by_hand', 'fill', now(), 'DU1', 'AAPL', 'NASDAQ', 'USD', 1, 100, -100, 'E1')"
)


@asynccontextmanager
async def open_change_socket(
    database_url: str, change_socket: ChangeSocket = TEST_SOCKET
) -> AsyncGenerator[AsyncWebSocketSession]:
    """The socket opens before the feed listens. The first message ("changed" after LISTEN) shows that it listens."""
    feed = TableChangeFeed(database_url)
    app = FastAPI()
    app.include_router(
        create_change_socket_router(feed, [change_socket], heartbeat_interval_seconds=SHORT_HEARTBEAT_SECONDS)
    )
    async with (
        anyio.create_task_group() as task_group,
        httpx.AsyncClient(transport=ASGIWebSocketTransport(app=app), base_url="http://test") as client,
        aconnect_ws(change_socket.path, client) as socket,
    ):
        while not feed.signals:
            await anyio.sleep(0.01)
        task_group.start_soon(feed.keep_listening)
        await receive_changed(socket)
        yield socket
        task_group.cancel_scope.cancel()


async def receive_type(socket: AsyncWebSocketSession) -> str:
    with anyio.fail_after(MESSAGE_WAIT_SECONDS):
        return str(json.loads(await socket.receive_text())["type"])


async def receive_changed(socket: AsyncWebSocketSession) -> None:
    """A heartbeat can come first when the notification is slow."""
    with anyio.fail_after(MESSAGE_WAIT_SECONDS):
        while json.loads(await socket.receive_text())["type"] != "changed":
            pass


async def write_in_other_connection(database_url: str, statement: LiteralString) -> None:
    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as connection:
        await connection.execute(statement)


@pytest.mark.anyio
async def test_a_change_of_a_watched_table_sends_changed(database_url: str) -> None:
    async with open_change_socket(database_url) as socket:
        await write_in_other_connection(
            database_url,
            "INSERT INTO watchlist_instrument (symbol, exchange, currency, added_at_utc) "
            "VALUES ('AAPL', 'NASDAQ', 'USD', now())",
        )

        await receive_changed(socket)


@pytest.mark.anyio
async def test_a_new_owner_ledger_fill_sends_changed_on_the_forward_test_socket(database_url: str) -> None:
    async with open_change_socket(database_url, FORWARD_TEST_CHANGE_SOCKET) as socket:
        await write_in_other_connection(database_url, NEW_FILL)

        await receive_changed(socket)


@pytest.mark.anyio
async def test_a_fill_that_is_read_again_sends_only_the_heartbeat(database_url: str) -> None:
    await write_in_other_connection(database_url, NEW_FILL)
    async with open_change_socket(database_url, FORWARD_TEST_CHANGE_SOCKET) as socket:
        await write_in_other_connection(
            database_url, NEW_FILL + " ON CONFLICT (ibkr_execution_id) WHERE ibkr_execution_id IS NOT NULL DO NOTHING"
        )

        assert await receive_type(socket) == "heartbeat"


@pytest.mark.anyio
async def test_a_change_of_another_table_sends_only_the_heartbeat(database_url: str) -> None:
    async with open_change_socket(database_url) as socket:
        await write_in_other_connection(
            database_url,
            "INSERT INTO exchange_rate (currency, day_start_utc, usd_per_unit) VALUES ('HKD', now(), 0.128)",
        )

        assert await receive_type(socket) == "heartbeat"


@pytest.mark.anyio
async def test_each_table_of_a_change_socket_has_the_notify_trigger(database_url: str) -> None:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        cursor = await connection.execute(
            "SELECT event_object_table FROM information_schema.triggers WHERE trigger_name = 'notify_table_change'"
        )
        tables_with_trigger = {str(row[0]) for row in await cursor.fetchall()}

    watched_tables = {table for socket in APP_CHANGE_SOCKETS for table in socket.tables}
    assert watched_tables <= tables_with_trigger
