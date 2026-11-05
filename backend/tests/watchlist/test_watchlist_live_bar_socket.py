"""/ws/watchlist-live-bars: the live daily bar of each watchlist instrument. Real PostgreSQL and the IBKR fake.

The table change feed of the Web process runs in the lifespan, so these tests call `receive` themselves after a
watchlist change. The fake updates its current daily bar (2026-01-02) a few times each second.
"""

import json
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import anyio
import httpx
import psycopg
import pytest
from fastapi import FastAPI
from httpx_ws import AsyncWebSocketSession, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from atrade.foundation.instrument import Instrument
from atrade.foundation.table_changes import TableChangeFeed
from atrade.market_data import LiveDailyBarHub
from atrade.watchlist import create_watchlist_live_bar_router
from tests.fakes.ibkr import FakeGatewayConnection

SOCKET_PATH = "/ws/watchlist-live-bars"
TENCENT = Instrument(symbol="700", exchange="SEHK", currency="HKD")
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
WAIT_SECONDS = 5
# The send interval of the tests: short, so that the tests do not wait.
SEND_INTERVAL_SECONDS = 0.05
DAILY_BAR_TIME = int(datetime(2026, 1, 2, tzinfo=UTC).timestamp())

type JsonObject = dict[str, Any]


def make_connected_gateway() -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    gateway_connection.connected = True
    return gateway_connection


@asynccontextmanager
async def open_live_bar_socket(
    database_url: str, feed: TableChangeFeed, hub: LiveDailyBarHub
) -> AsyncGenerator[AsyncWebSocketSession]:
    app = FastAPI()
    app.include_router(
        create_watchlist_live_bar_router(
            database_url=database_url,
            table_change_feed=feed,
            live_daily_bar_hub=hub,
            send_interval_seconds=SEND_INTERVAL_SECONDS,
        )
    )
    async with (
        httpx.AsyncClient(transport=ASGIWebSocketTransport(app=app), base_url="http://test") as client,
        aconnect_ws(SOCKET_PATH, client) as socket,
    ):
        yield socket
    hub.stop()


async def receive_until(socket: AsyncWebSocketSession, condition: Callable[[dict[str, Any]], bool]) -> JsonObject:
    """Merges the live bars of the messages by symbol until `condition` is true for the merged live bars."""
    live_bars: dict[str, Any] = {}
    with anyio.fail_after(WAIT_SECONDS):
        while not condition(live_bars):
            message: JsonObject = json.loads(await socket.receive_text())
            assert message["type"] in {"live_bars", "heartbeat"}
            for live_bar in message.get("live_bars", []):
                live_bars[live_bar["symbol"]] = live_bar
    return live_bars


def has_bars(*symbols: str) -> Callable[[dict[str, Any]], bool]:
    return lambda live_bars: all(live_bars.get(symbol, {}).get("bar") is not None for symbol in symbols)


async def wait_for_stream_count(gateway_connection: FakeGatewayConnection, count: int) -> None:
    with anyio.fail_after(WAIT_SECONDS):
        while gateway_connection.active_live_bar_stream_count != count:
            await anyio.sleep(0.01)


def add_instruments(database_url: str, instruments: list[Instrument]) -> list[int]:
    with psycopg.connect(database_url, autocommit=True) as connection:
        rows = [
            connection.execute(
                """
                INSERT INTO watchlist_instrument (symbol, exchange, currency, added_at_utc)
                VALUES (%(symbol)s, %(exchange)s, %(currency)s, now()) RETURNING id
                """,
                {"symbol": instrument.symbol, "exchange": instrument.exchange, "currency": instrument.currency},
            ).fetchone()
            for instrument in instruments
        ]
    return [int(row[0]) for row in rows if row is not None]


def delete_instrument(database_url: str, watchlist_instrument_id: int) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("DELETE FROM watchlist_instrument WHERE id = %(id)s", {"id": watchlist_instrument_id})


@pytest.mark.anyio
async def test_pushes_the_live_daily_bar_of_each_watchlist_instrument(database_url: str) -> None:
    add_instruments(database_url, [TENCENT, APPLE])
    gateway_connection = make_connected_gateway()

    async with open_live_bar_socket(
        database_url, TableChangeFeed(database_url), LiveDailyBarHub(gateway_connection)
    ) as socket:
        live_bars = await receive_until(socket, has_bars("700", "AAPL"))

    tencent = live_bars["700"]
    assert {key: tencent[key] for key in ("symbol", "exchange", "currency")} == {
        "symbol": "700",
        "exchange": "SEHK",
        "currency": "HKD",
    }
    assert tencent["bar"]["time"] == DAILY_BAR_TIME
    assert {subscription.instrument for subscription in gateway_connection.live_bar_subscriptions} == {
        TENCENT,
        APPLE,
    }


@pytest.mark.anyio
async def test_follows_the_watchlist_changes(database_url: str) -> None:
    tencent_id, _apple_id = add_instruments(database_url, [TENCENT, APPLE])
    gateway_connection = make_connected_gateway()
    feed = TableChangeFeed(database_url)
    hub = LiveDailyBarHub(gateway_connection, release_delay_seconds=0)

    async with open_live_bar_socket(database_url, feed, hub) as socket:
        await receive_until(socket, has_bars("700", "AAPL"))
        delete_instrument(database_url, tencent_id)
        feed.receive("watchlist_instrument")
        live_bars = await receive_until(socket, lambda bars: "700" in bars and bars["700"]["bar"] is None)
        await wait_for_stream_count(gateway_connection, 1)

        alibaba = Instrument(symbol="9988", exchange="SEHK", currency="HKD")
        add_instruments(database_url, [alibaba])
        feed.receive("watchlist_instrument")
        await receive_until(socket, has_bars("9988"))

    assert live_bars["700"]["bar"] is None
    # The streams end when the browser leaves (release delay 0).
    await wait_for_stream_count(gateway_connection, 0)


@pytest.mark.anyio
async def test_sends_no_live_bar_and_no_error_without_ib_gateway(database_url: str) -> None:
    add_instruments(database_url, [TENCENT])
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])

    async with open_live_bar_socket(
        database_url, TableChangeFeed(database_url), LiveDailyBarHub(gateway_connection)
    ) as socket:
        live_bars = await receive_until(socket, lambda bars: "700" in bars)

    assert live_bars["700"]["bar"] is None
