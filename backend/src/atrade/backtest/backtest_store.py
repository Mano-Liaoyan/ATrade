"""SQL for the backtest, backtest_equity_point, and backtest_trade tables. Only the backtest capability uses them."""

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final, Literal

import psycopg
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from atrade.backtest.backtest_metrics import BacktestMetrics, BacktestTrade, EquityPoint
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarSource

type BacktestStatus = Literal["queued", "running", "finished", "failed", "timed_out"]


@dataclass(frozen=True)
class BacktestRequest:
    strategy_version_id: int
    instrument: Instrument
    bar_period: BarPeriod
    time_range: TimeRange
    paper_capital_usd: Decimal
    # The source order of the bars and the look-back bars. None in a new request: the global source order. None in
    # a saved backtest only for a row from before the source order (docs/architecture/backtest.md section 10.12).
    source_order: list[BarSource] | None = None


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: list[EquityPoint]
    trades: list[BacktestTrade]
    metrics: BacktestMetrics
    # The bar count of each bar source in the backtest range, without the look-back bars.
    bar_count_by_source: dict[BarSource, int]


@dataclass(frozen=True)
class BacktestRow:
    id: int
    strategy_version_id: int
    symbol: str
    exchange: str
    currency: str
    bar_period: str
    start_utc: datetime
    end_utc: datetime
    paper_capital_usd: Decimal
    status: BacktestStatus
    error_message: str | None
    created_at_utc: datetime
    started_at_utc: datetime | None
    ended_at_utc: datetime | None
    final_equity_usd: Decimal | None
    total_return_percent: Decimal | None
    max_drawdown_percent: Decimal | None
    trade_count: int | None
    cagr_percent: Decimal | None
    annual_volatility_percent: Decimal | None
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    calmar_ratio: Decimal | None
    profit_factor: Decimal | None
    average_win_usd: Decimal | None
    average_win_percent: Decimal | None
    average_loss_usd: Decimal | None
    exposure_percent: Decimal | None
    turnover_per_year: Decimal | None
    win_rate_percent: Decimal | None
    conversation_id: int | None
    source_order: list[str] | None
    bar_count_by_source: dict[str, int] | None


BACKTEST_COLUMNS: Final = """
    id, strategy_version_id, symbol, exchange, currency, bar_period, start_utc, end_utc, paper_capital_usd,
    status, error_message, created_at_utc, started_at_utc, ended_at_utc,
    final_equity_usd, total_return_percent, max_drawdown_percent, trade_count,
    cagr_percent, annual_volatility_percent, sharpe_ratio, sortino_ratio, calmar_ratio, profit_factor,
    average_win_usd, average_win_percent, average_loss_usd, exposure_percent, turnover_per_year, win_rate_percent,
    conversation_id, source_order, bar_count_by_source
"""


def read_request(row: BacktestRow) -> BacktestRequest:
    return BacktestRequest(
        strategy_version_id=row.strategy_version_id,
        instrument=Instrument(symbol=row.symbol, exchange=row.exchange, currency=row.currency),
        bar_period=BarPeriod(row.bar_period),
        time_range=TimeRange(start_utc=row.start_utc, end_utc=row.end_utc),
        paper_capital_usd=row.paper_capital_usd,
        source_order=None if row.source_order is None else [BarSource(value) for value in row.source_order],
    )


def read_metrics(row: BacktestRow) -> BacktestMetrics | None:
    if (
        row.final_equity_usd is None
        or row.total_return_percent is None
        or row.max_drawdown_percent is None
        or row.trade_count is None
    ):
        return None
    return BacktestMetrics(
        final_equity_usd=row.final_equity_usd,
        total_return_percent=row.total_return_percent,
        max_drawdown_percent=row.max_drawdown_percent,
        trade_count=row.trade_count,
        cagr_percent=row.cagr_percent,
        annual_volatility_percent=row.annual_volatility_percent,
        sharpe_ratio=row.sharpe_ratio,
        sortino_ratio=row.sortino_ratio,
        calmar_ratio=row.calmar_ratio,
        profit_factor=row.profit_factor,
        average_win_usd=row.average_win_usd,
        average_win_percent=row.average_win_percent,
        average_loss_usd=row.average_loss_usd,
        exposure_percent=row.exposure_percent,
        turnover_per_year=row.turnover_per_year,
        win_rate_percent=row.win_rate_percent,
    )


