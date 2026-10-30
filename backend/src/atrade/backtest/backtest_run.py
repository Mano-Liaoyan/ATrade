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
from atrade.backtest.backtest_metrics import calculate_equity_curve, calculate_metrics
from atrade.backtest.backtest_store import BacktestRequest, BacktestResult
from atrade.backtest.strategy_engine_run import (
    StrategyFailedError,
    StrategyRun,
    read_currency_precision,
    run_strategy_on_bars,
)
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.clock import Clock
from atrade.market_data import BarRequest, read_saved_bars, read_source_order
from atrade.strategy import read_strategy_version

# The look-back is the warm-up of the strategy template: 3 average periods of its default 20 bars, and 1 week at
# least (docs/architecture/backtest.md section 10.3). A strategy that asks for more gets only these bars.
LOOK_BACK_AVERAGE_PERIOD_BARS = 20
LOOK_BACK_AVERAGE_PERIODS = 3
MIN_LOOK_BACK_LENGTH = timedelta(days=7)


def find_look_back_length(bar_period: BarPeriod) -> timedelta:
    """How long before the backtest start the saved look-back bars go, for `request_bars` in the strategy."""
    return max(bar_period.length * LOOK_BACK_AVERAGE_PERIOD_BARS * LOOK_BACK_AVERAGE_PERIODS, MIN_LOOK_BACK_LENGTH)


@dataclass(frozen=True)
class BacktestInputs:
    request: BacktestRequest
    code: str
    bars: list[Bar]
    look_back_bars: list[Bar]
    # None for a USD instrument.
    exchange_rates: DailyExchangeRates | None


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
    # The global source order (docs/architecture/market_data.md section 8.7.2).
    source_order = await read_source_order(database_url=database_url)
    saved_bars = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(
            instrument=request.instrument, bar_period=request.bar_period, time_range=request.time_range
        ),
        source_order=source_order,
    )
    start_utc = request.time_range.start_utc
    saved_look_back_bars = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(
            instrument=request.instrument,
            bar_period=request.bar_period,
            time_range=TimeRange(start_utc=start_utc - find_look_back_length(request.bar_period), end_utc=start_utc),
        ),
        source_order=source_order,
    )
    exchange_rates = (
        None
        if request.instrument.currency == USD
        else await read_daily_exchange_rates(database_url=database_url, request=request)
    )
    return BacktestInputs(
        request=request,
        code=strategy_version.code,
        bars=saved_bars.bars,
        look_back_bars=saved_look_back_bars.bars,
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


async def save_result(job: BacktestJob, inputs: BacktestInputs, starting_cash: Decimal, work_directory: Path) -> None:
    """Runs the strategy with `starting_cash` in the instrument currency and saves the result in USD."""
    request = inputs.request
    try:
        run = StrategyRun(
            code=inputs.code,
            request=request,
            starting_cash=starting_cash,
            bars=inputs.bars,
            look_back_bars=inputs.look_back_bars,
        )
        trades = run_strategy_on_bars(run, work_directory)
    except StrategyFailedError as error:
        # readability-exception: the engine reports a strategy error only as an exception (G1).
        await save_failure(job, str(error))
        return
    # In the instrument currency, like the trades.
    equity_curve = calculate_equity_curve(
        start_cash=starting_cash, bars=inputs.bars, bar_period=request.bar_period, trades=trades
    )
    if inputs.exchange_rates is not None:
        equity_curve = convert_equity_curve_to_usd(inputs.exchange_rates, equity_curve)
        trades = convert_trades_to_usd(inputs.exchange_rates, trades)
    metrics = calculate_metrics(
        paper_capital_usd=request.paper_capital_usd, equity_curve=equity_curve, trade_count=len(trades)
    )
    async with await psycopg.AsyncConnection.connect(job.database_url, autocommit=True) as connection:
        await backtest_store.save_result(
            connection,
            backtest_id=job.backtest_id,
            result=BacktestResult(equity_curve=equity_curve, trades=trades, metrics=metrics),
            ended_at_utc=job.clock.read_now_utc(),
        )


def find_starting_cash(inputs: BacktestInputs) -> Decimal | None:
    """The paper capital in the instrument currency, or None without a rate at the start (section 10.8)."""
    request = inputs.request
    if inputs.exchange_rates is None:
        return request.paper_capital_usd
    usd_per_unit = inputs.exchange_rates.find_usd_per_unit(request.time_range.start_utc)
    if usd_per_unit is None:
        return None
    return convert_paper_capital(
        request.paper_capital_usd, usd_per_unit, read_currency_precision(request.instrument.currency)
    )


async def run_backtest_steps(job: BacktestJob) -> None:
    inputs = await read_backtest_inputs(database_url=job.database_url, backtest_id=job.backtest_id)
    if not inputs.bars:
        await save_failure(job, describe_missing_bars(inputs.request))
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
