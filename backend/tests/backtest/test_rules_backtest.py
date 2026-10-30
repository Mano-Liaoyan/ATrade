"""The code from rule builder rules runs in a real backtest child on the bars of `tests/backtest/bars/` (#172).

The closes of the 20 bars from 2026-03-02: 100, 102, 104, 106, 108, 110, 108, 106, 104, 102, 100, 98, 96, 98,
100, 102, 104, 106, 108, 110. A market order fills at the close of its bar, at the bar end time (the next day).
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import psycopg
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


async def run_saved_rules(web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, rules: Json) -> Any:
    """Saves the rules as a rule builder version, so the platform knows the indicators of the version."""
    strategy = (await web_client.post("/api/strategies", json={"name": "Rules"})).json()
    version = (await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"rules": rules})).json()
    response = await web_client.post(
        "/api/backtests",
        json={
            "strategy_version_id": version["id"],
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
    return backtest


def save_bars_before_the_start(database_url: str, count: int) -> None:
    """One bar at 50 on each of the `count` days before 2026-03-01, every day (also on weekends)."""
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO ibkr_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES ('BTEST', 'ARCA', 'USD', '1-DAY', %s, 50, 51, 49, 50, 1000)
            """,
            [(datetime(2026, 3, 1, tzinfo=UTC) - timedelta(days=index + 1),) for index in range(count)],
        )


@pytest.mark.anyio
async def test_the_look_back_follows_the_longest_indicator_of_the_rules(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    # SMA(200) needs 200 bars. With the earlier look-back of 60 days, it had no value in the 20 bars of the range,
    # and the strategy never traded. Now the look-back gives the last 200 saved bars at 50, so SMA(200) is 50 on
    # the first bar of the range (close 100), and the strategy buys on it. The order fills at the bar end.
    save_test_bars(database_url)
    save_bars_before_the_start(database_url, 300)
    rules = make_rules(group("all_of", condition(price(), "above", indicator("sma", period=200))))

    backtest = await run_saved_rules(web_client, database_url, clock, rules)

    assert backtest["trades"][0]["time_utc"] == "2026-03-03T00:00:00Z"
    assert backtest["trades"][0]["side"] == "BUY"
    # Look-back bars make no fill and no equity point (section 10.3.1).
    assert backtest["equity_curve"][0]["time_utc"] == "2026-03-03T00:00:00Z"


@pytest.mark.anyio
async def test_without_saved_bars_before_the_start_the_indicators_warm_up_on_the_first_bars(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    # The same behaviour as before: SMA(3) has its first value on the third bar of the range (03-04, close 104),
    # and the order fills at the end of that bar.
    save_test_bars(database_url)
    rules = make_rules(group("all_of", condition(price(), "above", indicator("sma", period=3))))

    backtest = await run_saved_rules(web_client, database_url, clock, rules)

    assert backtest["trades"][0]["time_utc"] == "2026-03-05T00:00:00Z"


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
