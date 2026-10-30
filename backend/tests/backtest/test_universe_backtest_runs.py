"""Multi-instrument backtests that run in a real child process (docs/architecture/backtest.md section 10.10).

The test strategy holds 10 shares of each member of the current universe. It warms up an SMA(20) of each new member
on the look-back bars, so it buys on the first bar after the member joins.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.backtest.real_runner import run_backtest_runner, wait_for_final_status
from tests.backtest.test_universe_backtest_routes import read_universe_members
from tests.backtest.universe_data import (
    AAA,
    CCC,
    RANGE_START_UTC,
    SECOND_QUARTER_START_UTC,
    make_universe_request,
    save_universe_test_data,
    to_instrument_body,
)
from tests.fakes.clock import FixedClock

FOLLOW_UNIVERSE_FILE = Path(__file__).parent / "strategies" / "follow_universe.py"
# A buy fills at the close of the first bar after the period start: the bar that starts at the period start.
FIRST_FILL_DELAY = timedelta(days=1)


async def run_universe_backtest(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, **universe: object
) -> dict[str, Any]:
    strategy = (await web_client.post("/api/strategies", json={"name": "Follow universe"})).json()
    code = FOLLOW_UNIVERSE_FILE.read_text()
    version = (await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code})).json()
    response = await web_client.post("/api/backtests", json=make_universe_request(version["id"], **universe))
    assert response.status_code == 201, response.text
    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=120):
        backtest = await wait_for_final_status(web_client, response.json()["id"])
    assert backtest["status"] == "finished", backtest["error_message"]
    return backtest


def read_time(trade: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(trade["time_utc"])


def find_trades(backtest: dict[str, Any], symbol: str) -> list[tuple[str, datetime]]:
    return [(trade["side"], read_time(trade)) for trade in backtest["trades"] if trade["symbol"] == symbol]


@pytest.mark.anyio
async def test_a_rule_backtest_trades_the_members_of_each_quarter_only_in_that_quarter(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_universe_test_data(database_url)

    backtest = await run_universe_backtest(web_client, database_url, clock, universe_kind="rule", top_n=2)

    assert {period for period, _, _ in read_universe_members(database_url, backtest["id"])} == {
        f"{RANGE_START_UTC:%Y-%m-%d}",
        f"{SECOND_QUARTER_START_UTC:%Y-%m-%d}",
    }
    # AAA leaves at the second quarter start, CCC joins then. BBB stays. The look-back bars warm up each new member.
    assert find_trades(backtest, "AAA") == [
        ("BUY", RANGE_START_UTC + FIRST_FILL_DELAY),
        # The sell fills at the last close of AAA: the bar that closes at the second quarter start.
        ("SELL", SECOND_QUARTER_START_UTC),
    ]
    assert find_trades(backtest, "BBB") == [("BUY", RANGE_START_UTC + FIRST_FILL_DELAY)]
    # The strategy cannot read the list of the second quarter in the first quarter.
    assert find_trades(backtest, "CCC") == [("BUY", SECOND_QUARTER_START_UTC + FIRST_FILL_DELAY)]


@pytest.mark.anyio
async def test_the_trades_of_a_universe_backtest_have_the_real_exchange(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_universe_test_data(database_url)

    backtest = await run_universe_backtest(web_client, database_url, clock, universe_kind="rule", top_n=2)

    assert {(trade["symbol"], trade["exchange"]) for trade in backtest["trades"]} == {
        ("AAA", "NASDAQ"),
        ("BBB", "NYSE"),
        ("CCC", "ARCA"),
    }


@pytest.mark.anyio
async def test_a_list_backtest_has_one_period_from_the_start_and_trades_the_list(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_universe_test_data(database_url)
    instruments = [to_instrument_body(AAA), to_instrument_body(CCC)]

    backtest = await run_universe_backtest(
        web_client, database_url, clock, universe_kind="list", instruments=instruments
    )

    assert {period for period, _, _ in read_universe_members(database_url, backtest["id"])} == {
        f"{RANGE_START_UTC:%Y-%m-%d}"
    }
    assert find_trades(backtest, "AAA") == [("BUY", RANGE_START_UTC + FIRST_FILL_DELAY)]
    assert find_trades(backtest, "CCC") == [("BUY", RANGE_START_UTC + FIRST_FILL_DELAY)]
    # 2 positions of 10 shares, valued at the bar close prices: the equity changes with the prices.
    equity_values = {point["equity_usd"] for point in backtest["equity_curve"]}
    assert len(equity_values) > 2
    assert backtest["metrics"]["trade_count"] == 2
