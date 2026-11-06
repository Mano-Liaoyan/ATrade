"""The owner ledger of "By hand": the ledger start, the 3 order rules, the fills of orders by hand, and the owners of
each position on /ws/paper-trading. Real PostgreSQL and the IBKR fake (docs/architecture/paper_trading.md 11.10).
"""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta
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
from atrade.foundation.instrument import Instrument
from atrade.foundation.order_ref import MANUAL_ORDER_REF
from atrade.foundation.settings import Settings
from atrade.ibkr import AccountValue, OpenOrder
from atrade.ibkr import gateway_connection as gateway_connection_module
from atrade.paper_trading import ManualOrderLedger, PaperAccountMonitor, manual_order_ledger
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import (
    WEB_CLIENT_ID,
    FakeGatewayConnection,
    make_balance_values,
    make_execution,
    make_stock_position,
)
from tests.ibkr.test_read_executions import GatewayMessages, make_ib_execution

ACCOUNT_ID = "DU1234567"
ORDERS_PATH = "/api/paper-trading/orders"
MESSAGE_WAIT_SECONDS = 5
FILL_WAIT_SECONDS = 2
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
async def test_counts_an_open_sell_order_of_an_earlier_session_that_has_the_exchange_smart(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_gateway()
    gateway_connection.open_orders.append(
        OpenOrder(
            order_id=900,
            client_id=WEB_CLIENT_ID,
            perm_id=9000,
            account=ACCOUNT_ID,
            instrument=Instrument(symbol="700", exchange="SMART", currency="HKD"),
            side="SELL",
            quantity=Decimal(60),
            order_type="LMT",
            limit_price=Decimal(410),
            time_in_force="GTC",
            status="Submitted",
            filled_quantity=Decimal(0),
            order_ref=MANUAL_ORDER_REF,
        )
    )
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        response = await client.post(
            ORDERS_PATH, json=make_order(symbol="700", side="SELL", quantity=100, limit_price="410")
        )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "By hand holds 100 700 and has open sell orders for 60. ATrade refuses a sell order for 100."
    )


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


def make_earlier_session_market_buy(symbol: str) -> OpenOrder:
    """ib_async decodes no primary exchange for an open order of an earlier session."""
    return OpenOrder(
        order_id=900,
        client_id=WEB_CLIENT_ID,
        perm_id=9000,
        account=ACCOUNT_ID,
        instrument=Instrument(symbol=symbol, exchange="SMART", currency="USD"),
        side="BUY",
        quantity=Decimal(10),
        order_type="MKT",
        limit_price=None,
        time_in_force="GTC",
        status="Submitted",
        filled_quantity=Decimal(0),
        order_ref=MANUAL_ORDER_REF,
    )


@pytest.mark.anyio
async def test_an_earlier_session_market_buy_reads_its_daily_bars_with_the_exchange_of_the_watchlist(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            "INSERT INTO watchlist_instrument (symbol, exchange, currency, added_at_utc) "
            "VALUES ('MSFT', 'NYSE', 'USD', now())"
        )
    gateway_connection = make_gateway()
    gateway_connection.open_orders.append(make_earlier_session_market_buy("MSFT"))
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        response = await client.post(
            ORDERS_PATH, json=make_order(symbol="AAPL", side="BUY", quantity=1, limit_price="100")
        )

    assert response.status_code == 201
    assert [request.instrument.exchange for request in gateway_connection.historical_bar_requests] == ["NYSE"]


@pytest.mark.anyio
async def test_an_earlier_session_market_buy_of_an_unknown_instrument_refuses_with_a_clear_message(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_gateway()
    gateway_connection.open_orders.append(make_earlier_session_market_buy("MSFT"))
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        response = await client.post(
            ORDERS_PATH, json=make_order(symbol="AAPL", side="BUY", quantity=1, limit_price="100")
        )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "By hand has an open market buy order for MSFT from an earlier session, and ATrade does not know its"
            " exchange. Add MSFT to the watchlist or cancel the order."
        ),
        "rule": "buy_more_than_cash",
    }
    assert gateway_connection.historical_bar_requests == []


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
async def test_an_unfilled_market_buy_order_uses_cash_for_the_next_buy_order(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=make_gateway(),
    ) as client:
        # The daily closes of the fake are between 100 and 149 USD: 1 order fits in 10000 USD, and 2 orders do not.
        responses = [
            await client.post(ORDERS_PATH, json=make_order(symbol="AAPL", side="BUY", quantity=60, limit_price=None))
            for _ in range(3)
        ]

    assert [response.status_code for response in responses] == [201, 409, 409]
    assert responses[1].json()["rule"] == "buy_more_than_cash"


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


