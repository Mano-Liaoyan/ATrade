"""The code from rule builder rules runs in a real backtest child on the bars of `tests/backtest/bars/` (#172).

The closes of the 20 bars from 2026-03-02: 100, 102, 104, 106, 108, 110, 108, 106, 104, 102, 100, 98, 96, 98,
100, 102, 104, 106, 108, 110. A market order fills at the close of its bar, at the bar end time (the next day).
"""

from pathlib import Path
from typing import Any

import httpx
import pytest

from atrade.backtest.strategy_engine_run import StrategyRun, run_strategy_on_bars
from atrade.strategy.rules_code import make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from tests.backtest.real_runner import run_backtest_runner, save_test_bars, start_backtest, wait_for_final_status
from tests.backtest.test_strategy_template_backtest import (
    BAR_COUNT,
    FIRST_BAR_UTC,
    PAPER_CAPITAL_USD,
    make_request,
    make_wave_bars,
)
from tests.fakes.clock import FixedClock
from tests.strategy.rules_examples import Json, condition, group, indicator, make_rules, number, price


async def run_rules(web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, rules: Json) -> Any:
    save_test_bars(database_url)
    code = make_rules_code(StrategyRules.model_validate(rules))
    backtest_id = await start_backtest(web_client, code, strategy_name="Rules")
    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)
    assert backtest["status"] == "finished", backtest["error_message"]
    return [(trade["time_utc"][:10], trade["side"], trade["quantity_shares"]) for trade in backtest["trades"]]


@pytest.mark.anyio
async def test_a_cross_is_true_only_on_the_bar_of_the_cross(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    # SMA(3) has its first value on 03-04. The close is above it from 03-04 to 03-07, but no bar crosses there.
    # The close crosses above on 03-15 (98 > 97.33). The position closes 2 bars later, on 03-17. The close stays
    # above the average after that, but it does not cross again, so the strategy does not buy again.
    rules = make_rules(
        group("all_of", condition(price(), "crosses_above", indicator("sma", period=3))),
        exits={"exit_after_bars": 2},
    )

    trades = await run_rules(web_client, database_url, clock, rules)

    assert trades == [("2026-03-16", "BUY", "10"), ("2026-03-18", "SELL", "10")]


@pytest.mark.anyio
async def test_no_rule_runs_while_an_indicator_has_no_value(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    # The entry group is true on each bar where SMA(3) has a value: from 03-04 (close 104). 50% of 10000 USD buys
    # 48 shares. The take profit of 5% (109.2) sells the full position on 03-07 (close 110), and the strategy buys
    # again on the next bar: 50% of 10288 USD at 108 is 47 shares.
    rules = make_rules(
        group(
            "all_of",
            condition(price(), "above", number(0)),
            condition(indicator("sma", period=3), "above", number(0)),
        ),
        exits={"take_profit_percent": 5},
        position_size={"type": "percent_of_equity", "percent": 50},
    )

    trades = await run_rules(web_client, database_url, clock, rules)

    assert trades[:3] == [("2026-03-05", "BUY", "48"), ("2026-03-08", "SELL", "48"), ("2026-03-09", "BUY", "47")]


def test_each_exit_item_runs_in_the_engine(tmp_path: Path) -> None:
    # An in-process engine run on a price wave: the code of each exit item runs without an error and trades.
    rules = make_rules(
        group(
            "any_of",
            condition(price(), "crosses_above", indicator("sma", period=5)),
            group("all_of", condition(indicator("rsi", period=5), "below", number(40))),
        ),
        exits={
            "stop_loss_percent": 1,
            "take_profit_percent": 1.5,
            "exit_after_bars": 10,
            "exit_when_entry_is_false": True,
            "exit_group": group(
                "all_of", condition(indicator("bollinger_bands", "upper", period=5), "crosses_below", price("high"))
            ),
        },
        position_size={"type": "percent_of_equity", "percent": 10},
    )
    run = StrategyRun(
        code=make_rules_code(StrategyRules.model_validate(rules)),
        request=make_request(FIRST_BAR_UTC, BAR_COUNT),
        starting_cash=PAPER_CAPITAL_USD,
        bars=make_wave_bars(),
        look_back_bars=[],
    )

    trades = run_strategy_on_bars(run, tmp_path)

    assert [trade.side for trade in trades[:4]] == ["BUY", "SELL", "BUY", "SELL"]
