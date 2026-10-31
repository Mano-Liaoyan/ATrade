"""A forward test compared with a backtest of the same period (docs/architecture/forward_test.md section 12.10).

The records of the forward test and the result of the backtest are rows in a real PostgreSQL. The DataActor test
(test_forward_test_recorder.py) and the backtest run tests check how those rows are written.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import psycopg
import pytest

from atrade.foundation.instrument import Instrument
from tests.fakes.clock import FixedClock
from tests.forward_test.test_forward_test_routes import (
    FORWARD_TESTS_PATH,
    make_start_request,
    save_test_strategy_version,
)
from tests.saved_ranges import save_ibkr_saved_range

type JsonObject = dict[str, Any]

START_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
STOPPED_UTC = datetime(2026, 1, 2, 3, 10, 5, tzinfo=UTC)


def make_minute(minute: int, second: int = 0) -> datetime:
    return datetime(2026, 1, 2, 3, minute, second, tzinfo=UTC)


async def start_forward_test(web_client: httpx.AsyncClient, *, currency: str = "USD") -> JsonObject:
    strategy_version_id = await save_test_strategy_version(web_client)
    request = make_start_request(strategy_version_id) | {"currency": currency}
    return (await web_client.post(FORWARD_TESTS_PATH, json=request)).json()


def write_forward_test_end(database_url: str, forward_test_id: int, *, is_stopped: bool = True) -> None:
    """The worker writes the stop (test_forward_test_worker.py). The allocated capital of the start is 10000."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            UPDATE forward_test SET status = %(status)s, desired_state = %(desired_state)s,
                client_id = %(client_id)s, stopped_at_utc = %(stopped_at_utc)s
            WHERE id = %(id)s
            """,
            {
                "id": forward_test_id,
                "status": "stopped" if is_stopped else "running",
                "desired_state": "stopped" if is_stopped else "running",
                "client_id": None if is_stopped else 10,
                "stopped_at_utc": STOPPED_UTC if is_stopped else None,
            },
        )


def write_forward_test_records(database_url: str, forward_test_id: int) -> None:
    """Fills like the ATrade execution client writes them into the owner ledger, equity points like the DataActor
    writes them, and an interruption like the worker writes it (section 12.7). No equity point at 03:07 and 03:08:
    the LiveNode did not run."""
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO owner_ledger_entry (owner_kind, forward_test_id, entry_kind, time_utc, account, symbol,
                exchange, currency, quantity_change, price, commission, cash_change, ibkr_execution_id, ibkr_order_id)
            VALUES ('forward_test', %(id)s, 'fill', %(time_utc)s, 'DU1234567', 'AAPL', 'NASDAQ', 'USD',
                %(quantity_change)s, %(price)s, 1, %(cash_change)s, %(execution_id)s, 1)
            """,
            [
                {
                    "id": forward_test_id,
                    "execution_id": f"E-{forward_test_id}-1",
                    "time_utc": make_minute(5, 2),
                    "quantity_change": 10,
                    "price": "100.05",
                    "cash_change": "-1001.5",
                },
                {
                    "id": forward_test_id,
                    "execution_id": f"E-{forward_test_id}-2",
                    "time_utc": make_minute(9, 1),
                    "quantity_change": -10,
                    "price": "101.00",
                    "cash_change": "1009",
                },
            ],
        )
        cursor.executemany(
            """
            INSERT INTO forward_test_equity_point (forward_test_id, time_utc, equity_usd)
            VALUES (%(id)s, %(time_utc)s, %(equity_usd)s)
            """,
            [
                {"id": forward_test_id, "time_utc": make_minute(5), "equity_usd": "10000"},
                {"id": forward_test_id, "time_utc": make_minute(6), "equity_usd": "10010"},
                {"id": forward_test_id, "time_utc": make_minute(9), "equity_usd": "10020"},
                {"id": forward_test_id, "time_utc": make_minute(10), "equity_usd": "10006"},
            ],
        )
        cursor.execute(
            """
            INSERT INTO forward_test_interruption (forward_test_id, reason, started_at_utc, ended_at_utc)
            VALUES (%(id)s, 'crash', %(started_at_utc)s, %(ended_at_utc)s)
            """,
            {"id": forward_test_id, "started_at_utc": make_minute(6, 30), "ended_at_utc": make_minute(8, 30)},
        )


