"""The bars of `request_bars` go to `on_historical_bars`, not to `on_historical_data`, also for a member that joins
after the backtest start (docs/architecture/assistant.md, the warm-up handler rule)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from atrade.backtest.backtest_store import UniversePeriod
from atrade.backtest.backtest_universe import MemberBars
from atrade.backtest.strategy_engine_run import StrategyFailedError
from atrade.backtest.universe_engine_run import UniverseRun, run_universe_strategy
from atrade.foundation.bar import Bar, BarPeriod
from atrade.foundation.instrument import Instrument
from tests.backtest.universe_data import AAA, CCC

START_UTC = datetime(2026, 1, 1, tzinfo=UTC)
SECOND_QUARTER_UTC = datetime(2026, 4, 1, tzinfo=UTC)
END_UTC = datetime(2026, 6, 30, tzinfo=UTC)
LOOK_BACK_DAYS = 365

# The strategy reports its counts in the error of on_stop: a backtest gives the strategy no other output.
COUNT_HANDLER_CALLS_CODE = """
from datetime import timedelta

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import BarType, DataType
from nautilus_trader.trading import Strategy


class CountHandlerCallsConfig(StrategyConfig):
    pass


class CountHandlerCallsStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.names = set()
        self.data_call_count = 0
        self.bar_counts = []

    def on_start(self):
        self.subscribe_data(DataType("UniverseUpdate"))

    def on_data(self, data):
        for name in str(data.data.bar_types).split(","):
            if name and name not in self.names:
                self.names.add(name)
                self.request_bars(BarType.from_str(name), start=self.clock.utc_now() - timedelta(days=365))
                self.subscribe_bars(BarType.from_str(name))

    def on_historical_data(self, data):
        self.data_call_count += 1

    def on_historical_bars(self, bars):
        self.bar_counts.append(f"{bars[0].bar_type.instrument_id.symbol} {len(bars)} {self.clock.utc_now():%Y-%m-%d}")

    def on_stop(self):
        raise RuntimeError(f"on_historical_data={self.data_call_count} on_historical_bars={self.bar_counts}")
"""


def day_bars(first_utc: datetime, last_utc: datetime) -> list[Bar]:
    price = Decimal(10)
    return [
        Bar(start_utc=first_utc + timedelta(days=index), open=price, high=price, low=price, close=price, volume=price)
        for index in range((last_utc - first_utc).days)
    ]


def make_member(instrument: Instrument, join_utc: datetime) -> MemberBars:
    return MemberBars(
        instrument=instrument,
        bars=day_bars(join_utc, END_UTC),
        look_back_bars=day_bars(join_utc - timedelta(days=LOOK_BACK_DAYS), join_utc),
        open_bars=day_bars(START_UTC, END_UTC),
    )


def test_request_bars_gives_the_look_back_bars_to_on_historical_bars(tmp_path: Path) -> None:
    run = UniverseRun(
        code=COUNT_HANDLER_CALLS_CODE,
        bar_period=BarPeriod.ONE_DAY,
        currency="USD",
        starting_cash=Decimal(100000),
        members=[make_member(AAA, START_UTC), make_member(CCC, SECOND_QUARTER_UTC)],
        periods=[
            UniversePeriod(start_utc=START_UTC, members=[AAA]),
            UniversePeriod(start_utc=SECOND_QUARTER_UTC, members=[AAA, CCC]),
        ],
    )

    with pytest.raises(StrategyFailedError) as error:
        run_universe_strategy(run, tmp_path)

    assert "on_historical_data=0 on_historical_bars=['AAA 365 2026-01-01', 'CCC 365 2026-04-01']" in str(error.value)
