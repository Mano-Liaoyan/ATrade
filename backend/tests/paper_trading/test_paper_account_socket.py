"""/ws/paper-trading: the paper account check result, the balance, and the positions, through the Web app.

The Web process checks the paper account once after each connection (docs/architecture.md section 11.2).
"""

import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from httpx_ws import AsyncWebSocketSession, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from atrade.ibkr import AccountValue
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import (
    FakeGatewayConnection,
    make_balance_values,
    make_forward_test_order,
    make_stock_position,
)

ACCOUNT_ID = "DU1234567"
FIXED_NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
MESSAGE_WAIT_SECONDS = 5

type JsonObject = dict[str, Any]


def make_settings(database_url: str, frontend_build_dir: Path, *, ibkr_account_id: str | None = ACCOUNT_ID) -> Settings:
    return Settings(
        database_url=database_url,
        frontend_build_dir=frontend_build_dir,
        ibkr_account_id=ibkr_account_id,
    )


def make_connected_gateway(managed_accounts: list[str]) -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=managed_accounts)
    gateway_connection.connected = True
    return gateway_connection


@asynccontextmanager
async def open_paper_trading_socket(
    settings: Settings, gateway_connection: FakeGatewayConnection
) -> AsyncGenerator[AsyncWebSocketSession]:
    app = create_web_app(settings=settings, clock=FixedClock(FIXED_NOW_UTC), gateway_connection=gateway_connection)
    async with (
        httpx.AsyncClient(transport=ASGIWebSocketTransport(app=app), base_url="http://test") as client,
        aconnect_ws("/ws/paper-trading", client) as socket,
    ):
        yield socket


async def receive_account(socket: AsyncWebSocketSession) -> JsonObject:
    with anyio.fail_after(MESSAGE_WAIT_SECONDS):
        while True:
            message: JsonObject = json.loads(await socket.receive_text())
            if message["type"] == "account":
                return message


async def read_first_account(settings: Settings, gateway_connection: FakeGatewayConnection) -> JsonObject:
    async with open_paper_trading_socket(settings, gateway_connection) as socket:
        return await receive_account(socket)


