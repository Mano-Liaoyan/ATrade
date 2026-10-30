"""The owner ledger of "By hand": the ledger start, the 3 order rules, the fills of orders by hand, and the owners of
each position on /ws/paper-trading. Real PostgreSQL and the IBKR fake (docs/architecture/paper_trading.md 11.10).
"""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

import anyio
import httpx
import psycopg
import pytest
from httpx_ws import AsyncWebSocketSession, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from atrade.ibkr import AccountValue
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, make_balance_values, make_execution, make_stock_position

ACCOUNT_ID = "DU1234567"
ORDERS_PATH = "/api/paper-trading/orders"
MESSAGE_WAIT_SECONDS = 5
BY_HAND: dict[str, Any] = {"kind": "by_hand", "forward_test_id": None}

type JsonObject = dict[str, Any]


def make_gateway() -> FakeGatewayConnection:
    """10000 USD cash and 100 shares of 700 / SEHK at the ledger start."""
    gateway_connection = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID])
    gateway_connection.connected = True
    gateway_connection.account_values = make_balance_values(ACCOUNT_ID, net_liquidation_usd="15000", cash_usd="10000")
    gateway_connection.portfolio = [
        make_stock_position(
            ACCOUNT_ID, symbol="700", quantity="100", market_price="400", exchange="SEHK", currency="HKD"
        )
    ]
    return gateway_connection


def make_order(*, symbol: str, side: str, quantity: int, limit_price: str | None) -> JsonObject:
    exchange, currency = ("SEHK", "HKD") if symbol == "700" else ("NASDAQ", "USD")
    return {
        "symbol": symbol,
        "exchange": exchange,
        "currency": currency,
        "side": side,
        "quantity": quantity,
        "order_type": "MKT" if limit_price is None else "LMT",
        "limit_price": limit_price,
        "time_in_force": "DAY",
    }


@asynccontextmanager
async def open_client(
    *, database_url: str, clock: FixedClock, frontend_build_dir: Path, gateway_connection: FakeGatewayConnection
) -> AsyncGenerator[httpx.AsyncClient]:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=ACCOUNT_ID)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=ASGIWebSocketTransport(app=app), base_url="http://test") as client:
        yield client


async def read_account(client: httpx.AsyncClient) -> JsonObject:
    """The first "account" message, after the first "orders" message recorded the new fills."""
    socket: AsyncWebSocketSession
    async with aconnect_ws("/ws/paper-trading", client) as socket:
        with anyio.fail_after(MESSAGE_WAIT_SECONDS):
            while json.loads(await socket.receive_text())["type"] != "orders":
                pass
    async with aconnect_ws("/ws/paper-trading", client) as socket:
        with anyio.fail_after(MESSAGE_WAIT_SECONDS):
            while True:
                message: JsonObject = json.loads(await socket.receive_text())
                if message["type"] == "account":
                    return message


def find_position(account: JsonObject, symbol: str) -> JsonObject:
    return next(position for position in account["positions"] if position["symbol"] == symbol)


def count_manual_orders(database_url: str) -> int:
    with psycopg.connect(database_url) as connection:
        row = connection.execute("SELECT count(*) FROM manual_order").fetchone()
    return 0 if row is None else int(row[0])


@pytest.mark.anyio
async def test_the_ledger_starts_with_the_positions_and_the_cash_of_the_account_for_by_hand(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_gateway()
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        account = await read_account(client)

    position = find_position(account, "700")
    assert position["owners"] == [{"owner": BY_HAND, "quantity": "100", "average_cost": "400"}]
    assert position["unattributed_quantity"] == "0"
    assert account["unattributed_cash_usd"] == "0"
    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            "SELECT owner_kind, entry_kind, symbol, quantity_change, cash_change FROM owner_ledger_entry ORDER BY id"
        ).fetchall()
    assert [(row[0], row[1], row[2], str(row[3]), str(row[4])) for row in rows] == [
        ("by_hand", "ledger_start", "700", "100", "0"),
        ("by_hand", "ledger_start", None, "0", "10000"),
    ]


