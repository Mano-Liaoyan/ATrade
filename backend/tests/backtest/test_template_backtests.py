"""Each rule template runs in a real backtest child on test bars (docs/architecture.md section 17.4, #175).

300 daily bars at 50 come before the start, so each indicator of the templates has a value on the first bar of the
range. The first bar of the range closes at 100 with a high of more than 51, so each entry is true on it.
"""

import httpx
import pytest

from tests.backtest.real_runner import run_backtest_runner, save_test_bars, wait_for_final_status
from tests.backtest.test_rules_backtest import save_bars_before_the_start
from tests.fakes.clock import FixedClock


@pytest.mark.anyio
@pytest.mark.parametrize("template_id", ["s1", "s2", "s3"])
async def test_a_rule_template_runs_in_a_backtest_and_buys(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, template_id: str
) -> None:
    save_test_bars(database_url)
    save_bars_before_the_start(database_url, 300)
    strategy = (await web_client.post("/api/strategies", json={"name": "Template", "start_from": template_id})).json()
    response = await web_client.post(
        "/api/backtests",
        json={
            "strategy_version_id": strategy["versions"][0]["id"],
            "symbol": "BTEST",
            "exchange": "ARCA",
            "currency": "USD",
            "bar_period": "1-DAY",
            "start_utc": "2026-03-01T00:00:00Z",
            "end_utc": "2026-04-01T00:00:00Z",
            "paper_capital_usd": "10000",
        },
    )

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, response.json()["id"])

    assert backtest["status"] == "finished", backtest["error_message"]
    first_trade = backtest["trades"][0]
    # 95% of the equity of 10000 at the close of 100: 95 shares.
    assert (first_trade["time_utc"], first_trade["side"], first_trade["quantity_shares"]) == (
        "2026-03-03T00:00:00Z",
        "BUY",
        "95",
    )
