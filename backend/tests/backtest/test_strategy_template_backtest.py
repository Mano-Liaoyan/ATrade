"""The strategy template runs in a backtest and trades (review finding 2 of #61).

`request_bars` in `on_start` gets the look-back bars: saved bars before the backtest start
(docs/architecture/backtest.md section 10.3).
"""

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from atrade.backtest.backtest_store import BacktestRequest
from atrade.backtest.strategy_engine_run import run_strategy_on_bars
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.strategy.strategy_template import STRATEGY_TEMPLATE

FIRST_BAR_UTC = datetime(2026, 1, 1, tzinfo=UTC)
BAR_COUNT = 120
# A price wave with a period of 40 bars crosses its 20-bar moving average up and down several times.
WAVE_PERIOD_BARS = 40
# The template average period is 20 bars. 60 daily look-back bars are its warm-up of 3 average periods.
LOOK_BACK_BAR_COUNT = 60
RANGE_BAR_COUNT = 10


def make_bar(start_utc: datetime, close: Decimal) -> Bar:
    return Bar(start_utc=start_utc, open=close, high=close + 1, low=close - 1, close=close, volume=Decimal(1000))


def make_wave_bars() -> list[Bar]:
    return [
        make_bar(
            FIRST_BAR_UTC + timedelta(days=index),
            Decimal(str(round(100 + 10 * math.sin(2 * math.pi * index / WAVE_PERIOD_BARS), 2))),
        )
        for index in range(BAR_COUNT)
    ]


def make_request(start_utc: datetime, bar_count: int) -> BacktestRequest:
    return BacktestRequest(
        strategy_version_id=1,
        instrument=Instrument(symbol="WAVE", exchange="ARCA", currency="USD"),
        bar_period=BarPeriod.ONE_DAY,
        time_range=TimeRange(start_utc=start_utc, end_utc=start_utc + timedelta(days=bar_count)),
        paper_capital_usd=Decimal(100000),
    )


def test_the_template_trades_when_the_range_has_more_bars_than_the_average_period(tmp_path: Path) -> None:
    trades = run_strategy_on_bars(
        code=STRATEGY_TEMPLATE,
        request=make_request(FIRST_BAR_UTC, BAR_COUNT),
        bars=make_wave_bars(),
        look_back_bars=[],
        work_directory=tmp_path,
    )

    assert len(trades) >= 4
    assert {trade.side for trade in trades} == {"BUY", "SELL"}


def test_the_template_trades_on_the_first_bar_because_look_back_bars_warm_up_the_average(tmp_path: Path) -> None:
    # 60 look-back bars at 100 make the average 100. The first bar of the range closes at 110, above the average.
    start_utc = FIRST_BAR_UTC + timedelta(days=LOOK_BACK_BAR_COUNT)
    look_back_bars = [make_bar(FIRST_BAR_UTC + timedelta(days=index), Decimal(100)) for index in range(60)]
    bars = [make_bar(start_utc + timedelta(days=index), Decimal(110)) for index in range(RANGE_BAR_COUNT)]

    trades = run_strategy_on_bars(
        code=STRATEGY_TEMPLATE,
        request=make_request(start_utc, RANGE_BAR_COUNT),
        bars=bars,
        look_back_bars=look_back_bars,
        work_directory=tmp_path,
    )

    # The order fills at the close of the first bar of the range, at its end. No trade is before the start.
    assert [(trade.time_utc, trade.side, trade.price_usd) for trade in trades] == [
        (start_utc + timedelta(days=1), "BUY", Decimal("110.00"))
    ]


def test_without_look_back_bars_the_template_does_not_trade_on_the_first_bars(tmp_path: Path) -> None:
    start_utc = FIRST_BAR_UTC + timedelta(days=LOOK_BACK_BAR_COUNT)
    bars = [make_bar(start_utc + timedelta(days=index), Decimal(110)) for index in range(RANGE_BAR_COUNT)]

    trades = run_strategy_on_bars(
        code=STRATEGY_TEMPLATE,
        request=make_request(start_utc, RANGE_BAR_COUNT),
        bars=bars,
        look_back_bars=[],
        work_directory=tmp_path,
    )

    assert trades == []
