"""The strategy template runs in a backtest and trades (review finding 2 of #61).

The backtest engine has no data client, so `request_bars` in `on_start` gets no look-back bars. The indicator warms
up on the first bars of the range. This test uses enough bars for that. A backtest with look-back bars before the
start is an open question (docs/architecture/backtest.md section 10.3).
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


def make_wave_bars() -> list[Bar]:
    bars: list[Bar] = []
    for index in range(BAR_COUNT):
        close = Decimal(str(round(100 + 10 * math.sin(2 * math.pi * index / WAVE_PERIOD_BARS), 2)))
        bars.append(
            Bar(
                start_utc=FIRST_BAR_UTC + timedelta(days=index),
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=Decimal(1000),
            )
        )
    return bars


def test_the_template_trades_when_the_range_has_more_bars_than_the_average_period(tmp_path: Path) -> None:
    bars = make_wave_bars()
    request = BacktestRequest(
        strategy_version_id=1,
        instrument=Instrument(symbol="WAVE", exchange="ARCA", currency="USD"),
        bar_period=BarPeriod.ONE_DAY,
        time_range=TimeRange(start_utc=FIRST_BAR_UTC, end_utc=FIRST_BAR_UTC + timedelta(days=BAR_COUNT)),
        paper_capital_usd=Decimal(100000),
    )

    trades = run_strategy_on_bars(code=STRATEGY_TEMPLATE, request=request, bars=bars, work_directory=tmp_path)

    assert len(trades) >= 4
    assert {trade.side for trade in trades} == {"BUY", "SELL"}
