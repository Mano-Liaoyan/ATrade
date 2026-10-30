"""Each code template runs in a real multi-instrument backtest child on the `rule` universe (#202).

The first quarter has AAA and BBB, the second quarter BBB and CCC. So the rebalance of April sells AAA and buys CCC.
"""

from datetime import datetime

import httpx
import pytest

from tests.backtest.real_runner import run_backtest_runner, wait_for_final_status
from tests.backtest.universe_data import make_universe_request, save_universe_test_data
from tests.fakes.clock import FixedClock

# The rebalance orders fill in the first bars of the month. The buys come after the sells fill.
LAST_FILL_DAY_OF_MONTH = 5


@pytest.mark.anyio
@pytest.mark.parametrize("template_id", ["m1", "m2", "m3", "m4"])
async def test_a_code_template_rebalances_at_the_month_start_and_sells_before_it_buys(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, template_id: str
) -> None:
    save_universe_test_data(database_url)
    strategy = (await web_client.post("/api/strategies", json={"name": "Template", "start_from": template_id})).json()
    request = make_universe_request(strategy["versions"][0]["id"], universe_kind="rule", top_n=2)
    response = await web_client.post("/api/backtests", json=request)
    assert response.status_code == 201, response.text

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=120):
        backtest = await wait_for_final_status(web_client, response.json()["id"])

    assert backtest["status"] == "finished", backtest["error_message"]
    trades = [
        (trade["symbol"], trade["side"], datetime.fromisoformat(trade["time_utc"])) for trade in backtest["trades"]
    ]
    assert {(symbol, side) for symbol, side, _ in trades} == {
        ("AAA", "BUY"),
        ("BBB", "BUY"),
        ("AAA", "SELL"),
        ("CCC", "BUY"),
    }
    assert all(time.day <= LAST_FILL_DAY_OF_MONTH for _, _, time in trades), trades
    sell_aaa = next(index for index, (symbol, side, _) in enumerate(trades) if (symbol, side) == ("AAA", "SELL"))
    buy_ccc = next(index for index, (symbol, side, _) in enumerate(trades) if (symbol, side) == ("CCC", "BUY"))
    assert (trades[sell_aaa][2].month, trades[buy_ccc][2].month) == (4, 4)
    # The trades are in the fill order. The buy can fill in the same bar time as the sell, on the bar of CCC.
    assert sell_aaa < buy_ccc
    assert trades[sell_aaa][2] <= trades[buy_ccc][2]