async def insert_backtest(
    connection: psycopg.AsyncConnection,
    *,
    request: BacktestRequest,
    created_at_utc: datetime,
    conversation_id: int | None = None,
) -> BacktestRow:
    async with connection.cursor(row_factory=class_row(BacktestRow)) as cursor:
        await cursor.execute(
            f"""
            INSERT INTO backtest (strategy_version_id, symbol, exchange, currency, bar_period, start_utc, end_utc,
                paper_capital_usd, status, created_at_utc, conversation_id, source_order)
            VALUES (%(strategy_version_id)s, %(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, %(start_utc)s,
                %(end_utc)s, %(paper_capital_usd)s, 'queued', %(created_at_utc)s, %(conversation_id)s, %(source_order)s)
            RETURNING {BACKTEST_COLUMNS}
            """,
            {
                "strategy_version_id": request.strategy_version_id,
                "symbol": request.instrument.symbol,
                "exchange": request.instrument.exchange,
                "currency": request.instrument.currency,
                "bar_period": request.bar_period.value,
                "start_utc": request.time_range.start_utc,
                "end_utc": request.time_range.end_utc,
                "paper_capital_usd": request.paper_capital_usd,
                "created_at_utc": created_at_utc,
                "conversation_id": conversation_id,
                "source_order": None
                if request.source_order is None
                else Jsonb([bar_source.value for bar_source in request.source_order]),
            },
        )
        inserted_row = await cursor.fetchone()
    if inserted_row is None:
        message = "INSERT ... RETURNING returned no row."
        raise RuntimeError(message)
    return inserted_row


async def select_backtests(connection: psycopg.AsyncConnection) -> list[BacktestRow]:
    """Returns all backtests, the newest first."""
    async with connection.cursor(row_factory=class_row(BacktestRow)) as cursor:
        await cursor.execute(f"SELECT {BACKTEST_COLUMNS} FROM backtest ORDER BY id DESC")
        return await cursor.fetchall()


async def select_backtest(connection: psycopg.AsyncConnection, backtest_id: int) -> BacktestRow | None:
    async with connection.cursor(row_factory=class_row(BacktestRow)) as cursor:
        await cursor.execute(
            f"SELECT {BACKTEST_COLUMNS} FROM backtest WHERE id = %(backtest_id)s",
            {"backtest_id": backtest_id},
        )
        return await cursor.fetchone()


async def select_equity_curve(connection: psycopg.AsyncConnection, backtest_id: int) -> list[EquityPoint]:
    async with connection.cursor(row_factory=class_row(EquityPoint)) as cursor:
        await cursor.execute(
            """
            SELECT time_utc, equity_usd FROM backtest_equity_point
            WHERE backtest_id = %(backtest_id)s
            ORDER BY time_utc
            """,
            {"backtest_id": backtest_id},
        )
        return await cursor.fetchall()


@dataclass(frozen=True)
class TrialRow:
    """A finished backtest that can count as a trial of another backtest (docs/architecture/backtest.md 10.9.5)."""

    id: int
    strategy_version_id: int
    paper_capital_usd: Decimal


async def select_finished_backtests_of(
    connection: psycopg.AsyncConnection, *, instrument: Instrument, bar_period: BarPeriod
) -> list[TrialRow]:
    """The finished backtests of the instrument and the bar period, for all time ranges."""
    async with connection.cursor(row_factory=class_row(TrialRow)) as cursor:
        await cursor.execute(
            """
            SELECT id, strategy_version_id, paper_capital_usd FROM backtest
            WHERE status = 'finished' AND symbol = %(symbol)s AND exchange = %(exchange)s
                AND currency = %(currency)s AND bar_period = %(bar_period)s
            ORDER BY id
            """,
            {
                "symbol": instrument.symbol,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
                "bar_period": bar_period.value,
            },
        )
        return await cursor.fetchall()


async def select_equity_curves(
    connection: psycopg.AsyncConnection, backtest_ids: list[int]
) -> dict[int, list[EquityPoint]]:
    """The equity curves of the backtests, by backtest ID, with one query. A backtest without points has []."""
    equity_curves: dict[int, list[EquityPoint]] = {backtest_id: [] for backtest_id in backtest_ids}
    cursor = await connection.execute(
        """
        SELECT backtest_id, time_utc, equity_usd FROM backtest_equity_point
        WHERE backtest_id = ANY(%(backtest_ids)s)
        ORDER BY backtest_id, time_utc
        """,
        {"backtest_ids": backtest_ids},
    )
    for backtest_id, time_utc, equity_usd in await cursor.fetchall():
        equity_curves[backtest_id].append(EquityPoint(time_utc=time_utc, equity_usd=equity_usd))
    return equity_curves


async def select_trades(connection: psycopg.AsyncConnection, backtest_id: int) -> list[BacktestTrade]:
    async with connection.cursor(row_factory=class_row(BacktestTrade)) as cursor:
        await cursor.execute(
            """
            SELECT time_utc, side, quantity_shares, price_usd, commission_usd FROM backtest_trade
            WHERE backtest_id = %(backtest_id)s
            ORDER BY time_utc, id
            """,
            {"backtest_id": backtest_id},
        )
        return await cursor.fetchall()


