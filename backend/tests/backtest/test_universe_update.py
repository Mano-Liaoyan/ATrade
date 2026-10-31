"""A strategy gets the universe of each universe period as NautilusTrader custom data (#198).

The decision and the reason are in docs/architecture/backtest.md section 10.10.8. The platform class is in
`atrade/backtest/universe_update.py`.
"""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType, CustomData, DataType, Venue
from nautilus_trader.persistence import BarDataWrangler
from nautilus_trader.trading import Strategy

from atrade.backtest.arrow_bars import convert_bars_to_arrow_bytes
from atrade.backtest.strategy_engine_run import create_engine, create_instrument
from atrade.backtest.universe_update import UNIVERSE_UPDATE, make_universe_update
from atrade.foundation.bar import Bar, BarPeriod
from atrade.foundation.instrument import Instrument

FIRST_PERIOD_START_UTC = datetime(2026, 1, 1, tzinfo=UTC)
SECOND_PERIOD_START_UTC = datetime(2026, 1, 6, tzinfo=UTC)
PERIOD_BAR_COUNT = 5
FIRST_PERIOD_BAR_TYPES = ("AAA.SMART-1-DAY-LAST-EXTERNAL", "BBB.SMART-1-DAY-LAST-EXTERNAL")
SECOND_PERIOD_BAR_TYPES = ("BBB.SMART-1-DAY-LAST-EXTERNAL", "CCC.SMART-1-DAY-LAST-EXTERNAL")


class UniverseConfig(StrategyConfig):
    """A multi-instrument strategy configuration has no `instrument_id` and no `bar_type`."""


class FollowUniverseStrategy(Strategy):
    """Subscribes to the bars of each new member and records what it knows at each bar."""

    def __init__(self, config: UniverseConfig) -> None:
        super().__init__(config)
        self.lists: list[tuple[str, ...]] = []
        self.lists_known_at_bar: list[tuple[datetime, str, list[tuple[str, ...]]]] = []

    def on_start(self) -> None:
        self.subscribe_data(DataType(UNIVERSE_UPDATE))

    def on_data(self, data: object) -> None:
        assert isinstance(data, CustomData)
        assert data.data_type.type_name == UNIVERSE_UPDATE
        bar_types = tuple(str(data.data.bar_types).split(","))
        for bar_type in self.lists[-1] if self.lists else ():
            if bar_type not in bar_types:
                self.unsubscribe_bars(BarType.from_str(bar_type))
        for bar_type in bar_types:
            self.subscribe_bars(BarType.from_str(bar_type))
        self.lists.append(bar_types)

    def on_bar(self, bar: NautilusBar) -> None:
        self.lists_known_at_bar.append((self.clock.utc_now(), str(bar.bar_type), list(self.lists)))


def make_bars(first_start_utc: datetime, count: int) -> list[Bar]:
    return [
        Bar(
            start_utc=first_start_utc + timedelta(days=index),
            open=Decimal(100),
            high=Decimal(101),
            low=Decimal(99),
            close=Decimal(100),
            volume=Decimal(1000),
        )
        for index in range(count)
    ]


def run_two_universe_periods(work_directory: Path) -> FollowUniverseStrategy:
    engine = create_engine(
        starting_cash=Decimal(10000), currency="USD", venue=Venue("SMART"), work_directory=work_directory
    )
    # The child reads the bars of each instrument only for its universe periods (section 10.10.1).
    member_bars = {
        # AAA has bars in the second period too, so the test shows that the strategy unsubscribes from them.
        "AAA": make_bars(FIRST_PERIOD_START_UTC, 2 * PERIOD_BAR_COUNT),
        "BBB": make_bars(FIRST_PERIOD_START_UTC, 2 * PERIOD_BAR_COUNT),
        "CCC": make_bars(SECOND_PERIOD_START_UTC, PERIOD_BAR_COUNT),
    }
    for symbol, bars in member_bars.items():
        instrument = create_instrument(Instrument(symbol=symbol, exchange="SMART", currency="USD"), bars)
        engine.add_instrument(instrument)
        wrangler = BarDataWrangler(f"{instrument.id}-1-DAY-LAST-EXTERNAL", instrument.price_precision, 0)
        engine.add_data(wrangler.process_record_batch_bytes(convert_bars_to_arrow_bytes(bars, BarPeriod.ONE_DAY)))
    # Data with the same time comes in the order of the `add_data` calls. The bars come first, so the bar that closes
    # at a period start comes before the list of that period (section 10.10.3).
    engine.add_data(
        [
            make_universe_update(FIRST_PERIOD_START_UTC, list(FIRST_PERIOD_BAR_TYPES)),
            make_universe_update(SECOND_PERIOD_START_UTC, list(SECOND_PERIOD_BAR_TYPES)),
        ]
    )
    strategy = FollowUniverseStrategy(UniverseConfig())
    engine.add_strategy(strategy)
    engine.run()
    engine.dispose()
    return strategy


def test_the_strategy_gets_the_new_list_and_the_bars_of_the_new_members_at_the_second_period_start(
    tmp_path: Path,
) -> None:
    strategy = run_two_universe_periods(tmp_path)

    assert strategy.lists == [FIRST_PERIOD_BAR_TYPES, SECOND_PERIOD_BAR_TYPES]
    second_period_bar_types = {
        bar_type for time_utc, bar_type, _ in strategy.lists_known_at_bar if time_utc > SECOND_PERIOD_START_UTC
    }
    assert second_period_bar_types == set(SECOND_PERIOD_BAR_TYPES)


def test_the_strategy_cannot_read_the_second_list_in_the_first_period(tmp_path: Path) -> None:
    strategy = run_two_universe_periods(tmp_path)

    first_period_records = [
        (bar_type, lists)
        for time_utc, bar_type, lists in strategy.lists_known_at_bar
        if time_utc <= SECOND_PERIOD_START_UTC
    ]
    # A daily bar has the time of its close: 5 bars of AAA and of BBB close in the first period.
    assert len(first_period_records) == 2 * PERIOD_BAR_COUNT
    assert {bar_type for bar_type, _ in first_period_records} == set(FIRST_PERIOD_BAR_TYPES)
    assert all(lists == [FIRST_PERIOD_BAR_TYPES] for _, lists in first_period_records)
