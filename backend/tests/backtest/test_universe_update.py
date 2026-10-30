"""A strategy gets the universe of each universe period as NautilusTrader custom data (#198).

The platform adds one `UniverseUpdate` for each universe period start to the engine data. The engine sends it to
`on_data` at that time, in time order with the bars. The strategy configuration holds no universe, so the strategy
cannot read a later list (docs/architecture/backtest.md sections 10.10.1 and 10.10.8).
"""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType, CustomData, DataType, Venue, register_custom_data_class
from nautilus_trader.model.custom import customdataclass  # pyright: ignore[reportUnknownVariableType] untyped.
from nautilus_trader.persistence import BarDataWrangler
from nautilus_trader.trading import Strategy

from atrade.backtest.arrow_bars import NANOSECONDS_PER_SECOND, convert_bars_to_arrow_bytes
from atrade.backtest.strategy_engine_run import create_engine, create_instrument
from atrade.foundation.bar import Bar, BarPeriod
from atrade.foundation.instrument import Instrument

UNIVERSE_UPDATE = "UniverseUpdate"
FIRST_PERIOD_START_UTC = datetime(2026, 1, 1, tzinfo=UTC)
SECOND_PERIOD_START_UTC = datetime(2026, 1, 6, tzinfo=UTC)
PERIOD_BAR_COUNT = 5
FIRST_PERIOD_BAR_TYPES = ("AAA.SMART-1-DAY-LAST-EXTERNAL", "BBB.SMART-1-DAY-LAST-EXTERNAL")
SECOND_PERIOD_BAR_TYPES = ("BBB.SMART-1-DAY-LAST-EXTERNAL", "CCC.SMART-1-DAY-LAST-EXTERNAL")


@customdataclass
class UniverseUpdate:
    """The members of one universe period: their bar types, joined with commas."""

    bar_types: str = ""


register_custom_data_class(UniverseUpdate)


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


def to_nanoseconds(time_utc: datetime) -> int:
    return int(time_utc.timestamp()) * NANOSECONDS_PER_SECOND


def make_universe_update(period_start_utc: datetime, bar_types: tuple[str, ...]) -> CustomData:
    time_ns = to_nanoseconds(period_start_utc)
    # readability-exception: the decorator adds the `ts_event` and `ts_init` arguments, and the type checker does
    # not see them.
    update = UniverseUpdate(time_ns, time_ns, bar_types=",".join(bar_types))  # pyright: ignore[reportCallIssue]
    return CustomData(DataType(UNIVERSE_UPDATE), update)


def run_two_universe_periods(work_directory: Path) -> FollowUniverseStrategy:
    engine = create_engine(
        starting_cash=Decimal(10000), currency="USD", venue=Venue("SMART"), work_directory=work_directory
    )
    # The child reads the bars of each instrument only for its universe periods (section 10.10.1).
    member_bars = {
        "AAA": make_bars(FIRST_PERIOD_START_UTC, PERIOD_BAR_COUNT),
        "BBB": make_bars(FIRST_PERIOD_START_UTC, 2 * PERIOD_BAR_COUNT),
        "CCC": make_bars(SECOND_PERIOD_START_UTC, PERIOD_BAR_COUNT),
    }
    for symbol, bars in member_bars.items():
        instrument = create_instrument(Instrument(symbol=symbol, exchange="SMART", currency="USD"), bars)
        engine.add_instrument(instrument)
        wrangler = BarDataWrangler(f"{instrument.id}-1-DAY-LAST-EXTERNAL", instrument.price_precision, 0)
        engine.add_data(wrangler.process_record_batch_bytes(convert_bars_to_arrow_bytes(bars, BarPeriod.ONE_DAY)))
    engine.add_data(
        [
            make_universe_update(FIRST_PERIOD_START_UTC, FIRST_PERIOD_BAR_TYPES),
            make_universe_update(SECOND_PERIOD_START_UTC, SECOND_PERIOD_BAR_TYPES),
        ]
    )
    strategy = FollowUniverseStrategy(UniverseConfig())
    engine.add_strategy(strategy)
    engine.run()
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
