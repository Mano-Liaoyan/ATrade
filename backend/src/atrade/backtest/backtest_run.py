"""One backtest from start to end, in the backtest child process: read the inputs, run, and save the result.

The child gets only the backtest ID. It reads the request, the strategy version, and the bars from PostgreSQL.
"""

import asyncio
import tempfile
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import psycopg

from atrade.backtest import backtest_store
from atrade.backtest.backtest_access import describe_missing_bars
from atrade.backtest.backtest_exchange_rates import (
    USD,
    DailyExchangeRates,
    convert_equity_curve_to_usd,
    convert_paper_capital,
    convert_trades_to_usd,
    describe_missing_start_rate,
    read_daily_exchange_rates,
)
from atrade.backtest.backtest_metrics import (
    BacktestTrade,
    EquityPoint,
    calculate_equity_curve,
    calculate_metrics,
    calculate_universe_equity_curve,
)
from atrade.backtest.backtest_store import BacktestRequest, BacktestResult, UniversePeriod
from atrade.backtest.backtest_universe import (
    UniverseBars,
    describe_missing_universe_bars,
    find_universe_look_back_length,
    read_universe_bars,
    run_screen_periods,
)
from atrade.backtest.strategy_engine_run import (
    StrategyFailedError,
    StrategyRun,
    read_currency_precision,
    run_strategy_on_bars,
)
from atrade.backtest.universe_engine_run import UniverseRun, run_universe_strategy
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.clock import Clock
from atrade.market_data import BarRequest, BarSource, read_saved_bars, read_source_order
from atrade.strategy import read_strategy_version

# The default look-back is the warm-up of the strategy template: 3 average periods of its default 20 bars, and
# 1 week at least (docs/architecture/backtest.md section 10.3.1). A strategy without rules gets only these bars.
LOOK_BACK_AVERAGE_PERIOD_BARS = 20
LOOK_BACK_AVERAGE_PERIODS = 3
MIN_LOOK_BACK_LENGTH = timedelta(days=7)
# A daily bar comes on about 252 of 365 days, and an intraday bar only in the trading hours (about 6.5 of 24 hours
# on 5 of 7 days). The read range for a bar count is this many bar lengths per bar, so that it holds the bars.
DAILY_CALENDAR_FACTOR = 2
INTRADAY_CALENDAR_FACTOR = 6


@dataclass(frozen=True)
class LookBack:
    """The bars before the start that answer `request_bars` of the strategy (section 10.3.1).

    The read range goes `length` back from the start. With a `bar_count`, only the last bars of this count stay: the
    bars that the longest indicator of the rules needs (#164).
    """

    length: timedelta
    bar_count: int | None

    def keep_bars(self, bars: list[Bar]) -> list[Bar]:
        return bars if self.bar_count is None else bars[-self.bar_count :]


def find_look_back(bar_period: BarPeriod, warm_up_bar_count: int | None = None) -> LookBack:
    """The look-back of a strategy version. `warm_up_bar_count` is the bar count of the longest indicator of the
    rules, or None for a version without rules: then the look-back is the default length and keeps all bars.
    """
    default_length = max(
        bar_period.length * LOOK_BACK_AVERAGE_PERIOD_BARS * LOOK_BACK_AVERAGE_PERIODS, MIN_LOOK_BACK_LENGTH
    )
    if warm_up_bar_count is None:
        return LookBack(length=default_length, bar_count=None)
    factor = DAILY_CALENDAR_FACTOR if bar_period == BarPeriod.ONE_DAY else INTRADAY_CALENDAR_FACTOR
    return LookBack(
        length=max(bar_period.length * warm_up_bar_count * factor, default_length), bar_count=warm_up_bar_count
    )


@dataclass(frozen=True)
class UniverseInputs:
    periods: list[UniversePeriod]
    bars: UniverseBars


@dataclass(frozen=True)
class BacktestInputs:
    request: BacktestRequest
    code: str
    # The bars of a single-instrument backtest. Empty for a multi-instrument backtest: then `universe` has the bars.
    bars: list[Bar]
    look_back_bars: list[Bar]
    bar_count_by_source: dict[BarSource, int]
    # None for a USD instrument or universe.
    exchange_rates: DailyExchangeRates | None
    universe: UniverseInputs | None = None

    @property
    def has_bars(self) -> bool:
        if self.universe is None:
            return bool(self.bars)
        return any(member.bars for member in self.universe.bars.members)


