"""Backtests for other capabilities: queue a backtest and read its outcome. A forward test uses them for its
comparison with a backtest of the same period (docs/architecture/forward_test.md section 12.10).
"""

from dataclasses import dataclass
from datetime import datetime

import psycopg

from atrade.backtest import backtest_store
from atrade.backtest.backtest_metrics import BacktestMetrics, BacktestTrade, EquityPoint
from atrade.backtest.backtest_store import BacktestRequest, BacktestStatus

# A backtest has no exchange rates, so the paper capital in USD can only buy USD instruments.
SUPPORTED_CURRENCY = "USD"


@dataclass(frozen=True)
class BacktestOutcome:
    """A backtest with its result. `metrics` is None and the lists are empty until the backtest finished."""

    id: int
    request: BacktestRequest
    status: BacktestStatus
    error_message: str | None
    metrics: BacktestMetrics | None
    equity_curve: list[EquityPoint]
    trades: list[BacktestTrade]


def check_backtest_request(request: BacktestRequest) -> str | None:
    """Returns why a backtest cannot run with this request, or None."""
    currency = request.instrument.currency
    if currency != SUPPORTED_CURRENCY:
        return f"A backtest supports only USD instruments. The instrument currency is {currency}."
    if request.time_range.end_utc <= request.time_range.start_utc:
        return "The time range must end after it starts."
    return None


async def queue_backtest(*, database_url: str, request: BacktestRequest, created_at_utc: datetime) -> int:
    """Adds a queued backtest and returns its ID. The backtest runner of the Web process starts it."""
    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as connection:
        row = await backtest_store.insert_backtest(connection, request=request, created_at_utc=created_at_utc)
    return row.id


async def read_backtest_outcome(*, database_url: str, backtest_id: int) -> BacktestOutcome | None:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        row = await backtest_store.select_backtest(connection, backtest_id)
        if row is None:
            return None
        equity_curve = await backtest_store.select_equity_curve(connection, backtest_id)
        trades = await backtest_store.select_trades(connection, backtest_id)
    return BacktestOutcome(
        id=row.id,
        request=backtest_store.read_request(row),
        status=row.status,
        error_message=row.error_message,
        metrics=backtest_store.read_metrics(row),
        equity_curve=equity_curve,
        trades=trades,
    )