def write_backtest_result(database_url: str, backtest_id: int) -> None:
    """Rows like the backtest child process writes them (backtest_store.save_result)."""
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO backtest_equity_point (backtest_id, time_utc, equity_usd) VALUES (%s, %s, %s)",
            [
                (backtest_id, make_minute(minute), equity)
                for minute, equity in zip(range(5, 11), range(10000, 10060, 10))
            ],
        )
        cursor.executemany(
            """
            INSERT INTO backtest_trade (backtest_id, time_utc, side, quantity_shares, price_usd, commission_usd)
            VALUES (%s, %s, %s, %s, %s, 0)
            """,
            [
                (backtest_id, make_minute(5), "BUY", 10, "100.00"),
                (backtest_id, make_minute(9), "SELL", 10, "101.20"),
                (backtest_id, make_minute(10), "BUY", 5, "99.00"),
            ],
        )
        cursor.execute(
            """
            UPDATE backtest SET status = 'finished', started_at_utc = %(now)s, ended_at_utc = %(now)s,
                final_equity_usd = 10050, total_return_percent = 0.50, max_drawdown_percent = 0, trade_count = 3
            WHERE id = %(id)s
            """,
            {"id": backtest_id, "now": STOPPED_UTC},
        )


async def start_same_period_backtest(web_client: httpx.AsyncClient, forward_test_id: int) -> httpx.Response:
    return await web_client.post(f"{FORWARD_TESTS_PATH}/{forward_test_id}/same-period-backtests")


