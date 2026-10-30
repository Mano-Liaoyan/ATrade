"""SQL for the backtest, backtest_equity_point, and backtest_trade tables. Only the backtest capability uses them."""

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final, Literal

import psycopg
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from atrade.backtest.backtest_metrics import BacktestMetrics, BacktestTrade, EquityPoint, find_split_time
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarSource

type BacktestStatus = Literal["queued", "running", "finished", "failed", "timed_out", "cancelled"]
# The values of the parameters of a parameter sweep run, by parameter name (docs/architecture/backtest.md 10.11).
type ParameterValues = dict[str, int | float | bool]
# docs/architecture/backtest.md section 10.10.2. The kind `screen` is not in this version.
type UniverseKind = Literal["single", "rule", "list"]
type MultiInstrumentKind = Literal["rule", "list"]


@dataclass(frozen=True)
class BacktestUniverse:
    """The universe of a multi-instrument backtest. All members are in `currency`. `top_n` is only for `rule`."""

    kind: MultiInstrumentKind
    currency: str
    top_n: int | None = None


@dataclass(frozen=True)
class UniversePeriod:
    """The members of the universe from `start_utc` to the start of the next period, or to the backtest end."""

    start_utc: datetime
    members: list[Instrument]


@dataclass(frozen=True)
class BacktestRequest:
    strategy_version_id: int
    # None for a multi-instrument backtest: then `universe` names the members.
    instrument: Instrument | None
    bar_period: BarPeriod
    time_range: TimeRange
    paper_capital_usd: Decimal
    # The last percent of the range that is out of sample (docs/architecture/backtest.md section 10.9.4). 0 is no
    # split. The same-period backtest of a forward test uses 0, because a forward test has no split.
    out_of_sample_share: int = 0
    # The source order of the bars and the look-back bars. None in a new request: the global source order. None in
    # a saved backtest only for a row from before the source order (docs/architecture/backtest.md section 10.12).
    source_order: list[BarSource] | None = None
    universe: BacktestUniverse | None = None
    # The parameter values of a parameter sweep run. The child gives them to the strategy configuration.
    parameters: ParameterValues | None = None

    @property
    def universe_kind(self) -> UniverseKind:
        return "single" if self.universe is None else self.universe.kind

    @property
    def currency(self) -> str:
        """The currency of the instrument or of all universe members."""
        if self.universe is not None:
            return self.universe.currency
        return self.single_instrument.currency

    @property
    def single_instrument(self) -> Instrument:
        """The instrument of a single-instrument backtest."""
        if self.instrument is None:
            message = "A multi-instrument backtest has no single instrument."
            raise ValueError(message)
        return self.instrument


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
    symbol: str | None
    exchange: str | None
    currency: str | None
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
    out_of_sample_share: int
    split_time_utc: datetime | None
    source_order: list[str] | None
    bar_count_by_source: dict[str, int] | None
    universe_kind: UniverseKind
    universe_top_n: int | None
    sweep_id: int | None
    parameters: ParameterValues | None


BACKTEST_COLUMNS: Final = """
    id, strategy_version_id, symbol, exchange, currency, bar_period, start_utc, end_utc, paper_capital_usd,
    status, error_message, created_at_utc, started_at_utc, ended_at_utc,
    final_equity_usd, total_return_percent, max_drawdown_percent, trade_count,
    cagr_percent, annual_volatility_percent, sharpe_ratio, sortino_ratio, calmar_ratio, profit_factor,
    average_win_usd, average_win_percent, average_loss_usd, exposure_percent, turnover_per_year, win_rate_percent,
    out_of_sample_share, split_time_utc, conversation_id, source_order, bar_count_by_source, universe_kind,
    universe_top_n, sweep_id, parameters
"""


@dataclass(frozen=True)
class OverlappingBacktest:
    id: int
    strategy_version_id: int


def read_row_instrument(row: BacktestRow) -> Instrument | None:
    if row.symbol is None or row.exchange is None or row.currency is None:
        return None
    return Instrument(symbol=row.symbol, exchange=row.exchange, currency=row.currency)


def read_universe(row: BacktestRow) -> BacktestUniverse | None:
    if row.universe_kind == "single" or row.currency is None:
        return None
    return BacktestUniverse(kind=row.universe_kind, currency=row.currency, top_n=row.universe_top_n)