@pytest.mark.anyio
async def test_pushes_balance_and_positions_after_a_passed_check(database_url: str, frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    gateway_connection.account_values = make_balance_values(
        ACCOUNT_ID, net_liquidation_usd="101234.50", cash_usd="25000.00"
    )
    gateway_connection.portfolio = [make_stock_position(ACCOUNT_ID, symbol="AAPL", quantity="10", market_price="200")]

    account = await read_first_account(make_settings(database_url, frontend_build_dir), gateway_connection)

    assert account["check"] == {
        "status": "passed",
        "message": None,
        "actual_accounts": [ACCOUNT_ID],
        "expected_account": ACCOUNT_ID,
    }
    assert account["balance"] == {
        "net_liquidation_usd": "101234.50",
        "cash_usd": "25000.00",
        "base_currency": "USD",
        "net_liquidation_base": "101234.50",
        "cash_base": "25000.00",
        "usd_per_base_unit": "1",
        "exchange_rate_source": "base_currency_is_usd",
        "message": None,
    }
    assert account["positions"] == [
        {
            "symbol": "AAPL",
            "security_type": "STK",
            "exchange": "NASDAQ",
            "currency": "USD",
            "quantity": "10",
            "average_cost": "200",
            "market_price": "200",
            "market_value": "2000",
            "unrealized_pnl": "0",
            "owners": [
                {"owner": {"kind": "by_hand", "forward_test_id": None}, "quantity": "10", "average_cost": "200"}
            ],
            "unattributed_quantity": "0",
        }
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("managed_accounts", "expected_account", "message_part"),
    [
        ([ACCOUNT_ID], None, "ATRADE_IBKR_ACCOUNT_ID is not set"),
        (["DU1234567", "DU7654321"], ACCOUNT_ID, "returned 2 accounts"),
        ([], ACCOUNT_ID, "returned 0 accounts"),
        (["DU7654321"], ACCOUNT_ID, "is not the expected account"),
        (["U1234567"], "U1234567", "does not start with DU"),
    ],
)
async def test_refuses_an_account_that_fails_the_check(
    database_url: str,
    frontend_build_dir: Path,
    managed_accounts: list[str],
    expected_account: str | None,
    message_part: str,
) -> None:
    gateway_connection = make_connected_gateway(managed_accounts)
    gateway_connection.account_values = make_balance_values("U1234567", net_liquidation_usd="1", cash_usd="1")

    account = await read_first_account(
        make_settings(database_url, frontend_build_dir, ibkr_account_id=expected_account), gateway_connection
    )

    assert account["check"]["status"] == "failed"
    assert message_part in account["check"]["message"]
    assert account["check"]["actual_accounts"] == managed_accounts
    assert account["check"]["expected_account"] == expected_account
    assert account["balance"] is None
    assert account["positions"] == []


@pytest.mark.anyio
async def test_refuses_a_connection_that_is_not_on_the_paper_port(database_url: str, frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    gateway_connection.port = 4001

    account = await read_first_account(make_settings(database_url, frontend_build_dir), gateway_connection)

    assert account["check"]["status"] == "failed"
    assert "port 4001" in account["check"]["message"]
    assert "paper port 4004" in account["check"]["message"]


@pytest.mark.anyio
async def test_refuses_a_trading_mode_that_is_not_paper(database_url: str, frontend_build_dir: Path) -> None:
    # Settings refuse "live" at start. A copy without validation shows that the check also refuses it.
    settings = make_settings(database_url, frontend_build_dir).model_copy(update={"trading_mode": "live"})

    account = await read_first_account(settings, make_connected_gateway([ACCOUNT_ID]))

    assert account["check"]["status"] == "failed"
    assert "trading_mode is 'live'" in account["check"]["message"]


@pytest.mark.anyio
async def test_writes_one_error_line_and_does_not_retry_a_failed_check(
    database_url: str, frontend_build_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.ERROR, logger="atrade.paper_trading")
    gateway_connection = make_connected_gateway(["DU7654321"])

    async with open_paper_trading_socket(make_settings(database_url, frontend_build_dir), gateway_connection) as socket:
        first = await receive_account(socket)
        gateway_connection.managed_accounts = [ACCOUNT_ID]
        await anyio.sleep(1)

    assert first["check"]["status"] == "failed"
    error_lines = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert len(error_lines) == 1
    assert "DU7654321" in error_lines[0].getMessage()
    assert ACCOUNT_ID in error_lines[0].getMessage()


@pytest.mark.anyio
async def test_clears_the_result_when_the_connection_drops(database_url: str, frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    gateway_connection.account_values = make_balance_values(ACCOUNT_ID, net_liquidation_usd="5", cash_usd="5")

    async with open_paper_trading_socket(make_settings(database_url, frontend_build_dir), gateway_connection) as socket:
        connected = await receive_account(socket)
        gateway_connection.connected = False
        dropped = await receive_account(socket)

    assert connected["check"]["status"] == "passed"
    assert dropped["check"] == {
        "status": "disconnected",
        "message": None,
        "actual_accounts": [],
        "expected_account": ACCOUNT_ID,
    }
    assert dropped["balance"] is None


@pytest.mark.anyio
async def test_checks_again_after_a_reconnection(database_url: str, frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway(["DU7654321"])

    async with open_paper_trading_socket(make_settings(database_url, frontend_build_dir), gateway_connection) as socket:
        first = await receive_account(socket)
        gateway_connection.connected = False
        await receive_account(socket)
        gateway_connection.managed_accounts = [ACCOUNT_ID]
        gateway_connection.connected = True
        after_reconnection = await receive_account(socket)

    assert first["check"]["status"] == "failed"
    assert after_reconnection["check"]["status"] == "passed"


@pytest.mark.anyio
async def test_pushes_a_balance_change(database_url: str, frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    gateway_connection.account_values = make_balance_values(ACCOUNT_ID, net_liquidation_usd="100", cash_usd="100")

    async with open_paper_trading_socket(make_settings(database_url, frontend_build_dir), gateway_connection) as socket:
        await receive_account(socket)
        gateway_connection.account_values = make_balance_values(ACCOUNT_ID, net_liquidation_usd="90", cash_usd="80")
        changed = await receive_account(socket)

    assert changed["balance"]["net_liquidation_usd"] == "90"
    assert changed["balance"]["cash_usd"] == "80"


@pytest.mark.anyio
async def test_pushes_a_eur_balance_in_usd_with_the_base_currency_and_the_rate(
    database_url: str, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    gateway_connection.account_values = [
        AccountValue(account=ACCOUNT_ID, tag="NetLiquidation", value="1000.00", currency="EUR"),
        AccountValue(account=ACCOUNT_ID, tag="TotalCashValue", value="500.00", currency="EUR"),
    ]
    gateway_connection.exchange_rates = {("EUR", "USD"): Decimal("1.1139")}

    account = await read_first_account(make_settings(database_url, frontend_build_dir), gateway_connection)

    assert account["balance"] == {
        "net_liquidation_usd": "1113.90",
        "cash_usd": "556.95",
        "base_currency": "EUR",
        "net_liquidation_base": "1000.00",
        "cash_base": "500.00",
        "usd_per_base_unit": "1.1139",
        "exchange_rate_source": "ibkr_forex",
        "message": None,
    }


@pytest.mark.anyio
async def test_shows_no_balance_when_the_gateway_is_not_connected(database_url: str, frontend_build_dir: Path) -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID], is_gateway_reachable=False)

    account = await read_first_account(make_settings(database_url, frontend_build_dir), gateway_connection)

    assert account["check"]["status"] == "disconnected"
    assert account["balance"] is None
    assert account["positions"] == []


async def receive_orders(socket: AsyncWebSocketSession) -> list[JsonObject]:
    with anyio.fail_after(MESSAGE_WAIT_SECONDS):
        while True:
            message: JsonObject = json.loads(await socket.receive_text())
            if message["type"] == "orders":
                return message["orders"]


@pytest.mark.anyio
async def test_pushes_the_open_orders_and_each_change(database_url: str, frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    forward_test_order = make_forward_test_order(ACCOUNT_ID, forward_test_id=42, order_id=7, client_id=10)

    async with open_paper_trading_socket(make_settings(database_url, frontend_build_dir), gateway_connection) as socket:
        first = await receive_orders(socket)
        gateway_connection.open_orders = [forward_test_order]
        after_new_order = await receive_orders(socket)
        gateway_connection.open_orders = []
        after_fill = await receive_orders(socket)

    assert first == []
    assert [order["order_id"] for order in after_new_order] == [7]
    assert after_new_order[0]["source"] == {"kind": "forward_test", "forward_test_id": 42}
    assert after_new_order[0]["status"] == "Submitted"
    assert after_fill == []


@pytest.mark.anyio
async def test_pushes_no_orders_when_the_check_did_not_pass(database_url: str, frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway(["DU7654321"])
    gateway_connection.open_orders = [
        make_forward_test_order("DU7654321", forward_test_id=42, order_id=7, client_id=10)
    ]

    async with open_paper_trading_socket(make_settings(database_url, frontend_build_dir), gateway_connection) as socket:
        orders = await receive_orders(socket)

    assert orders == []
