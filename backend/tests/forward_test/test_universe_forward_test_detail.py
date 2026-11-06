"""The detail route of a multi-instrument forward test: the Instruments tab and the Symbol column of the fills
(docs/architecture/forward_test.md sections 12.13 and 12.16)."""

from datetime import UTC, datetime
from decimal import Decimal

import httpx
import psycopg
import pytest

from atrade.forward_test import OwnerFill
from atrade.foundation.instrument import Instrument
from atrade.paper_trading import ForwardTestLedger
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection
from tests.forward_test.test_forward_test_routes import (
    FAKE_ACCOUNT_ID,
    FORWARD_TESTS_PATH,
    JsonObject,
    make_universe_request,
    save_test_strategy_version,
)

APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")


async def start_watchlist_forward_test(
    web_client: httpx.AsyncClient, database_url: str, symbols: list[str]
) -> JsonObject:
    strategy_version_id = await save_test_strategy_version(web_client)
    with psycopg.connect(database_url, autocommit=True) as connection:
        for symbol in symbols:
            connection.execute(
                """
                INSERT INTO watchlist_instrument (symbol, exchange, currency, added_at_utc)
                VALUES (%(symbol)s, 'NASDAQ', 'USD', now())
                """,
                {"symbol": symbol},
            )
    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, {"kind": "list"})
    )
    assert response.status_code == 201
    return response.json()


async def save_ledger_fill(database_url: str, forward_test_id: int, side: str, price: str, number: int) -> None:
    ledger = ForwardTestLedger(
        database_url=database_url,
        account=FAKE_ACCOUNT_ID,
        forward_test_id=forward_test_id,
        gateway_connection=FakeGatewayConnection(managed_accounts=[FAKE_ACCOUNT_ID]),
        clock=FixedClock(datetime(2026, 1, 5, tzinfo=UTC)),
    )
    await ledger.save_fill(
        OwnerFill(
            forward_test_id=forward_test_id,
            instrument=APPLE,
            side="BUY" if side == "BUY" else "SELL",
            quantity=Decimal(10),
            price=Decimal(price),
            time_utc=datetime(2026, 1, 5 + number, 15, tzinfo=UTC),
            order_ref=f"O-FT{forward_test_id}-{number}",
            execution_id=f"0000e0d5.{number}",
            ibkr_order_id=number,
            commission=Decimal(0),
        )
    )


@pytest.mark.anyio
async def test_the_detail_lists_each_member_with_its_fills_net_profit_and_quarters(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_watchlist_forward_test(web_client, database_url, ["AAPL", "MSFT"])
    await save_ledger_fill(database_url, forward_test["id"], "BUY", "100", 1)
    await save_ledger_fill(database_url, forward_test["id"], "SELL", "110", 2)

    response = await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}")

    assert response.status_code == 200
    assert response.json()["instruments"] == [
        {"symbol": "AAPL", "exchange": "NASDAQ", "trade_count": 2, "net_profit_usd": "100", "quarter_count": 1},
        {"symbol": "MSFT", "exchange": "NASDAQ", "trade_count": 0, "net_profit_usd": "0", "quarter_count": 1},
    ]
    assert [(fill["symbol"], fill["side"]) for fill in response.json()["fills"]] == [("AAPL", "BUY"), ("AAPL", "SELL")]


@pytest.mark.anyio
async def test_a_single_instrument_forward_test_has_no_instrument_rows(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    universe = {"kind": "single", "symbol": "AAPL", "exchange": "NASDAQ", "currency": "USD"}
    forward_test = (
        await web_client.post(FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, universe))
    ).json()

    response = await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}")

    assert response.json()["instruments"] == []


