"""The `robustness` object of `GET /api/backtests/{backtest_id}`: the trial count and the probabilistic or deflated
Sharpe ratio (docs/architecture/backtest.md section 10.9.5). The route calculates them at each read.

The tests save finished backtests with SQL, because only the saved rows and equity curves matter here.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest

TEST_STRATEGY_CODE = (Path(__file__).parent / "strategies" / "buy_and_sell_by_bar_count.py").read_text()
PAPER_CAPITAL = Decimal(10000)
# Daily Sharpe ratio 0.33: PSR(0) is 99.44 % (tests/backtest/test_sharpe_probability.py).
GOOD_RETURNS = [Decimal("0.02"), Decimal("-0.01")] * 30


async def save_strategy(web_client: httpx.AsyncClient, name: str) -> int:
    return (await web_client.post("/api/strategies", json={"name": name})).json()["id"]


async def save_version(web_client: httpx.AsyncClient, strategy_id: int, comment: str = "") -> int:
    code = f"{TEST_STRATEGY_CODE}\n# {comment}\n" if comment else TEST_STRATEGY_CODE
    return (await web_client.post(f"/api/strategies/{strategy_id}/versions", json={"code": code})).json()["id"]


@dataclass(frozen=True)
class SavedBacktest:
    strategy_version_id: int
    daily_returns: list[Decimal]
    exchange: str = "ARCA"
    bar_period: str = "1-DAY"
    status: str = "finished"
    start_day: int = 5


def save_backtest(database_url: str, backtest: SavedBacktest) -> int:
    """Saves a backtest with one equity point at 21:00 UTC of each day, so each point gives one daily return."""
    start_utc = datetime(2026, 1, backtest.start_day, tzinfo=UTC)
    equity_usd = PAPER_CAPITAL
    points: list[dict[str, Any]] = []
    for index, daily_return in enumerate(backtest.daily_returns):
        equity_usd *= 1 + daily_return
        points.append({"time_utc": start_utc + timedelta(days=index, hours=21), "equity_usd": equity_usd})
    with psycopg.connect(database_url, autocommit=True) as connection:
        cursor = connection.execute(
            """
            INSERT INTO backtest (strategy_version_id, symbol, exchange, currency, bar_period, start_utc, end_utc,
                paper_capital_usd, status, created_at_utc)
            VALUES (%(strategy_version_id)s, 'BTEST', %(exchange)s, 'USD', %(bar_period)s, %(start_utc)s,
                %(end_utc)s, %(paper_capital_usd)s, %(status)s, %(start_utc)s)
            RETURNING id
            """,
            {
                "strategy_version_id": backtest.strategy_version_id,
                "exchange": backtest.exchange,
                "bar_period": backtest.bar_period,
                "status": backtest.status,
                "start_utc": start_utc,
                "end_utc": start_utc + timedelta(days=len(backtest.daily_returns) + 1),
                "paper_capital_usd": PAPER_CAPITAL,
            },
        )
        row = cursor.fetchone()
        assert row is not None
        backtest_id = int(row[0])
        with connection.cursor() as point_cursor:
            point_cursor.executemany(
                """
                INSERT INTO backtest_equity_point (backtest_id, time_utc, equity_usd)
                VALUES (%(backtest_id)s, %(time_utc)s, %(equity_usd)s)
                """,
                [{"backtest_id": backtest_id, **point} for point in points],
            )
    return backtest_id


async def read_robustness(web_client: httpx.AsyncClient, backtest_id: int) -> dict[str, Any]:
    response = await web_client.get(f"/api/backtests/{backtest_id}")
    assert response.status_code == 200
    return response.json()["robustness"]


@pytest.mark.anyio
async def test_trial_count_counts_the_finished_backtests_of_the_strategy_instrument_and_bar_period(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    strategy_id = await save_strategy(web_client, "Counted")
    first_version_id = await save_version(web_client, strategy_id)
    second_version_id = await save_version(web_client, strategy_id, "version 2")
    other_strategy_version_id = await save_version(web_client, await save_strategy(web_client, "Other"))
    backtest_id = save_backtest(database_url, SavedBacktest(first_version_id, GOOD_RETURNS))
    # Counted: another version of the strategy, with another time range.
    save_backtest(database_url, SavedBacktest(second_version_id, GOOD_RETURNS[:10], start_day=20))
    # Not counted: another instrument, another bar period, a backtest that did not finish, another strategy.
    save_backtest(database_url, SavedBacktest(first_version_id, GOOD_RETURNS, exchange="NYSE"))
    save_backtest(database_url, SavedBacktest(first_version_id, GOOD_RETURNS, bar_period="1-HOUR"))
    save_backtest(database_url, SavedBacktest(first_version_id, GOOD_RETURNS, status="running"))
    save_backtest(database_url, SavedBacktest(first_version_id, [], status="failed"))
    save_backtest(database_url, SavedBacktest(other_strategy_version_id, GOOD_RETURNS))

    robustness = await read_robustness(web_client, backtest_id)

    assert robustness["trial_count"] == 2


@pytest.mark.anyio
async def test_one_trial_gives_the_probabilistic_sharpe_and_two_give_the_deflated_sharpe(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    strategy_id = await save_strategy(web_client, "Deflated")
    version_id = await save_version(web_client, strategy_id)
    backtest_id = save_backtest(database_url, SavedBacktest(version_id, GOOD_RETURNS))

    alone = await read_robustness(web_client, backtest_id)
    save_backtest(database_url, SavedBacktest(version_id, [Decimal("0.012"), Decimal("-0.01")] * 30))
    with_one_more = await read_robustness(web_client, backtest_id)

    assert alone == {
        "trial_count": 1,
        "sharpe_probability_percent": "99.44",
        "sharpe_probability_kind": "probabilistic",
        "sharpe_probability_status": "likely_real",
        "missing_reasons": {},
        "out_of_sample_to_in_sample_sharpe_percent": None,
        "out_of_sample_use_count": None,
    }
    assert with_one_more["trial_count"] == 2
    assert with_one_more["sharpe_probability_kind"] == "deflated"
    assert Decimal(with_one_more["sharpe_probability_percent"]) < Decimal(alone["sharpe_probability_percent"])


@pytest.mark.anyio
async def test_a_later_finished_backtest_makes_the_deflated_sharpe_of_an_earlier_backtest_lower(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    strategy_id = await save_strategy(web_client, "Later")
    version_id = await save_version(web_client, strategy_id)
    backtest_id = save_backtest(database_url, SavedBacktest(version_id, GOOD_RETURNS))
    save_backtest(database_url, SavedBacktest(version_id, [Decimal("0.012"), Decimal("-0.01")] * 30))
    before = await read_robustness(web_client, backtest_id)

    save_backtest(database_url, SavedBacktest(version_id, [Decimal("0.03"), Decimal("-0.01")] * 30, start_day=10))
    after = await read_robustness(web_client, backtest_id)

    assert (before["trial_count"], after["trial_count"]) == (2, 3)
    assert Decimal(after["sharpe_probability_percent"]) < Decimal(before["sharpe_probability_percent"])


@pytest.mark.anyio
async def test_fewer_than_60_daily_returns_give_no_sharpe_probability(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    strategy_id = await save_strategy(web_client, "Short")
    backtest_id = save_backtest(
        database_url, SavedBacktest(await save_version(web_client, strategy_id), GOOD_RETURNS[:59])
    )

    robustness = await read_robustness(web_client, backtest_id)

    assert robustness["sharpe_probability_percent"] is None
    assert robustness["sharpe_probability_status"] is None
    assert robustness["missing_reasons"] == {"sharpe_probability_percent": "Fewer than 60 daily returns"}
