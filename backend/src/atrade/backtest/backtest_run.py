"""One backtest from start to end, in the backtest child process: read the inputs, run, and save the result.

The child gets only the backtest ID. It reads the request, the strategy version, and the bars from PostgreSQL.
"""

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

import psycopg

from atrade.backtest import backtest_store
from atrade.backtest.backtest_metrics import calculate_equity_curve, calculate_metrics
from atrade.backtest.backtest_store import BacktestRequest, BacktestResult
from atrade.backtest.strategy_engine_run import StrategyFailedError, run_strategy_on_bars
from atrade.foundation.bar import Bar
from atrade.foundation.clock import Clock
from atrade.market_data import BarRequest, read_saved_bars
from atrade.strategy import read_strategy_version


@dataclass(frozen=True)
class BacktestInputs:
    request: BacktestRequest
    code: str
    bars: list[Bar]


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
    bars = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(
            instrument=request.instrument, bar_period=request.bar_period, time_range=request.time_range
        ),
    )
    return BacktestInputs(request=request, code=strategy_version.code, bars=bars)


def describe_missing_bars(request: BacktestRequest) -> str:
    instrument = request.instrument
    return (
        f"PostgreSQL has no saved {request.bar_period.value} bars of {instrument.symbol} / {instrument.exchange}"
        f" / {instrument.currency} from {request.time_range.start_utc.isoformat()}"
        f" to {request.time_range.end_utc.isoformat()}. Open the bar chart of the instrument to load bars from IBKR."
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


async def save_result(job: BacktestJob, inputs: BacktestInputs, work_directory: Path) -> None:
    request = inputs.request
    try:
        trades = run_strategy_on_bars(
            code=inputs.code, request=request, bars=inputs.bars, work_directory=work_directory
        )
    except StrategyFailedError as error:
        # readability-exception: the engine reports a strategy error only as an exception (G1).
        await save_failure(job, str(error))
        return
    equity_curve = calculate_equity_curve(
        paper_capital_usd=request.paper_capital_usd, bars=inputs.bars, bar_period=request.bar_period, trades=trades
    )
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


async def run_backtest_steps(job: BacktestJob) -> None:
    inputs = await read_backtest_inputs(database_url=job.database_url, backtest_id=job.backtest_id)
    if not inputs.bars:
        await save_failure(job, describe_missing_bars(inputs.request))
        return
    # The strategy file and the error log go to /tmp, the only writable path in the web container.
    with tempfile.TemporaryDirectory(prefix=f"atrade-backtest-{job.backtest_id}-") as work_directory:
        await save_result(job, inputs, Path(work_directory))


def run_backtest(*, database_url: str, backtest_id: int, clock: Clock) -> None:
    """Runs one backtest and writes its status and result to PostgreSQL. The child process entry point calls it."""
    asyncio.run(run_backtest_steps(BacktestJob(database_url=database_url, backtest_id=backtest_id, clock=clock)))