@pytest.mark.anyio
async def test_the_same_period_backtest_uses_the_period_and_the_start_balance_of_a_stopped_forward_test(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_forward_test(web_client)
    write_forward_test_end(database_url, forward_test["id"])

    response = await start_same_period_backtest(web_client, forward_test["id"])

    assert response.status_code == 201
    backtest = (await web_client.get(f"/api/backtests/{response.json()['backtest_id']}")).json()
    assert backtest["status"] == "queued"
    assert backtest["strategy_version_id"] == forward_test["strategy_version_id"]
    assert (backtest["symbol"], backtest["exchange"], backtest["currency"]) == ("AAPL", "NASDAQ", "USD")
    assert backtest["bar_period"] == "1-MINUTE"
    assert backtest["start_utc"] == "2026-01-02T03:04:05Z"
    assert backtest["end_utc"] == "2026-01-02T03:10:05Z"
    assert backtest["paper_capital_usd"] == "10000"


@pytest.mark.anyio
async def test_the_same_period_backtest_of_a_running_forward_test_ends_now(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    write_forward_test_end(database_url, forward_test["id"], is_stopped=False)
    clock.now_utc = START_UTC + timedelta(hours=2)

    response = await start_same_period_backtest(web_client, forward_test["id"])

    backtest = (await web_client.get(f"/api/backtests/{response.json()['backtest_id']}")).json()
    assert backtest["end_utc"] == "2026-01-02T05:04:05Z"


@pytest.mark.anyio
async def test_the_same_period_backtest_of_an_old_forward_test_is_refused_without_a_start_balance(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_forward_test(web_client)
    # A forward test from the time before the allocated capital uses its start balance (section 12.24).
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            "UPDATE forward_test SET allocated_capital_usd = NULL WHERE id = %(id)s", {"id": forward_test["id"]}
        )

    response = await start_same_period_backtest(web_client, forward_test["id"])

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The forward test has no start balance yet. The backtest uses it as the paper capital."
    )


@pytest.mark.anyio
async def test_the_same_period_backtest_is_refused_for_an_instrument_that_is_not_in_usd(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_forward_test(web_client, currency="EUR")
    write_forward_test_end(database_url, forward_test["id"])

    response = await start_same_period_backtest(web_client, forward_test["id"])

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "A same-period backtest supports only USD instruments, because a forward test has no exchange rates."
        " The instrument currency is EUR."
    )


@pytest.mark.anyio
async def test_the_same_period_backtest_of_an_unknown_forward_test_is_not_found(web_client: httpx.AsyncClient) -> None:
    response = await start_same_period_backtest(web_client, 999)

    assert response.status_code == 404


@pytest.mark.anyio
async def test_compares_the_metrics_the_equity_curves_the_fills_and_the_interruptions(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_forward_test(web_client)
    write_forward_test_end(database_url, forward_test["id"])
    write_forward_test_records(database_url, forward_test["id"])
    backtest_id = (await start_same_period_backtest(web_client, forward_test["id"])).json()["backtest_id"]
    write_backtest_result(database_url, backtest_id)

    response = await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/comparison/{backtest_id}")

    assert response.status_code == 200
    comparison = response.json()
    assert comparison["forward_test"]["id"] == forward_test["id"]
    assert comparison["backtest"]["id"] == backtest_id
    assert comparison["backtest"]["status"] == "finished"
    # The metric functions of backtest: 10000 -> 10006, the peak 10020 falls to 10006 (0.1397 %).
    # The other metrics: test_forward_test_metrics.py.
    forward_test_metrics = comparison["forward_test_metrics"]
    assert {
        name: forward_test_metrics[name]
        for name in (
            "final_equity_usd",
            "net_profit_usd",
            "total_return_percent",
            "max_drawdown_percent",
            "trade_count",
        )
    } == {
        "final_equity_usd": "10006",
        "net_profit_usd": "6",
        "total_return_percent": "0.06",
        "max_drawdown_percent": "0.14",
        "trade_count": 2,
    }
    # The Net profit of the backtest uses its paper capital: 10050 - 10000.
    assert (comparison["backtest"]["metrics"]["trade_count"], comparison["backtest"]["metrics"]["net_profit_usd"]) == (
        3,
        "50",
    )
    assert [point["time_utc"] for point in comparison["forward_test_equity_curve"]] == [
        "2026-01-02T03:05:00Z",
        "2026-01-02T03:06:00Z",
        "2026-01-02T03:09:00Z",
        "2026-01-02T03:10:00Z",
    ]
    assert len(comparison["backtest_equity_curve"]) == 6
    # A fill belongs to the last bar that ended at or before it: the reaction to that bar.
    assert comparison["fills"] == [
        {
            "bar_end_utc": "2026-01-02T03:05:00Z",
            "side": "BUY",
            "forward_test_quantity_shares": "10",
            "forward_test_price_usd": "100.05",
            "backtest_quantity_shares": "10",
            "backtest_price_usd": "100.00",
            "price_difference_usd": "0.05",
        },
        {
            "bar_end_utc": "2026-01-02T03:09:00Z",
            "side": "SELL",
            "forward_test_quantity_shares": "10",
            "forward_test_price_usd": "101.00",
            "backtest_quantity_shares": "10",
            "backtest_price_usd": "101.20",
            "price_difference_usd": "-0.20",
        },
        {
            "bar_end_utc": "2026-01-02T03:10:00Z",
            "side": "BUY",
            "forward_test_quantity_shares": None,
            "forward_test_price_usd": None,
            "backtest_quantity_shares": "5",
            "backtest_price_usd": "99.00",
            "price_difference_usd": None,
        },
    ]
    assert comparison["interruptions"] == [
        {"start_utc": "2026-01-02T03:06:30Z", "end_utc": "2026-01-02T03:08:30Z"},
    ]


@pytest.mark.anyio
async def test_a_queued_backtest_has_no_result_yet(web_client: httpx.AsyncClient, database_url: str) -> None:
    forward_test = await start_forward_test(web_client)
    write_forward_test_end(database_url, forward_test["id"])
    backtest_id = (await start_same_period_backtest(web_client, forward_test["id"])).json()["backtest_id"]

    comparison = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/comparison/{backtest_id}")).json()

    assert comparison["backtest"]["status"] == "queued"
    assert comparison["backtest"]["metrics"] is None
    assert comparison["backtest_equity_curve"] == []
    assert comparison["forward_test_metrics"]["trade_count"] == 0
    assert comparison["fills"] == []
    assert comparison["interruptions"] == []


@pytest.mark.anyio
async def test_an_interruption_that_still_lasts_ends_now_on_the_chart(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    write_forward_test_end(database_url, forward_test["id"], is_stopped=False)
    clock.now_utc = STOPPED_UTC
    backtest_id = (await start_same_period_backtest(web_client, forward_test["id"])).json()["backtest_id"]
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO forward_test_interruption (forward_test_id, reason, started_at_utc)
            VALUES (%(id)s, 'gateway', %(started_at_utc)s)
            """,
            {"id": forward_test["id"], "started_at_utc": make_minute(9)},
        )

    comparison = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/comparison/{backtest_id}")).json()

    assert comparison["interruptions"] == [{"start_utc": "2026-01-02T03:09:00Z", "end_utc": "2026-01-02T03:10:05Z"}]


@pytest.mark.anyio
async def test_a_backtest_of_another_instrument_is_refused(web_client: httpx.AsyncClient, database_url: str) -> None:
    forward_test = await start_forward_test(web_client)
    # The start route refuses a backtest without saved bars, so the other instrument gets one saved bar.
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO ibkr_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES ('MSFT', 'NASDAQ', 'USD', '1-MINUTE', %(start_utc)s, 100, 101, 99, 100, 1000)
            """,
            {"start_utc": make_minute(5)},
        )
        save_ibkr_saved_range(connection, Instrument(symbol="MSFT", exchange="NASDAQ", currency="USD"), "1-MINUTE")
    other_backtest = await web_client.post(
        "/api/backtests",
        json={
            "strategy_version_id": forward_test["strategy_version_id"],
            "symbol": "MSFT",
            "exchange": "NASDAQ",
            "currency": "USD",
            "bar_period": "1-MINUTE",
            "start_utc": "2026-01-02T03:04:05Z",
            "end_utc": "2026-01-02T03:10:05Z",
            "paper_capital_usd": "10000",
        },
    )

    response = await web_client.get(
        f"{FORWARD_TESTS_PATH}/{forward_test['id']}/comparison/{other_backtest.json()['id']}"
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The backtest must use the strategy version, the instrument, and the bar period of the forward test."
    )


@pytest.mark.anyio
async def test_the_forward_test_page_has_the_records_and_links_each_same_period_backtest(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_forward_test(web_client)
    write_forward_test_end(database_url, forward_test["id"])
    write_forward_test_records(database_url, forward_test["id"])
    first_backtest_id = (await start_same_period_backtest(web_client, forward_test["id"])).json()["backtest_id"]
    write_backtest_result(database_url, first_backtest_id)
    second_backtest_id = (await start_same_period_backtest(web_client, forward_test["id"])).json()["backtest_id"]

    response = await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["forward_test"]["id"] == forward_test["id"]
    assert detail["forward_test"]["interruptions"][0]["reason"] == "crash"
    assert detail["metrics"]["trade_count"] == 2
    assert [point["equity_usd"] for point in detail["equity_curve"]] == ["10000", "10010", "10020", "10006"]
    assert detail["fills"][0] == {
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "time_utc": "2026-01-02T03:05:02Z",
        "kind": "fill",
        "side": "BUY",
        "quantity_shares": "10",
        "price_usd": "100.05",
        "commission_usd": "1",
        "amount_usd": "1000.50",
        "split_ratio": None,
    }
    # Newest first. The page links to the comparison with each one.
    assert [(item["id"], item["status"]) for item in detail["same_period_backtests"]] == [
        (second_backtest_id, "queued"),
        (first_backtest_id, "finished"),
    ]


@pytest.mark.anyio
async def test_a_new_forward_test_page_has_no_records_and_no_backtests(web_client: httpx.AsyncClient) -> None:
    forward_test = await start_forward_test(web_client)

    detail = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}")).json()

    assert detail["metrics"]["trade_count"] == 0
    assert (detail["equity_curve"], detail["fills"], detail["same_period_backtests"]) == ([], [], [])


@pytest.mark.anyio
async def test_the_page_of_an_unknown_forward_test_is_not_found(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get(f"{FORWARD_TESTS_PATH}/999")

    assert response.status_code == 404
