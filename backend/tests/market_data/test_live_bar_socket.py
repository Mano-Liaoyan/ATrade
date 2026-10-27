"""/ws/market-data: pushes the live bar of one instrument and one bar period, through the Web app and the IBKR fake.

The fake updates its current bar a few times each second (tests/fakes/ibkr.py). The clock is 2026-01-02 03:04:05 UTC.
"""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from httpx_ws import AsyncWebSocketSession, WebSocketDisconnect, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from atrade.app.web import create_web_app
from atrade.foundation.bar import BarPeriod
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, LiveBarSubscription

FIXED_NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
MESSAGE_WAIT_SECONDS = 5
TENCENT = Instrument(symbol="700", exchange="SEHK", currency="HKD")
# The fake keeps a subscription until the socket closes. The route ends it a short time after the browser leaves.
SUBSCRIPTION_END_WAIT_SECONDS = 2
POLICY_VIOLATION_CODE = 1008

type JsonObject = dict[str, Any]


def make_settings(frontend_build_dir: Path) -> Settings:
    return Settings(database_url="postgresql://unused/atrade", frontend_build_dir=frontend_build_dir)


def make_connected_gateway() -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    gateway_connection.connected = True
    return gateway_connection


def live_bar_path(instrument: Instrument, bar_period: str) -> str:
    return (
        f"/ws/market-data?symbol={instrument.symbol}&exchange={instrument.exchange}"
        f"&currency={instrument.currency}&bar_period={bar_period}"
    )


@asynccontextmanager
async def open_market_data_socket(
    frontend_build_dir: Path, gateway_connection: FakeGatewayConnection, path: str
) -> AsyncGenerator[AsyncWebSocketSession]:
    app = create_web_app(
        settings=make_settings(frontend_build_dir),
        clock=FixedClock(FIXED_NOW_UTC),
        gateway_connection=gateway_connection,
    )
    async with (
        httpx.AsyncClient(transport=ASGIWebSocketTransport(app=app), base_url="http://test") as client,
        aconnect_ws(path, client) as socket,
    ):
        yield socket


async def receive_message(socket: AsyncWebSocketSession) -> JsonObject:
    with anyio.fail_after(MESSAGE_WAIT_SECONDS):
        message: JsonObject = json.loads(await socket.receive_text())
        return message


@pytest.mark.anyio
async def test_pushes_updates_of_the_current_bar(frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway()

    async with open_market_data_socket(
        frontend_build_dir, gateway_connection, live_bar_path(TENCENT, "1-HOUR")
    ) as socket:
        first = await receive_message(socket)
        second = await receive_message(socket)

    # The current 1 hour bar starts at 03:00 UTC. The fake opens it at 100 + (step % 50).
    bar_start = int(datetime(2026, 1, 2, 3, tzinfo=UTC).timestamp())
    assert first == {
        "type": "bar",
        "bar": {"time": bar_start, "open": 123.0, "high": 125.0, "low": 122.0, "close": 123.0, "volume": 10.0},
    }
    assert second == {
        "type": "bar",
        "bar": {"time": bar_start, "open": 123.0, "high": 125.0, "low": 122.0, "close": 123.25, "volume": 20.0},
    }
    assert gateway_connection.live_bar_subscriptions == [LiveBarSubscription(TENCENT, BarPeriod.ONE_HOUR)]


@pytest.mark.anyio
async def test_ends_the_ibkr_subscription_when_the_browser_leaves(frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway()

    async with open_market_data_socket(
        frontend_build_dir, gateway_connection, live_bar_path(TENCENT, "1-DAY")
    ) as socket:
        await receive_message(socket)
        assert gateway_connection.active_live_bar_stream_count == 1

    with anyio.fail_after(SUBSCRIPTION_END_WAIT_SECONDS):
        while gateway_connection.active_live_bar_stream_count > 0:
            await anyio.sleep(0.01)


@pytest.mark.anyio
async def test_sends_an_error_and_closes_when_ib_gateway_is_not_reachable(frontend_build_dir: Path) -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])

    async with open_market_data_socket(
        frontend_build_dir, gateway_connection, live_bar_path(TENCENT, "1-DAY")
    ) as socket:
        message = await receive_message(socket)
        with pytest.raises(WebSocketDisconnect):
            await receive_message(socket)

    assert message == {
        "type": "error",
        "detail": "IB Gateway is not reachable at ib-gateway:4004. Live bars need IB Gateway.",
    }
    assert gateway_connection.live_bar_subscriptions == []


@pytest.mark.anyio
async def test_sends_an_error_and_closes_when_the_ibkr_subscription_fails(frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway()
    gateway_connection.live_bars_error_message = "No market data permissions for SEHK STK"

    async with open_market_data_socket(
        frontend_build_dir, gateway_connection, live_bar_path(TENCENT, "1-DAY")
    ) as socket:
        message = await receive_message(socket)
        with pytest.raises(WebSocketDisconnect):
            await receive_message(socket)

    assert message == {
        "type": "error",
        "detail": "Reading live bars from IB Gateway failed: No market data permissions for SEHK STK",
    }


def is_policy_violation(error: WebSocketDisconnect) -> bool:
    return error.code == POLICY_VIOLATION_CODE


@pytest.mark.anyio
async def test_refuses_an_unknown_bar_period(frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway()

    # The route refuses the socket before it accepts it, with the policy violation code.
    with pytest.RaisesGroup(pytest.RaisesExc(WebSocketDisconnect, check=is_policy_violation), flatten_subgroups=True):
        async with open_market_data_socket(
            frontend_build_dir, gateway_connection, live_bar_path(TENCENT, "2-WEEK")
        ) as socket:
            await receive_message(socket)

    assert gateway_connection.live_bar_subscriptions == []