def count_fills(database_url: str) -> int:
    with psycopg.connect(database_url) as connection:
        row = connection.execute("SELECT count(*) FROM owner_ledger_entry WHERE entry_kind = 'fill'").fetchone()
    assert row is not None
    return row[0]


@pytest.mark.anyio
async def test_records_a_fill_by_hand_while_no_page_is_open(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manual_order_ledger, "FILL_RECORD_INTERVAL_SECONDS", 0.01)
    gateway_connection = make_gateway()
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=ACCOUNT_ID)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=ASGIWebSocketTransport(app=app), base_url="http://test") as client,
    ):
        response = await client.post(
            ORDERS_PATH, json=make_order(symbol="AAPL", side="BUY", quantity=10, limit_price="100")
        )
        gateway_connection.executions = [
            make_execution(ACCOUNT_ID, order_id=response.json()["ibkr_order_id"], quantity="10", price="100")
        ]
        with anyio.move_on_after(FILL_WAIT_SECONDS):
            while count_fills(database_url) == 0:
                await anyio.sleep(0.01)

    assert count_fills(database_url) == 1


@pytest.mark.anyio
async def test_the_fill_recording_continues_after_a_database_error(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manual_order_ledger, "FILL_RECORD_INTERVAL_SECONDS", 0)
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=ACCOUNT_ID)
    monitor = PaperAccountMonitor(settings=settings, gateway_connection=make_gateway())
    ledger = ManualOrderLedger(paper_account_monitor=monitor, database_url=database_url, clock=clock)
    accounts: list[str] = []

    with anyio.CancelScope() as scope:

        async def fail_once(account: str) -> None:
            accounts.append(account)
            if len(accounts) == 1:
                message = "The database is not available."
                raise psycopg.OperationalError(message)
            scope.cancel()

        monkeypatch.setattr(ledger, "record_fills", fail_once)
        await ledger.keep_recording_fills()

    assert accounts == [ACCOUNT_ID, ACCOUNT_ID]


@pytest.mark.anyio
async def test_reads_the_exchange_rate_only_for_a_new_fill(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = make_gateway()
    gateway_connection.exchange_rates[("HKD", "USD")] = Decimal("0.13")
    async with open_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        gateway_connection=gateway_connection,
    ) as client:
        await read_account(client)
        response = await client.post(
            ORDERS_PATH, json=make_order(symbol="700", side="SELL", quantity=10, limit_price="400")
        )
    gateway_connection.executions = [
        make_execution(
            ACCOUNT_ID,
            order_id=response.json()["ibkr_order_id"],
            quantity="10",
            price="400",
            side="SLD",
            symbol="700",
            currency="HKD",
        )
    ]
    gateway_connection.exchange_rate_requests.clear()
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=ACCOUNT_ID)
    monitor = PaperAccountMonitor(settings=settings, gateway_connection=gateway_connection)
    ledger = ManualOrderLedger(paper_account_monitor=monitor, database_url=database_url, clock=clock)

    await ledger.record_fills(ACCOUNT_ID)
    await ledger.record_fills(ACCOUNT_ID)

    assert gateway_connection.exchange_rate_requests == [("HKD", "USD")]
    assert count_fills(database_url) == 1


@pytest.mark.anyio
async def test_records_a_fill_by_hand_without_a_report_at_the_limit(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gateway_connection_module, "COMMISSION_REPORT_WAIT_SECONDS", 0.05)
    gateway_connection = make_gateway()
    messages = GatewayMessages(monkeypatch)
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
        gateway_connection.open_orders = []
        messages.execution = make_ib_execution(
            order_id=response.json()["ibkr_order_id"], client_id=WEB_CLIENT_ID, age=timedelta(minutes=5)
        )
        gateway_connection.read_executions = messages.connection.read_executions  # pyright: ignore[reportAttributeAccessIssue]
        await read_account(client)

    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            "SELECT quantity_change, commission FROM owner_ledger_entry WHERE entry_kind = 'fill'"
        ).fetchall()
    assert rows == [(Decimal(10), Decimal(0))]


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
