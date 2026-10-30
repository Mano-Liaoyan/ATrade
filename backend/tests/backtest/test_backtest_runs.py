"""Backtests that run in a real child process on the small bar file and the test strategy.

The runner of each test starts real child processes (`python -m atrade.app.backtest_process`). The tests read
the status and the result through the HTTP routes.
"""

from datetime import UTC, datetime, timedelta

import httpx
import psycopg
import pytest

from atrade.strategy.strategy_template import STRATEGY_TEMPLATE
from tests.backtest.real_runner import (
    TEST_STRATEGY_FILE,
    run_backtest_runner,
    save_test_bars,
    start_backtest,
    wait_for_final_status,
)
from tests.fakes.clock import FixedClock


@pytest.mark.anyio
async def test_finished_backtest_shows_metrics_equity_curve_and_trades(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    backtest_id = await start_backtest(web_client, TEST_STRATEGY_FILE.read_text())

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "finished", backtest["error_message"]
    assert backtest["error_message"] is None
    assert backtest["started_at_utc"] == "2026-01-02T03:04:05Z"
    assert backtest["ended_at_utc"] is not None
    # Each market order fills at the close of the bar that sent it: bars 3, 8, and 13 close at 104, 106, and 96.
    assert backtest["trades"] == [
        {
            "time_utc": "2026-03-05T00:00:00Z",
            "side": "BUY",
            "quantity_shares": "10",
            "price_usd": "104.00",
            "commission_usd": "0.00",
            "symbol": "BTEST",
            "exchange": "ARCA",
        },
        {
            "time_utc": "2026-03-10T00:00:00Z",
            "side": "SELL",
            "quantity_shares": "10",
            "price_usd": "106.00",
            "commission_usd": "0.00",
            "symbol": "BTEST",
            "exchange": "ARCA",
        },
        {
            "time_utc": "2026-03-15T00:00:00Z",
            "side": "BUY",
            "quantity_shares": "10",
            "price_usd": "96.00",
            "commission_usd": "0.00",
            "symbol": "BTEST",
            "exchange": "ARCA",
        },
    ]
    # 10000 + 10 * (106 - 104) + 10 * (110 - 96) = 10160. The peak 10060 falls to 10020: 40 / 10060 = 0.40 %.
    assert backtest["metrics"] == {
        "final_equity_usd": "10160.00",
        "total_return_percent": "1.60",
        "max_drawdown_percent": "0.40",
        "trade_count": 3,
        # The range has 31 days: no CAGR and no Calmar ratio. The one round trip has a profit of 20 on 1040.
        "cagr_percent": None,
        "annual_volatility_percent": "2.15",
        "sharpe_ratio": "9.32",
        "sortino_ratio": "20.05",
        "calmar_ratio": None,
        "profit_factor": None,
        "average_win_usd": "20.00",
        "average_win_percent": "1.92",
        "average_loss_usd": None,
        # 13 of the 20 bar ends have a position.
        "exposure_percent": "65.00",
        # Fills of 1040 + 1060 + 960 = 3060, mean equity 10049, 31 / 365.25 years.
        "turnover_per_year": "3.59",
        "win_rate_percent": "100.00",
        "missing_reasons": {
            "cagr_percent": "The range is shorter than 90 days",
            "calmar_ratio": "The range is shorter than 90 days",
            "profit_factor": "No round trip with a loss",
            "average_loss_usd": "No round trip with a loss",
        },
    }
    equity_curve = backtest["equity_curve"]
    assert [point["equity_usd"] for point in equity_curve] == [
        "10000.00", "10000.00", "10000.00", "10020.00", "10040.00", "10060.00", "10040.00", "10020.00",
        "10020.00", "10020.00", "10020.00", "10020.00", "10020.00", "10040.00", "10060.00", "10080.00",
        "10100.00", "10120.00", "10140.00", "10160.00",
    ]  # fmt: skip
    assert equity_curve[0]["time_utc"] == "2026-03-03T00:00:00Z"
    assert equity_curve[-1]["time_utc"] == "2026-03-22T00:00:00Z"


@pytest.mark.anyio
async def test_failed_backtest_shows_the_strategy_error(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    failing_code = TEST_STRATEGY_FILE.read_text().replace(
        "        self.bar_count += 1\n", "        self.bar_count += 1\n        raise ValueError('no trade today')\n"
    )
    backtest_id = await start_backtest(web_client, failing_code)

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "failed"
    assert "ValueError: no trade today" in backtest["error_message"]
    assert "in on_bar" in backtest["error_message"]
    assert backtest["metrics"] is None


@pytest.mark.anyio
async def test_backtest_without_saved_bars_fails_with_a_clear_message(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    # The start route refuses a backtest without saved bars. The child checks again, because it reads the bars later.
    save_test_bars(database_url)
    backtest_id = await start_backtest(web_client, TEST_STRATEGY_FILE.read_text())
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("DELETE FROM ibkr_bar")

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "failed"
    assert backtest["error_message"] == (
        "There are no saved 1 day bars of BTEST / ARCA / USD from 2026-03-01 00:00 UTC to 2026-04-01 00:00 UTC."
        " ATrade saves bars when a bar chart loads them from IBKR and when a forward test receives them."
        " IBKR has bars only for the regular trading hours: a period when the market was closed has no bars."
        " Open the bar chart of the instrument with this bar period to load the bars, or select a period with"
        " trading hours."
    )


@pytest.mark.anyio
async def test_the_template_warms_up_on_saved_bars_before_the_start(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    # 59 saved bars at 50 before the start (2026-03-01) make the 20-bar average 50. The first bar of the range
    # closes at 100, above the average, so the template buys on it. Without look-back bars the average is not ready.
    save_test_bars(database_url)
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO ibkr_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES ('BTEST', 'ARCA', 'USD', '1-DAY', %s, 50, 51, 49, 50, 1000)
            """,
            [(datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index),) for index in range(59)],
        )
    backtest_id = await start_backtest(web_client, STRATEGY_TEMPLATE, strategy_name="Template")

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "finished", backtest["error_message"]
    assert backtest["trades"][0] == {
        "time_utc": "2026-03-03T00:00:00Z",
        "side": "BUY",
        "quantity_shares": "10",
        "price_usd": "100.00",
        "commission_usd": "0.00",
        "symbol": "BTEST",
        "exchange": "ARCA",
    }
    # The equity curve starts at the first bar of the range: look-back bars make no equity point.
    assert backtest["equity_curve"][0]["time_utc"] == "2026-03-03T00:00:00Z"
