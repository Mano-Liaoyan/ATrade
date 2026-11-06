"""A parameter sweep run gets the warm-up of its own indicator length (docs/architecture/backtest.md section 10.3.1)."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from atrade.backtest.backtest_run import find_look_back
from atrade.backtest.backtest_store import BacktestRequest, ParameterValues
from atrade.backtest.strategy_engine_run import StrategyRun, run_strategy_on_bars
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.strategy.rules_code import find_warm_up_bar_count, make_rules_code
from atrade.strategy.strategy_rules import StrategyRules
from atrade.strategy.version_reading import StrategyVersion
from tests.strategy.rules_examples import condition, group, indicator, make_rules, price

START_UTC = datetime(2024, 1, 1, tzinfo=UTC)
RUN_DAYS = 120
WAVE = Instrument(symbol="WAVE", exchange="ARCA", currency="USD")
REQUEST = BacktestRequest(
    strategy_version_id=1,
    instrument=WAVE,
    bar_period=BarPeriod.ONE_DAY,
    time_range=TimeRange(START_UTC, START_UTC + timedelta(days=RUN_DAYS)),
    paper_capital_usd=Decimal(100000),
)


def make_sma_rules(period: int) -> StrategyRules:
    return StrategyRules.model_validate(
        make_rules(group("all_of", condition(price(), "above", indicator("sma", period=period))))
    )


def make_bar(day: int) -> Bar:
    close = Decimal(1000 + day)
    return Bar(START_UTC + timedelta(days=day), close, close + 1, close - 1, close, Decimal(1000000))


def find_first_trade_date(period: int, parameters: ParameterValues | None, work_directory: Path) -> date | None:
    """The first trade of the version with SMA(`period`) and the run `parameters`, with the look-back of the run."""
    rules = make_sma_rules(period)
    version = StrategyVersion(1, 1, "Sweep", 1, make_rules_code(rules), rules)
    bars_before_start = [make_bar(day) for day in range(-300, 0)]
    look_back = find_look_back(BarPeriod.ONE_DAY, version.count_warm_up_bars(parameters))
    run = StrategyRun(
        code=version.make_run_code(parameters),
        request=replace(REQUEST, parameters=parameters),
        starting_cash=REQUEST.paper_capital_usd,
        bars=[make_bar(day) for day in range(RUN_DAYS)],
        look_back_bars=look_back.keep_bars(bars_before_start),
    )
    work_directory.mkdir()
    trades = run_strategy_on_bars(run, work_directory)
    return trades[0].time_utc.date() if trades else None


def test_the_run_parameters_change_the_warm_up_bar_count() -> None:
    assert find_warm_up_bar_count(make_sma_rules(20), {"sma_1_period": 100}) == 100


def test_other_run_parameters_keep_the_warm_up_bar_count() -> None:
    assert find_warm_up_bar_count(make_sma_rules(20), {"position_shares": 5}) == 20


@pytest.mark.parametrize("period", [100, 200])
def test_a_sweep_run_trades_like_a_version_saved_with_the_same_length(period: int, tmp_path: Path) -> None:
    saved = find_first_trade_date(period, None, tmp_path / "saved")
    swept = find_first_trade_date(20, {"sma_1_period": period}, tmp_path / "swept")

    assert saved == swept == date(2024, 1, 2)