async def start_next_queued_backtest(connection: psycopg.AsyncConnection, *, started_at_utc: datetime) -> int | None:
    """Marks the oldest queued backtest as running and returns its ID. Returns None when the queue is empty."""
    cursor = await connection.execute(
        """
        UPDATE backtest SET status = 'running', started_at_utc = %(started_at_utc)s
        WHERE id = (SELECT id FROM backtest WHERE status = 'queued' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED)
        RETURNING id
        """,
        {"started_at_utc": started_at_utc},
    )
    started_row = await cursor.fetchone()
    if started_row is None:
        return None
    return int(started_row[0])


async def end_backtest(
    connection: psycopg.AsyncConnection,
    *,
    backtest_id: int,
    ended_at_utc: datetime,
    status_if_running: BacktestStatus,
    error_message: str | None,
) -> None:
    """Ends a backtest that is still running with `status_if_running` and `error_message`.

    The child process sets "finished" or "failed" itself. The status is still "running" only when the child
    ended without a result, for example after a timeout or a crash.
    """
    await connection.execute(
        """
        UPDATE backtest SET ended_at_utc = %(ended_at_utc)s, status = %(status)s, error_message = %(error_message)s
        WHERE id = %(backtest_id)s AND status = 'running'
        """,
        {
            "backtest_id": backtest_id,
            "ended_at_utc": ended_at_utc,
            "status": status_if_running,
            "error_message": error_message,
        },
    )


async def fail_running_backtests(
    connection: psycopg.AsyncConnection, *, ended_at_utc: datetime, error_message: str
) -> None:
    await connection.execute(
        """
        UPDATE backtest SET status = 'failed', error_message = %(error_message)s, ended_at_utc = %(ended_at_utc)s
        WHERE status = 'running'
        """,
        {"ended_at_utc": ended_at_utc, "error_message": error_message},
    )


async def save_result(
    connection: psycopg.AsyncConnection,
    *,
    backtest_id: int,
    result: BacktestResult,
    ended_at_utc: datetime,
) -> None:
    """Saves the equity curve, the trades, and the metrics, and sets the status "finished". One transaction."""
    async with connection.transaction(), connection.cursor() as cursor:
        await cursor.executemany(
            """
            INSERT INTO backtest_equity_point (backtest_id, time_utc, equity_usd)
            VALUES (%(backtest_id)s, %(time_utc)s, %(equity_usd)s)
            """,
            [
                {"backtest_id": backtest_id, "time_utc": point.time_utc, "equity_usd": point.equity_usd}
                for point in result.equity_curve
            ],
        )
        await cursor.executemany(
            """
            INSERT INTO backtest_trade (backtest_id, time_utc, side, quantity_shares, price_usd, commission_usd)
            VALUES (%(backtest_id)s, %(time_utc)s, %(side)s, %(quantity_shares)s, %(price_usd)s, %(commission_usd)s)
            """,
            [
                {
                    "backtest_id": backtest_id,
                    "time_utc": trade.time_utc,
                    "side": trade.side,
                    "quantity_shares": trade.quantity_shares,
                    "price_usd": trade.price_usd,
                    "commission_usd": trade.commission_usd,
                }
                for trade in result.trades
            ],
        )
        await cursor.execute(
            """
            UPDATE backtest SET status = 'finished', ended_at_utc = %(ended_at_utc)s, final_equity_usd = %(final_equity_usd)s,
                total_return_percent = %(total_return_percent)s, max_drawdown_percent = %(max_drawdown_percent)s,
                trade_count = %(trade_count)s, cagr_percent = %(cagr_percent)s,
                annual_volatility_percent = %(annual_volatility_percent)s, sharpe_ratio = %(sharpe_ratio)s,
                sortino_ratio = %(sortino_ratio)s, calmar_ratio = %(calmar_ratio)s, profit_factor = %(profit_factor)s,
                average_win_usd = %(average_win_usd)s, average_win_percent = %(average_win_percent)s,
                average_loss_usd = %(average_loss_usd)s, exposure_percent = %(exposure_percent)s,
                turnover_per_year = %(turnover_per_year)s, win_rate_percent = %(win_rate_percent)s,
                bar_count_by_source = %(bar_count_by_source)s
            WHERE id = %(backtest_id)s
            """,
            {
                "backtest_id": backtest_id,
                **asdict(result.metrics),
                "bar_count_by_source": Jsonb(
                    {bar_source.value: count for bar_source, count in result.bar_count_by_source.items()}
                ),
                "ended_at_utc": ended_at_utc,
            },
        )


async def save_failure(
    connection: psycopg.AsyncConnection, *, backtest_id: int, error_message: str, ended_at_utc: datetime
) -> None:
    await connection.execute(
        """
        UPDATE backtest SET status = 'failed', error_message = %(error_message)s, ended_at_utc = %(ended_at_utc)s
        WHERE id = %(backtest_id)s
        """,
        {"backtest_id": backtest_id, "error_message": error_message, "ended_at_utc": ended_at_utc},
    )