async def read_universe_inputs(
    *, database_url: str, backtest_id: int, request: BacktestRequest, source_order: list[BarSource], look_back: LookBack
) -> UniverseInputs:
    universe = request.universe
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        if universe is not None and universe.screen is not None and universe.rebalance_period is not None:
            # A `screen` universe: the child runs the copy of the screen at each period start, then records the
            # members for the Instruments tab (docs/architecture/backtest.md section 10.10.8).
            periods = await run_screen_periods(
                database_url=database_url,
                screen=universe.screen,
                rebalance_period=universe.rebalance_period,
                time_range=request.time_range,
            )
            await backtest_store.replace_universe_members(connection, backtest_id=backtest_id, universe_periods=periods)
        else:
            periods = await backtest_store.select_universe_periods(
                connection, backtest_id=backtest_id, currency=request.currency
            )
    bars = await read_universe_bars(
        database_url=database_url,
        request=request,
        periods=periods,
        source_order=source_order,
        look_back_length=find_universe_look_back_length(request.bar_period, look_back.length),
    )
    return UniverseInputs(periods=periods, bars=bars)


async def read_single_inputs(
    *, request: BacktestRequest, database_url: str, source_order: list[BarSource], look_back: LookBack
) -> tuple[list[Bar], list[Bar], dict[BarSource, int]]:
    """The bars of the range, the look-back bars, and the bar count of each bar source in the range."""
    saved_bars = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(
            instrument=request.single_instrument, bar_period=request.bar_period, time_range=request.time_range
        ),
        source_order=source_order,
    )
    start_utc = request.time_range.start_utc
    saved_look_back_bars = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(
            instrument=request.single_instrument,
            bar_period=request.bar_period,
            time_range=TimeRange(start_utc=start_utc - look_back.length, end_utc=start_utc),
        ),
        source_order=source_order,
    )
    return saved_bars.bars, look_back.keep_bars(saved_look_back_bars.bars), saved_bars.bar_counts


async def read_backtest_inputs(*, database_url: str, backtest_id: int) -> BacktestInputs:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        row = await backtest_store.select_backtest(connection, backtest_id)
    if row is None:
        message = f"Backtest {backtest_id} does not exist."
        raise LookupError(message)
    request = backtest_store.read_request(row)
    strategy_version = await read_strategy_version(
        database_url=database_url, strategy_version_id=request.strategy_version_id
    )
    if strategy_version is None:
        message = f"Strategy version {request.strategy_version_id} does not exist."
        raise LookupError(message)
    # Only saved bars: a backtest does not depend on IB Gateway or its rate limits (docs/architecture.md section 10).
    # The source order of the backtest. Only a row from before the source order has none: then the global source
    # order (docs/architecture/backtest.md section 10.12).
    source_order = request.source_order or await read_source_order(database_url=database_url)
    look_back = find_look_back(request.bar_period, strategy_version.warm_up_bar_count)
    exchange_rates = (
        None if request.currency == USD else await read_daily_exchange_rates(database_url=database_url, request=request)
    )
    if request.universe is not None:
        universe = await read_universe_inputs(
            database_url=database_url,
            backtest_id=backtest_id,
            request=request,
            source_order=source_order,
            look_back=look_back,
        )
        return BacktestInputs(
            request=request,
            code=strategy_version.code,
            bars=[],
            look_back_bars=[],
            bar_count_by_source=universe.bars.bar_count_by_source,
            exchange_rates=exchange_rates,
            universe=universe,
        )
    bars, look_back_bars, bar_count_by_source = await read_single_inputs(
        request=request, database_url=database_url, source_order=source_order, look_back=look_back
    )
    return BacktestInputs(
        request=request,
        code=strategy_version.code,
        bars=bars,
        look_back_bars=look_back_bars,
        bar_count_by_source=bar_count_by_source,
        exchange_rates=exchange_rates,
    )


@dataclass(frozen=True)
class BacktestJob:
    database_url: str
    backtest_id: int
    clock: Clock


async def save_failure(job: BacktestJob, error_message: str) -> None:
    async with await psycopg.AsyncConnection.connect(job.database_url, autocommit=True) as connection:
        await backtest_store.save_failure(
            connection,
            backtest_id=job.backtest_id,
            error_message=error_message,
            ended_at_utc=job.clock.read_now_utc(),
        )