def read_request(row: BacktestRow) -> BacktestRequest:
    return BacktestRequest(
        strategy_version_id=row.strategy_version_id,
        instrument=read_row_instrument(row),
        bar_period=BarPeriod(row.bar_period),
        time_range=TimeRange(start_utc=row.start_utc, end_utc=row.end_utc),
        paper_capital_usd=row.paper_capital_usd,
        out_of_sample_share=row.out_of_sample_share,
        source_order=None if row.source_order is None else [BarSource(value) for value in row.source_order],
        universe=read_universe(row),
        parameters=row.parameters,
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


async def insert_backtest(  # noqa: PLR0913 readability-exception: the keywords of a backtest or a sweep run.
    connection: psycopg.AsyncConnection,
    *,
    request: BacktestRequest,
    created_at_utc: datetime,
    universe_periods: list[UniversePeriod] | None = None,
    conversation_id: int | None = None,
    sweep_id: int | None = None,
) -> BacktestRow:
    """Adds a queued backtest, and the members of each universe period of a multi-instrument backtest. One
    transaction."""
    instrument = request.instrument
    async with connection.transaction(), connection.cursor(row_factory=class_row(BacktestRow)) as cursor:
        await cursor.execute(
            f"""
            INSERT INTO backtest (strategy_version_id, symbol, exchange, currency, bar_period, start_utc, end_utc,
                paper_capital_usd, out_of_sample_share, split_time_utc, status, created_at_utc, conversation_id,
                source_order, universe_kind, universe_top_n, sweep_id, parameters)
            VALUES (%(strategy_version_id)s, %(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, %(start_utc)s,
                %(end_utc)s, %(paper_capital_usd)s, %(out_of_sample_share)s, %(split_time_utc)s, 'queued',
                %(created_at_utc)s, %(conversation_id)s, %(source_order)s, %(universe_kind)s, %(universe_top_n)s,
                %(sweep_id)s, %(parameters)s)
            RETURNING {BACKTEST_COLUMNS}
            """,
            {
                "strategy_version_id": request.strategy_version_id,
                "symbol": None if instrument is None else instrument.symbol,
                "exchange": None if instrument is None else instrument.exchange,
                "currency": request.currency,
                "bar_period": request.bar_period.value,
                "start_utc": request.time_range.start_utc,
                "end_utc": request.time_range.end_utc,
                "paper_capital_usd": request.paper_capital_usd,
                "out_of_sample_share": request.out_of_sample_share,
                "split_time_utc": find_split_time(request.time_range, request.out_of_sample_share),
                "created_at_utc": created_at_utc,
                "conversation_id": conversation_id,
                "source_order": None
                if request.source_order is None
                else Jsonb([bar_source.value for bar_source in request.source_order]),
                "universe_kind": request.universe_kind,
                "universe_top_n": None if request.universe is None else request.universe.top_n,
                "sweep_id": sweep_id,
                "parameters": None if request.parameters is None else Jsonb(request.parameters),
            },
        )
        inserted_row = await cursor.fetchone()
        if inserted_row is None:
            message = "INSERT ... RETURNING returned no row."
            raise RuntimeError(message)
        await cursor.executemany(
            """
            INSERT INTO backtest_universe_member (backtest_id, period_start_utc, symbol, exchange)
            VALUES (%(backtest_id)s, %(period_start_utc)s, %(symbol)s, %(exchange)s)
            """,
            [
                {
                    "backtest_id": inserted_row.id,
                    "period_start_utc": period.start_utc,
                    "symbol": member.symbol,
                    "exchange": member.exchange,
                }
                for period in universe_periods or []
                for member in period.members
            ],
        )
    return inserted_row


async def select_universe_periods(
    connection: psycopg.AsyncConnection, *, backtest_id: int, currency: str
) -> list[UniversePeriod]:
    """The members of each universe period of the backtest, oldest period first."""
    cursor = await connection.execute(
        """
        SELECT period_start_utc, symbol, exchange FROM backtest_universe_member
        WHERE backtest_id = %(backtest_id)s ORDER BY period_start_utc, symbol, exchange
        """,
        {"backtest_id": backtest_id},
    )
    periods: list[UniversePeriod] = []
    for period_start_utc, symbol, exchange in await cursor.fetchall():
        if not periods or periods[-1].start_utc != period_start_utc:
            periods.append(UniversePeriod(start_utc=period_start_utc, members=[]))
        periods[-1].members.append(Instrument(symbol=symbol, exchange=exchange, currency=currency))
    return periods


async def select_backtests(connection: psycopg.AsyncConnection) -> list[BacktestRow]:
    """Returns all backtests that are not runs of a parameter sweep, the newest first (docs/architecture/backtest.md
    section 10.11.4)."""
    async with connection.cursor(row_factory=class_row(BacktestRow)) as cursor:
        await cursor.execute(f"SELECT {BACKTEST_COLUMNS} FROM backtest WHERE sweep_id IS NULL ORDER BY id DESC")
        return await cursor.fetchall()


async def select_backtest(connection: psycopg.AsyncConnection, backtest_id: int) -> BacktestRow | None:
    async with connection.cursor(row_factory=class_row(BacktestRow)) as cursor:
        await cursor.execute(
            f"SELECT {BACKTEST_COLUMNS} FROM backtest WHERE id = %(backtest_id)s",
            {"backtest_id": backtest_id},
        )
        return await cursor.fetchone()


async def select_overlapping_out_of_sample_parts(
    connection: psycopg.AsyncConnection, row: BacktestRow
) -> list[OverlappingBacktest]:
    """The backtests of the same instrument or universe and bar period whose out-of-sample part overlaps the
    out-of-sample part of `row`: the finished backtests and `row` itself. A universe is the same as in
    `select_finished_backtests_of`. The caller filters them by strategy, because the strategy tables belong to the
    strategy capability."""
    async with connection.cursor(row_factory=class_row(OverlappingBacktest)) as cursor:
        await cursor.execute(
            """
            SELECT id, strategy_version_id FROM backtest
            WHERE id = %(id)s
                OR (status = 'finished'
                    AND symbol IS NOT DISTINCT FROM %(symbol)s AND exchange IS NOT DISTINCT FROM %(exchange)s
                    AND currency IS NOT DISTINCT FROM %(currency)s AND bar_period = %(bar_period)s
                    AND universe_kind = %(universe_kind)s
                    AND universe_top_n IS NOT DISTINCT FROM %(universe_top_n)s
                    AND split_time_utc < %(end_utc)s AND %(split_time_utc)s < end_utc)
            ORDER BY id
            """,
            {
                "id": row.id,
                "symbol": row.symbol,
                "exchange": row.exchange,
                "currency": row.currency,
                "bar_period": row.bar_period,
                "universe_kind": row.universe_kind,
                "universe_top_n": row.universe_top_n,
                "end_utc": row.end_utc,
                "split_time_utc": row.split_time_utc,
            },
        )
        return await cursor.fetchall()


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


async def select_finished_backtests_of(connection: psycopg.AsyncConnection, row: BacktestRow) -> list[TrialRow]:
    """The finished backtests of the same instrument or universe and the bar period of `row`, for all time ranges.
    A universe is the same when the kind, the currency, and `universe_top_n` are the same
    (docs/architecture/backtest.md section 10.10.8)."""
    async with connection.cursor(row_factory=class_row(TrialRow)) as cursor:
        await cursor.execute(
            """
            SELECT id, strategy_version_id, paper_capital_usd FROM backtest
            WHERE status = 'finished' AND symbol IS NOT DISTINCT FROM %(symbol)s
                AND exchange IS NOT DISTINCT FROM %(exchange)s AND currency IS NOT DISTINCT FROM %(currency)s
                AND bar_period = %(bar_period)s AND universe_kind = %(universe_kind)s
                AND universe_top_n IS NOT DISTINCT FROM %(universe_top_n)s
            ORDER BY id
            """,
            {
                "symbol": row.symbol,
                "exchange": row.exchange,
                "currency": row.currency,
                "bar_period": row.bar_period,
                "universe_kind": row.universe_kind,
                "universe_top_n": row.universe_top_n,
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
            SELECT time_utc, side, quantity_shares, price_usd, commission_usd, symbol, exchange FROM backtest_trade
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
            INSERT INTO backtest_trade (backtest_id, time_utc, side, quantity_shares, price_usd, commission_usd,
                symbol, exchange)
            VALUES (%(backtest_id)s, %(time_utc)s, %(side)s, %(quantity_shares)s, %(price_usd)s, %(commission_usd)s,
                %(symbol)s, %(exchange)s)
            """,
            [
                {
                    "backtest_id": backtest_id,
                    "time_utc": trade.time_utc,
                    "side": trade.side,
                    "quantity_shares": trade.quantity_shares,
                    "price_usd": trade.price_usd,
                    "commission_usd": trade.commission_usd,
                    "symbol": trade.symbol,
                    "exchange": trade.exchange,
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