def write_split_round_trips(database_url: str, forward_test_id: int) -> None:
    """Buy 100 at 100, a 2:1 split, sell 200 at 55: a win of 1000. Buy 100 at 50, sell 100 at 45: a loss of 500."""
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO owner_ledger_entry (owner_kind, forward_test_id, entry_kind, time_utc, account, symbol,
                exchange, currency, quantity_change, price, commission, cash_change, ibkr_execution_id, ibkr_order_id)
            VALUES ('forward_test', %s, 'fill', %s, 'DU1234567', 'AAPL', 'NASDAQ', 'USD', %s, %s, 0, %s, %s, %s)
            """,
            [
                (forward_test_id, make_day(1), 100, "100", "-10000", "E-1", 1),
                (forward_test_id, make_day(4), -200, "55", "11000", "E-2", 2),
                (forward_test_id, make_day(5), 100, "50", "-5000", "E-3", 3),
                (forward_test_id, make_day(6), -100, "45", "4500", "E-4", 4),
            ],
        )
        cursor.execute(
            """
            INSERT INTO owner_ledger_entry (owner_kind, forward_test_id, entry_kind, time_utc, account, symbol,
                exchange, currency, quantity_change, cash_change, stock_split_id)
            VALUES ('forward_test', %s, 'split_adjustment', %s, 'DU1234567', 'AAPL', 'NASDAQ', 'USD', 100, 0, 1)
            """,
            (forward_test_id, make_day(2)),
        )
        cursor.executemany(
            "INSERT INTO forward_test_equity_point (forward_test_id, time_utc, equity_usd) VALUES (%s, %s, 100000)",
            [(forward_test_id, make_day(day)) for day in range(1, 9)],
        )


@pytest.mark.anyio
async def test_a_split_adjustment_counts_for_the_position_but_not_as_a_trade(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_watchlist_forward_test(web_client, database_url, ["AAPL"])
    write_split_round_trips(database_url, forward_test["id"])

    detail = (await web_client.get(f"/api/forward-tests/{forward_test['id']}")).json()

    metrics = detail["metrics"]
    assert Decimal(metrics["win_rate_percent"]) == 50
    assert Decimal(metrics["profit_factor"]) == 2
    assert Decimal(metrics["average_loss_usd"]) == -500
    assert Decimal(metrics["exposure_percent"]) == 50
    assert metrics["trade_count"] == 4
    [instrument] = detail["instruments"]
    assert instrument["trade_count"] == 4
    assert Decimal(instrument["net_profit_usd"]) == 500
    assert [fill["round_trip_net_profit_usd"] for fill in detail["fills"]] == [None, None, "1000", None, "-500"]


@pytest.mark.anyio
async def test_a_split_adjustment_that_ends_a_round_trip_has_the_net_profit_of_the_instrument_row(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_watchlist_forward_test(web_client, database_url, ["AAPL"])
    # Buy 5 at 100. A 1:10 reverse split leaves 0.5 shares, so the position goes to 0 with 30 USD cash in lieu.
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO owner_ledger_entry (owner_kind, forward_test_id, entry_kind, time_utc, account, symbol,
                exchange, currency, quantity_change, price, commission, cash_change, ibkr_execution_id, ibkr_order_id)
            VALUES ('forward_test', %s, 'fill', %s, 'DU1234567', 'AAPL', 'NASDAQ', 'USD', 5, 100, 0, -500, 'E-1', 1)
            """,
            (forward_test["id"], make_day(1)),
        )
        connection.execute(
            """
            INSERT INTO owner_ledger_entry (owner_kind, forward_test_id, entry_kind, time_utc, account, symbol,
                exchange, currency, quantity_change, cash_change, stock_split_id)
            VALUES ('forward_test', %s, 'split_adjustment', %s, 'DU1234567', 'AAPL', 'NASDAQ', 'USD', -5, 30, 1)
            """,
            (forward_test["id"], make_day(2)),
        )

    detail = (await web_client.get(f"/api/forward-tests/{forward_test['id']}")).json()

    [instrument] = detail["instruments"]
    profits = [fill["round_trip_net_profit_usd"] for fill in detail["fills"]]
    assert profits[0] is None
    assert Decimal(profits[1]) == Decimal(instrument["net_profit_usd"])


def make_day(day: int) -> datetime:
    return datetime(2026, 2, day, 15, tzinfo=UTC)