def run_single_instrument(
    inputs: BacktestInputs, starting_cash: Decimal, work_directory: Path
) -> tuple[list[BacktestTrade], list[EquityPoint]]:
    """The trades and the equity curve in the instrument currency."""
    request = inputs.request
    run = StrategyRun(
        code=inputs.code,
        request=request,
        starting_cash=starting_cash,
        bars=inputs.bars,
        look_back_bars=inputs.look_back_bars,
    )
    trades = run_strategy_on_bars(run, work_directory)
    equity_curve = calculate_equity_curve(
        start_cash=starting_cash, bars=inputs.bars, bar_period=request.bar_period, trades=trades
    )
    return trades, equity_curve


def run_universe(
    inputs: BacktestInputs, universe: UniverseInputs, starting_cash: Decimal, work_directory: Path
) -> tuple[list[BacktestTrade], list[EquityPoint]]:
    """The trades and the equity curve in the universe currency: the cash plus all positions at the bar closes."""
    request = inputs.request
    run = UniverseRun(
        code=inputs.code,
        bar_period=request.bar_period,
        currency=request.currency,
        starting_cash=starting_cash,
        members=universe.bars.members,
        periods=universe.periods,
        parameters=request.parameters or {},
    )
    trades = run_universe_strategy(run, work_directory)
    equity_curve = calculate_universe_equity_curve(
        start_cash=starting_cash,
        bars_by_instrument={
            (member.instrument.symbol, member.instrument.exchange): member.bars for member in universe.bars.members
        },
        bar_period=request.bar_period,
        trades=trades,
    )
    return trades, equity_curve


async def save_result(job: BacktestJob, inputs: BacktestInputs, starting_cash: Decimal, work_directory: Path) -> None:
    """Runs the strategy with `starting_cash` in the backtest currency and saves the result in USD."""
    request = inputs.request
    try:
        if inputs.universe is None:
            trades, equity_curve = run_single_instrument(inputs, starting_cash, work_directory)
        else:
            trades, equity_curve = run_universe(inputs, inputs.universe, starting_cash, work_directory)
    except StrategyFailedError as error:
        # readability-exception: the engine reports a strategy error only as an exception (G1).
        await save_failure(job, str(error))
        return
    if inputs.exchange_rates is not None:
        equity_curve = convert_equity_curve_to_usd(inputs.exchange_rates, equity_curve)
        trades = convert_trades_to_usd(inputs.exchange_rates, trades)
    metrics = calculate_metrics(
        paper_capital_usd=request.paper_capital_usd,
        time_range=request.time_range,
        equity_curve=equity_curve,
        trades=trades,
    )
    async with await psycopg.AsyncConnection.connect(job.database_url, autocommit=True) as connection:
        await backtest_store.save_result(
            connection,
            backtest_id=job.backtest_id,
            result=BacktestResult(
                equity_curve=equity_curve,
                trades=trades,
                metrics=metrics,
                bar_count_by_source=inputs.bar_count_by_source,
            ),
            ended_at_utc=job.clock.read_now_utc(),
        )


def find_starting_cash(inputs: BacktestInputs) -> Decimal | None:
    """The paper capital in the backtest currency, or None without a rate at the start (section 10.8)."""
    request = inputs.request
    if inputs.exchange_rates is None:
        return request.paper_capital_usd
    usd_per_unit = inputs.exchange_rates.find_usd_per_unit(request.time_range.start_utc)
    if usd_per_unit is None:
        return None
    return convert_paper_capital(request.paper_capital_usd, usd_per_unit, read_currency_precision(request.currency))


def describe_no_bars(request: BacktestRequest) -> str:
    if request.universe is None:
        return describe_missing_bars(request)
    return describe_missing_universe_bars(request)


async def run_backtest_steps(job: BacktestJob) -> None:
    inputs = await read_backtest_inputs(database_url=job.database_url, backtest_id=job.backtest_id)
    if not inputs.has_bars:
        await save_failure(job, describe_no_bars(inputs.request))
        return
    starting_cash = find_starting_cash(inputs)
    if starting_cash is None:
        await save_failure(job, describe_missing_start_rate(inputs.request))
        return
    # The strategy file and the error log go to /tmp, the only writable path in the web container.
    with tempfile.TemporaryDirectory(prefix=f"atrade-backtest-{job.backtest_id}-") as work_directory:
        await save_result(job, inputs, starting_cash, Path(work_directory))


def run_backtest(*, database_url: str, backtest_id: int, clock: Clock) -> None:
    """Runs one backtest and writes its status and result to PostgreSQL. The child process entry point calls it."""
    asyncio.run(run_backtest_steps(BacktestJob(database_url=database_url, backtest_id=backtest_id, clock=clock)))
