"""The metrics of a forward test: the metrics of a backtest from the same functions, the Net profit, and the win rate
of the comparison (docs/architecture/forward_test.md section 12.10).
"""

from datetime import UTC, datetime
from decimal import Decimal

import httpx
import psycopg
import pytest

from atrade.backtest import BacktestTrade
from atrade.forward_test.comparison_routes import calculate_win_rate_in_period
from atrade.foundation.bar import TimeRange
from tests.forward_test.test_forward_test_comparison import (
    make_minute,
    start_forward_test,
    write_forward_test_end,
    write_forward_test_records,
)
from tests.forward_test.test_forward_test_routes import FORWARD_TESTS_PATH

# The forward test starts at 03:04:05 and stops at 03:10:05. This backtest ends before the last forward test fills.
SHORT_BACKTEST_END_UTC = datetime(2026, 1, 2, 3, 9, 5, tzinfo=UTC)


def write_losing_round_trip(database_url: str, forward_test_id: int) -> None:
    """A round trip with a loss after 03:09:05: it is outside the short backtest."""
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO forward_test_fill (forward_test_id, trade_id, time_utc, side, quantity_shares, price_usd,
                commission_usd)
            VALUES (%(id)s, %(trade_id)s, %(time_utc)s, %(side)s, 10, %(price_usd)s, 1)
            """,
            [
                {
                    "id": forward_test_id,
                    "trade_id": "T-3",
                    "time_utc": make_minute(9, 20),
                    "side": "BUY",
                    "price_usd": "101.00",
                },
                {
                    "id": forward_test_id,
                    "trade_id": "T-4",
                    "time_utc": make_minute(9, 40),
                    "side": "SELL",
                    "price_usd": "100.00",
                },
            ],
        )


async def start_short_backtest(web_client: httpx.AsyncClient, database_url: str, strategy_version_id: int) -> int:
    """A backtest of the forward test setup from the forward test start to 03:09:05."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES ('AAPL', 'NASDAQ', 'USD', '1-MINUTE', %(start_utc)s, 100, 101, 99, 100, 1000)
            """,
            {"start_utc": make_minute(5)},
        )
    response = await web_client.post(
        "/api/backtests",
        json={
            "strategy_version_id": strategy_version_id,
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "currency": "USD",
            "bar_period": "1-MINUTE",
            "start_utc": "2026-01-02T03:04:05Z",
            "end_utc": SHORT_BACKTEST_END_UTC.isoformat(),
            "paper_capital_usd": "10000",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.anyio
async def test_the_forward_test_page_has_the_new_metrics_and_the_net_profit(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_forward_test(web_client)
    write_forward_test_end(database_url, forward_test["id"])
    write_forward_test_records(database_url, forward_test["id"])

    detail = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}")).json()

    # Start balance 10000. One round trip: buy 10 at 100.05, sell 10 at 101.00, commission 1 each: profit 7.50 on an
    # entry amount of 1000.50 (0.75 %). The position is open at the bar ends 03:06 and 03:09 of the 4 equity points.
    # All equity points are on one UTC date, so there is 1 daily return. The range is 6 minutes.
    assert detail["metrics"] == {
        "final_equity_usd": "10006",
        "net_profit_usd": "6",
        "total_return_percent": "0.06",
        "max_drawdown_percent": "0.14",
        "trade_count": 2,
        "cagr_percent": None,
        "annual_volatility_percent": None,
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "calmar_ratio": None,
        "profit_factor": None,
        "average_win_usd": "7.50",
        "average_win_percent": "0.75",
        "average_loss_usd": None,
        "exposure_percent": "50.00",
        # Fill amounts 2010.50, mean equity 10009, 6 minutes of a year.
        "turnover_per_year": "17608.20",
        "win_rate_percent": "100.00",
        "missing_reasons": {
            "cagr_percent": "The range is shorter than 90 days",
            "calmar_ratio": "The range is shorter than 90 days",
            "annual_volatility_percent": "Fewer than 2 daily returns",
            "sharpe_ratio": "Fewer than 2 daily returns",
            "sortino_ratio": "Fewer than 2 daily returns",
            "profit_factor": "No round trip with a loss",
            "average_loss_usd": "No round trip with a loss",
        },
    }
    assert "split_metrics" not in detail
    assert "robustness" not in detail


@pytest.mark.anyio
async def test_the_comparison_win_rate_counts_only_the_fills_in_the_backtest_period(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_forward_test(web_client)
    write_forward_test_end(database_url, forward_test["id"])
    write_forward_test_records(database_url, forward_test["id"])
    write_losing_round_trip(database_url, forward_test["id"])
    backtest_id = await start_short_backtest(web_client, database_url, forward_test["strategy_version_id"])

    detail = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}")).json()
    comparison = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/comparison/{backtest_id}")).json()

    # The forward test page counts both round trips: 1 win of 2.
    assert detail["metrics"]["win_rate_percent"] == "50.00"
    # The losing round trip ends after the backtest period, so the comparison does not count it.
    assert comparison["forward_test_metrics"]["win_rate_percent"] == "100.00"
    assert comparison["forward_test_metrics"]["trade_count"] == 4
    assert "win_rate_percent" not in comparison["forward_test_metrics"]["missing_reasons"]
    assert "split_metrics" not in comparison
    assert "robustness" not in comparison


@pytest.mark.anyio
async def test_the_comparison_win_rate_has_a_reason_without_a_round_trip_in_the_backtest_period(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_forward_test(web_client)
    write_forward_test_end(database_url, forward_test["id"])
    write_losing_round_trip(database_url, forward_test["id"])
    backtest_id = await start_short_backtest(web_client, database_url, forward_test["strategy_version_id"])

    comparison = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/comparison/{backtest_id}")).json()

    metrics = comparison["forward_test_metrics"]
    assert metrics["win_rate_percent"] is None
    assert metrics["missing_reasons"]["win_rate_percent"] == "No round trips in the backtest period"
    # The other round trip metrics count all fills: the losing round trip.
    assert metrics["average_loss_usd"] == "-12.00"
    assert "average_loss_usd" not in metrics["missing_reasons"]


def fill(minute: int, side: str, price: str) -> BacktestTrade:
    return BacktestTrade(
        time_utc=datetime(2026, 1, 2, 3, minute, tzinfo=UTC),
        side="BUY" if side == "BUY" else "SELL",
        quantity_shares=Decimal(10),
        price_usd=Decimal(price),
        commission_usd=Decimal(0),
    )


def test_a_round_trip_that_starts_before_the_backtest_period_does_not_count_for_the_win_rate() -> None:
    # The first round trip starts at 03:04, before the period. Its SELL at 03:06 is not the start of a short position.
    fills = [fill(4, "BUY", "100"), fill(6, "SELL", "90"), fill(7, "BUY", "100"), fill(8, "SELL", "110")]
    period = TimeRange(start_utc=datetime(2026, 1, 2, 3, 5, tzinfo=UTC), end_utc=datetime(2026, 1, 2, 3, 9, tzinfo=UTC))

    assert calculate_win_rate_in_period(fills, period) == Decimal("100.00")
