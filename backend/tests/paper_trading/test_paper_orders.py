"""Paper orders sent by hand: send, list, and cancel through the HTTP routes, with the IBKR fake.

ATrade runs the paper account check before each order (docs/architecture/paper_trading.md sections 11.2-11.4).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest

from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import (
    FakeGatewayConnection,
    make_balance_values,
    make_execution,
    make_forward_test_order,
    make_stock_position,
)

ACCOUNT_ID = "DU1234567"
ORDERS_PATH = "/api/paper-trading/orders"
MANUAL_ORDERS_PATH = "/api/paper-trading/manual-orders"
FORWARD_TEST_CLIENT_ID = 10

type JsonObject = dict[str, Any]

LIMIT_ORDER: JsonObject = {
    "symbol": "AAPL",
    "exchange": "NASDAQ",
    "currency": "USD",
    "side": "BUY",
    "quantity": 3,
    "order_type": "LMT",
    "limit_price": "1.25",
    "time_in_force": "GTC",
}
MARKET_ORDER: JsonObject = {
    "symbol": "700",
    "exchange": "SEHK",
    "currency": "HKD",
    "side": "SELL",
    "quantity": 100,
    "order_type": "MKT",
    "limit_price": None,
    "time_in_force": "DAY",
}


def make_connected_gateway(managed_accounts: list[str]) -> FakeGatewayConnection:
    """The owner ledger starts with 10000.00 USD cash and 100 shares of 700 / SEHK for "By hand"."""
    gateway_connection = FakeGatewayConnection(managed_accounts=managed_accounts)
    gateway_connection.connected = True
    gateway_connection.account_values = make_balance_values(ACCOUNT_ID, net_liquidation_usd="12000", cash_usd="10000")
    gateway_connection.portfolio = [
        make_stock_position(
            ACCOUNT_ID, symbol="700", quantity="100", market_price="400", exchange="SEHK", currency="HKD"
        )
    ]
    return gateway_connection


@asynccontextmanager
async def open_client(
    *, database_url: str, clock: FixedClock, frontend_build_dir: Path, gateway_connection: FakeGatewayConnection
) -> AsyncGenerator[httpx.AsyncClient]:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=ACCOUNT_ID)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.anyio
async def test_sends_a_limit_order_to_the_paper_account_and_lists_it_as_an_order_by_hand(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        send_response = await client.post(ORDERS_PATH, json=LIMIT_ORDER)
        list_response = await client.get(ORDERS_PATH)

    assert send_response.status_code == 201
    order_id = send_response.json()["ibkr_order_id"]
    assert send_response.json()["account"] == ACCOUNT_ID
    assert list_response.status_code == 200
    assert list_response.json() == {
        "orders": [
            {
                "order_id": order_id,
                "account": ACCOUNT_ID,
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "currency": "USD",
                "side": "BUY",
                "quantity": "3",
                "order_type": "LMT",
                "limit_price": "1.25",
                "time_in_force": "GTC",
                "status": "Submitted",
                "filled_quantity": "0",
                "source": {"kind": "by_hand", "forward_test_id": None},
                "can_cancel": True,
            }
        ]
    }
    sent_order = gateway_connection.open_orders[0]
    assert sent_order.account == ACCOUNT_ID
    assert sent_order.order_ref == "ATRADE-BY-HAND"


@pytest.mark.anyio
async def test_stores_the_order_by_hand_without_status(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        send_response = await client.post(ORDERS_PATH, json=MARKET_ORDER)
        manual_orders_response = await client.get(MANUAL_ORDERS_PATH)

    assert manual_orders_response.status_code == 200
    assert manual_orders_response.json() == {
        "manual_orders": [
            {
                "id": 1,
                "created_at_utc": "2026-01-02T03:04:05Z",
                "account": ACCOUNT_ID,
                "symbol": "700",
                "exchange": "SEHK",
                "currency": "HKD",
                "side": "SELL",
                "quantity": 100,
                "order_type": "MKT",
                "limit_price": None,
                "time_in_force": "DAY",
                "ibkr_order_id": send_response.json()["ibkr_order_id"],
                # IBKR is the only source of fills. The fake has no execution of this order.
                "filled_quantity": "0",
                "average_fill_price": None,
            }
        ]
    }


@pytest.mark.anyio
async def test_refuses_the_order_with_the_actual_and_expected_account_when_the_check_fails(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway(["DU7654321"])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        send_response = await client.post(ORDERS_PATH, json=LIMIT_ORDER)
        manual_orders_response = await client.get(MANUAL_ORDERS_PATH)

    assert send_response.status_code == 403
    body = send_response.json()
    assert body["actual_accounts"] == ["DU7654321"]
    assert body["expected_account"] == ACCOUNT_ID
    assert "DU7654321" in body["detail"]
    assert gateway_connection.open_orders == []
    assert manual_orders_response.json() == {"manual_orders": []}


@pytest.mark.anyio
async def test_refuses_the_order_when_ib_gateway_is_not_connected(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        send_response = await client.post(ORDERS_PATH, json=LIMIT_ORDER)

    assert send_response.status_code == 403
    assert send_response.json()["detail"] == "ATrade is not connected to IB Gateway."
    assert send_response.json()["expected_account"] == ACCOUNT_ID
    assert gateway_connection.open_orders == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "changed_fields",
    [
        {"order_type": "LMT", "limit_price": None},
        {"order_type": "MKT", "limit_price": "1.25"},
        {"order_type": "STP"},
        {"time_in_force": "IOC"},
        {"quantity": 0},
        {"limit_price": "-1"},
        {"side": "SHORT"},
        {"symbol": ""},
    ],
)
async def test_refuses_an_order_that_is_not_a_market_or_limit_order_with_day_or_gtc(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, changed_fields: JsonObject
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        send_response = await client.post(ORDERS_PATH, json=LIMIT_ORDER | changed_fields)

    assert send_response.status_code == 422
    assert gateway_connection.open_orders == []


@pytest.mark.anyio
async def test_reports_an_ibkr_error_and_stores_no_order(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    gateway_connection.order_error_message = "Order rejected"
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        send_response = await client.post(ORDERS_PATH, json=LIMIT_ORDER)
        manual_orders_response = await client.get(MANUAL_ORDERS_PATH)

    assert send_response.status_code == 502
    assert "Order rejected" in send_response.json()["detail"]
    assert manual_orders_response.json() == {"manual_orders": []}


@pytest.mark.anyio
async def test_lists_forward_test_orders_with_their_forward_test_id_and_no_cancel(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    gateway_connection.open_orders = [
        make_forward_test_order(ACCOUNT_ID, forward_test_id=42, order_id=7, client_id=FORWARD_TEST_CLIENT_ID),
        make_forward_test_order("DU0000001", forward_test_id=43, order_id=8, client_id=FORWARD_TEST_CLIENT_ID),
    ]
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        list_response = await client.get(ORDERS_PATH)

    orders = list_response.json()["orders"]
    assert [order["order_id"] for order in orders] == [7]
    assert orders[0]["source"] == {"kind": "forward_test", "forward_test_id": 42}
    assert orders[0]["can_cancel"] is False


@pytest.mark.anyio
async def test_lists_no_orders_when_the_check_did_not_pass(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway(["DU7654321"])
    gateway_connection.open_orders = [
        make_forward_test_order("DU7654321", forward_test_id=42, order_id=7, client_id=FORWARD_TEST_CLIENT_ID)
    ]
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        list_response = await client.get(ORDERS_PATH)

    assert list_response.status_code == 200
    assert list_response.json() == {"orders": []}


@pytest.mark.anyio
async def test_cancels_an_order_by_hand(database_url: str, clock: FixedClock, frontend_build_dir: Path) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        order_id = (await client.post(ORDERS_PATH, json=LIMIT_ORDER)).json()["ibkr_order_id"]
        cancel_response = await client.delete(f"{ORDERS_PATH}/{order_id}")
        list_response = await client.get(ORDERS_PATH)

    assert cancel_response.status_code == 202
    assert list_response.json() == {"orders": []}


@pytest.mark.anyio
async def test_refuses_to_cancel_a_forward_test_order(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    gateway_connection.open_orders = [
        make_forward_test_order(ACCOUNT_ID, forward_test_id=42, order_id=7, client_id=FORWARD_TEST_CLIENT_ID)
    ]
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        cancel_response = await client.delete(f"{ORDERS_PATH}/7")

    assert cancel_response.status_code == 409
    assert "forward test 42" in cancel_response.json()["detail"]
    assert len(gateway_connection.open_orders) == 1


@pytest.mark.anyio
async def test_reports_an_unknown_order_on_cancel(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        cancel_response = await client.delete(f"{ORDERS_PATH}/999")

    assert cancel_response.status_code == 404


async def start_forward_test_on(
    client: httpx.AsyncClient, *, symbol: str, allocated_capital_usd: str = "1000"
) -> JsonObject:
    # A new strategy has version 1 from the template. A forward test can use it.
    strategy = (await client.post("/api/strategies", json={"name": f"Blocker {symbol}"})).json()
    strategy_version_id = (await client.get(f"/api/strategies/{strategy['id']}/versions/1")).json()["id"]
    request = {
        "strategy_version_id": strategy_version_id,
        "symbol": symbol,
        "exchange": "NASDAQ",
        "currency": "USD",
        "bar_period": "1-MINUTE",
        "allocated_capital_usd": allocated_capital_usd,
    }
    return (await client.post("/api/forward-tests", json=request)).json()


@pytest.mark.anyio
async def test_sends_an_order_by_hand_on_the_instrument_of_a_running_forward_test(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    """The owners share the instruments (section 12.2). The order by hand goes to IBKR."""
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        forward_test = await start_forward_test_on(client, symbol="AAPL")
        response = await client.post(ORDERS_PATH, json=LIMIT_ORDER)

    assert forward_test["client_id"] == FORWARD_TEST_CLIENT_ID
    assert response.status_code == 201
    assert len(gateway_connection.open_orders) == 1


@pytest.mark.anyio
async def test_the_cash_of_by_hand_does_not_include_the_allocated_capital(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    """The ledger cash of "By hand" is 10000. A forward test takes 9000 of it (section 11.13)."""
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        await start_forward_test_on(client, symbol="MSFT", allocated_capital_usd="9000")
        response = await client.post(ORDERS_PATH, json=LIMIT_ORDER | {"quantity": 1000, "limit_price": "2"})

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "By hand has 1000.00 USD cash and open buy orders for 0.00 USD. ATrade refuses a buy order for 2000.00 USD."
        ),
        "rule": "buy_more_than_cash",
    }


@pytest.mark.anyio
async def test_sends_an_order_by_hand_when_the_forward_test_runs_on_another_instrument(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        await start_forward_test_on(client, symbol="MSFT")
        response = await client.post(ORDERS_PATH, json=LIMIT_ORDER)

    assert response.status_code == 201


@pytest.mark.anyio
async def test_lists_orders_by_hand_with_the_fills_from_ibkr(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        filled_order_id = (await client.post(ORDERS_PATH, json=MARKET_ORDER)).json()["ibkr_order_id"]
        open_order_id = (await client.post(ORDERS_PATH, json=LIMIT_ORDER)).json()["ibkr_order_id"]
        gateway_connection.executions = [
            make_execution(ACCOUNT_ID, order_id=filled_order_id, quantity="60", price="380.20"),
            make_execution(ACCOUNT_ID, order_id=filled_order_id, quantity="40", price="380.70"),
            # The same order ID from another client ID is another order.
            make_execution(
                ACCOUNT_ID, order_id=open_order_id, quantity="3", price="1.25", client_id=FORWARD_TEST_CLIENT_ID
            ),
        ]
        manual_orders = (await client.get(MANUAL_ORDERS_PATH)).json()["manual_orders"]

    fills = [(order["symbol"], order["filled_quantity"], order["average_fill_price"]) for order in manual_orders]
    assert fills == [("700", "100", "380.40"), ("AAPL", "0", None)]


@pytest.mark.anyio
async def test_lists_orders_by_hand_without_fills_when_the_check_did_not_pass(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_connected_gateway([ACCOUNT_ID])
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        await client.post(ORDERS_PATH, json=MARKET_ORDER)
        gateway_connection.connected = False
        manual_orders = (await client.get(MANUAL_ORDERS_PATH)).json()["manual_orders"]

    assert [(order["filled_quantity"], order["average_fill_price"]) for order in manual_orders] == [(None, None)]
