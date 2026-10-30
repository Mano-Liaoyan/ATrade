"""`screen` universe backtests that run in a real child process: the child runs the copy of the screen at each
period start and records the members of each period (docs/architecture/backtest.md sections 10.10.2 and 10.10.8).

The closes of the test bars go up by 1 each day. The screen keeps the instruments with a close above 520: the last
close before 2026-02-02 is 499, before 2026-03-01 it is 527. So the first period has no member.
"""

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from tests.backtest.real_runner import run_backtest_runner, wait_for_final_status
from tests.backtest.test_screen_universe_routes import start_screen_backtest
from tests.backtest.test_universe_backtest_routes import read_universe_members
from tests.backtest.test_universe_backtest_runs import FIRST_FILL_DELAY, FOLLOW_UNIVERSE_FILE, find_trades
from tests.backtest.universe_data import AAA, BBB, CCC, SECOND_QUARTER_START_UTC, save_universe_test_data
from tests.fakes.clock import FixedClock
from tests.screen.test_screen_run_routes import add_to_watchlist, create_screen, make_definition

MARCH_START_UTC = datetime(2026, 3, 1, tzinfo=UTC)


async def run_screen_backtest(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, rebalance_period: str
) -> dict[str, Any]:
    save_universe_test_data(database_url)
    add_to_watchlist(database_url, AAA, BBB, CCC)
    definition = make_definition(filters=[{"field": "last_price", "operator": ">", "value": "520"}])
    screen_id = await create_screen(web_client, definition)
    strategy = (await web_client.post("/api/strategies", json={"name": "Follow universe"})).json()
    code = FOLLOW_UNIVERSE_FILE.read_text()
    version = (await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code})).json()
    response = await start_screen_backtest(
        web_client, version["id"], screen_id=screen_id, rebalance_period=rebalance_period
    )
    assert response.status_code == 201, response.text
    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=120):
        backtest = await wait_for_final_status(web_client, response.json()["id"])
    assert backtest["status"] == "finished", backtest["error_message"]
    return backtest


def all_members(day: datetime) -> list[tuple[str, str, str]]:
    return [(f"{day:%Y-%m-%d}", member.symbol, member.exchange) for member in (AAA, BBB, CCC)]


@pytest.mark.anyio
async def test_a_quarterly_screen_backtest_runs_the_screen_at_each_quarter_start(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    backtest = await run_screen_backtest(web_client, database_url, clock, "quarter")

    # The first period (the range start) has no member, so it has no row.
    assert read_universe_members(database_url, backtest["id"]) == all_members(SECOND_QUARTER_START_UTC)
    # The strategy gets the list of the second quarter only at its start.
    for symbol in ("AAA", "BBB", "CCC"):
        assert find_trades(backtest, symbol) == [("BUY", SECOND_QUARTER_START_UTC + FIRST_FILL_DELAY)]


@pytest.mark.anyio
async def test_a_monthly_screen_backtest_runs_the_screen_at_each_month_start(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    backtest = await run_screen_backtest(web_client, database_url, clock, "month")

    assert read_universe_members(database_url, backtest["id"]) == [
        *all_members(MARCH_START_UTC),
        *all_members(SECOND_QUARTER_START_UTC),
    ]
    for symbol in ("AAA", "BBB", "CCC"):
        assert find_trades(backtest, symbol) == [("BUY", MARCH_START_UTC + FIRST_FILL_DELAY)]