@pytest.mark.anyio
async def test_refuses_a_sell_order_larger_than_the_position_minus_the_open_sell_orders(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_gateway()
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        first_response = await client.post(
            ORDERS_PATH, json=make_order(symbol="700", side="SELL", quantity=60, limit_price="410")
        )
        refused_response = await client.post(
            ORDERS_PATH, json=make_order(symbol="700", side="SELL", quantity=50, limit_price=None)
        )

    assert first_response.status_code == 201
    assert refused_response.status_code == 409
    assert refused_response.json() == {
        "detail": "By hand holds 100 700 and has open sell orders for 60. ATrade refuses a sell order for 50.",
        "rule": "sell_more_than_position",
    }
    assert len(gateway_connection.open_orders) == 1
    assert count_manual_orders(database_url) == 1


@pytest.mark.anyio
async def test_by_hand_cannot_sell_short(database_url: str, clock: FixedClock, frontend_build_dir: Path) -> None:
    gateway_connection = make_gateway()
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        response = await client.post(
            ORDERS_PATH, json=make_order(symbol="AAPL", side="SELL", quantity=1, limit_price="5")
        )

    assert response.status_code == 409
    assert response.json()["rule"] == "sell_more_than_position"
    assert response.json()["detail"] == (
        "By hand holds 0 AAPL and has open sell orders for 0. ATrade refuses a sell order for 1."
    )
    assert gateway_connection.open_orders == []
    assert count_manual_orders(database_url) == 0


@pytest.mark.anyio
async def test_refuses_a_buy_order_larger_than_the_cash_minus_the_open_buy_orders(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_gateway()
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        first_response = await client.post(
            ORDERS_PATH, json=make_order(symbol="AAPL", side="BUY", quantity=50, limit_price="100")
        )
        refused_response = await client.post(
            ORDERS_PATH, json=make_order(symbol="AAPL", side="BUY", quantity=51, limit_price="100")
        )
        allowed_response = await client.post(
            ORDERS_PATH, json=make_order(symbol="AAPL", side="BUY", quantity=50, limit_price="100")
        )

    assert first_response.status_code == 201
    assert refused_response.status_code == 409
    assert refused_response.json() == {
        "detail": (
            "By hand has 10000.00 USD cash and open buy orders for 5000.00 USD. "
            "ATrade refuses a buy order for 5100.00 USD."
        ),
        "rule": "buy_more_than_cash",
    }
    assert allowed_response.status_code == 201
    assert count_manual_orders(database_url) == 2


@pytest.mark.anyio
async def test_a_market_buy_order_uses_the_last_daily_close_and_a_foreign_currency_the_ibkr_rate(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_gateway()
    gateway_connection.exchange_rates[("HKD", "USD")] = Decimal("0.1")
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        # The daily closes of the fake are between 100 and 149 HKD: 600 shares are more than 6000 USD.
        refused_response = await client.post(
            ORDERS_PATH, json=make_order(symbol="700", side="BUY", quantity=1000, limit_price=None)
        )
        allowed_response = await client.post(
            ORDERS_PATH, json=make_order(symbol="700", side="BUY", quantity=100, limit_price=None)
        )

    assert refused_response.status_code == 409
    assert refused_response.json()["rule"] == "buy_more_than_cash"
    assert allowed_response.status_code == 201


@pytest.mark.anyio
async def test_records_each_fill_of_an_order_by_hand_once(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_gateway()
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        await read_account(client)
        response = await client.post(
            ORDERS_PATH, json=make_order(symbol="AAPL", side="BUY", quantity=10, limit_price="100")
        )
        order_id = response.json()["ibkr_order_id"]
        gateway_connection.open_orders = []
        gateway_connection.executions = [
            make_execution(ACCOUNT_ID, order_id=order_id, quantity="4", price="99", commission="1"),
            make_execution(ACCOUNT_ID, order_id=order_id, quantity="6", price="100", commission="1"),
        ]
        gateway_connection.portfolio = [
            *gateway_connection.portfolio,
            make_stock_position(ACCOUNT_ID, symbol="AAPL", quantity="10", market_price="100"),
        ]
        await read_account(client)
        account = await read_account(client)

    position = find_position(account, "AAPL")
    assert position["owners"] == [{"owner": BY_HAND, "quantity": "10", "average_cost": "99.6"}]
    assert position["unattributed_quantity"] == "0"
    # The fake cash stays 10000: the ledger cash of "By hand" is 10000 - 996 - 2.
    assert account["unattributed_cash_usd"] == "998"
    with psycopg.connect(database_url) as connection:
        row = connection.execute("SELECT count(*) FROM owner_ledger_entry WHERE entry_kind = 'fill'").fetchone()
    assert row == (2,)


@pytest.mark.anyio
async def test_shows_a_position_from_outside_the_ledger_as_unattributed(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_gateway()
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        await read_account(client)
        gateway_connection.portfolio = [
            make_stock_position(
                ACCOUNT_ID, symbol="700", quantity="150", market_price="400", exchange="SEHK", currency="HKD"
            ),
            make_stock_position(ACCOUNT_ID, symbol="AAPL", quantity="50", market_price="100"),
        ]
        account = await read_account(client)

    assert find_position(account, "700")["unattributed_quantity"] == "50"
    assert find_position(account, "AAPL")["owners"] == []
    assert find_position(account, "AAPL")["unattributed_quantity"] == "50"


@pytest.mark.anyio
async def test_refuses_orders_by_hand_until_the_ledger_can_start_with_a_usd_cash_value(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_gateway()
    gateway_connection.account_values = [
        AccountValue(account=ACCOUNT_ID, tag="NetLiquidation", value="1000", currency="EUR"),
        AccountValue(account=ACCOUNT_ID, tag="TotalCashValue", value="1000", currency="EUR"),
    ]
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        response = await client.post(
            ORDERS_PATH, json=make_order(symbol="700", side="SELL", quantity=1, limit_price="5")
        )

    assert response.status_code == 409
    assert response.json()["rule"] == "ledger_not_started"
    assert gateway_connection.open_orders == []
