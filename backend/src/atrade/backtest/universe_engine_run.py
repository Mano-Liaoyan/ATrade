"""Runs a multi-instrument strategy on the bars of its universe members in the NautilusTrader backtest engine
(docs/architecture/backtest.md section 10.10.4).

All members are on one simulated venue SMART with one cash account (ADR 0003). The strategy gets the list of each
universe period as `UniverseUpdate` custom data (section 10.10.8).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Final

from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import CustomData, Equity, TradeTick, Venue
from nautilus_trader.persistence import DataCatalogConfig, ParquetDataCatalog

from atrade.backtest.arrow_bars import convert_bars_to_arrow_bytes
from atrade.backtest.backtest_metrics import BacktestTrade
from atrade.backtest.backtest_store import ParameterValues, UniversePeriod
from atrade.backtest.backtest_universe import MemberBars
from atrade.backtest.strategy_engine_run import (
    CATALOG_FIRST_NS,
    CATALOG_LAST_NS,
    LOOK_BACK_CATALOG_DIRECTORY_NAME,
    EngineInputs,
    create_engine,
    create_instrument,
    create_wrangler,
    make_last_close_tick,
    make_open_ticks,
    read_trades,
    run_engine,
)
from atrade.backtest.universe_update import make_universe_update
from atrade.foundation.bar import BarPeriod
from atrade.foundation.instrument import Instrument

SIMULATED_VENUE: Final = Venue("SMART")


@dataclass(frozen=True)
class UniverseRun:
    """The inputs of one engine run. The account starts with `starting_cash` in `currency`."""

    code: str
    bar_period: BarPeriod
    currency: str
    starting_cash: Decimal
    members: list[MemberBars]
    periods: list[UniversePeriod]
    # The parameter values of a parameter sweep run (docs/architecture/backtest.md 10.11.2).
    parameters: ParameterValues = field(default_factory=dict[str, int | float | bool])


def find_bar_type_name(instrument: Instrument, bar_period: BarPeriod) -> str:
    return bar_period.external_bar_type(f"{instrument.symbol}.{SIMULATED_VENUE}")


@dataclass(frozen=True)
class MemberData:
    bars: list[NautilusBar]
    look_back_bars: list[NautilusBar]


def make_universe_updates(run: UniverseRun) -> list[CustomData]:
    return [
        make_universe_update(
            period.start_utc, [find_bar_type_name(member, run.bar_period) for member in period.members]
        )
        for period in run.periods
    ]


def create_universe_catalog(look_back_bars: list[list[NautilusBar]], work_directory: Path) -> DataCatalogConfig:
    """One catalog with the look-back bars of all members. A request gets only the bars up to the engine time."""
    catalog_path = work_directory / LOOK_BACK_CATALOG_DIRECTORY_NAME
    catalog_path.mkdir()
    catalog = ParquetDataCatalog(str(catalog_path))
    for member_bars in look_back_bars:
        if member_bars:
            catalog.write_bars(member_bars, start=CATALOG_FIRST_NS, end=CATALOG_LAST_NS)
    return DataCatalogConfig(str(catalog_path))


def run_universe_strategy(
    run: UniverseRun, work_directory: Path, changed_orders: list[str] | None = None
) -> list[BacktestTrade]:
    """Returns the trades of the strategy on the bars of all members, in `run.currency`, with the real exchange.

    `changed_orders` gets the lines of the fill warning. Raises StrategyFailedError with the strategy error.
    """
    instruments: list[Equity] = []
    member_data: list[MemberData] = []
    open_ticks: list[list[TradeTick]] = []
    last_close_ticks: list[TradeTick] = []
    for member in run.members:
        all_bars = member.look_back_bars + member.bars
        if not all_bars:
            continue
        # The open bars of the whole range hold more bars than `all_bars`: their prices also need a precision.
        nautilus_instrument = create_instrument(member.instrument, all_bars + member.open_bars, SIMULATED_VENUE)
        open_ticks.append(make_open_ticks(nautilus_instrument, member.open_bars))
        if member.open_bars:
            last_close_ticks.append(make_last_close_tick(nautilus_instrument, member.open_bars, run.bar_period))
        wrangler = create_wrangler(nautilus_instrument, run.bar_period, all_bars)
        instruments.append(nautilus_instrument)
        member_data.append(
            MemberData(
                bars=wrangler.process_record_batch_bytes(convert_bars_to_arrow_bytes(member.bars, run.bar_period))
                if member.bars
                else [],
                look_back_bars=wrangler.process_record_batch_bytes(
                    convert_bars_to_arrow_bytes(member.look_back_bars, run.bar_period)
                )
                if member.look_back_bars
                else [],
            )
        )
    engine = create_engine(
        starting_cash=run.starting_cash,
        currency=run.currency,
        venue=SIMULATED_VENUE,
        look_back_catalog=create_universe_catalog([data.look_back_bars for data in member_data], work_directory),
        work_directory=work_directory,
    )
    for nautilus_instrument in instruments:
        engine.add_instrument(nautilus_instrument)
    for data in member_data:
        if data.bars:
            engine.add_data(data.bars)
    # Data with the same time comes in the order of the `add_data` calls. The bars come first, so the bar that closes
    # at a period start comes before the list of that period (section 10.10.3).
    engine.add_data(make_universe_updates(run))
    run_engine(
        engine,
        EngineInputs(run.code, dict(run.parameters), open_ticks, last_close_ticks, changed_orders),
        work_directory,
    )
    return read_trades(engine, {member.instrument.symbol: member.instrument.exchange for member in run.members})
