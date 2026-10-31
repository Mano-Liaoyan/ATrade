"""HTTP routes of the forward test page and the comparison: the forward test with its records and its backtests of
the same period, start a backtest of the same period, and compare the forward test with a backtest
(docs/architecture/forward_test.md section 12.10).
"""

import dataclasses
from datetime import datetime
from decimal import Decimal
from typing import Literal

import psycopg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from atrade.backtest import (
    BacktestMetrics,
    BacktestOutcome,
    BacktestRequest,
    BacktestStatus,
    BacktestTrade,
    BacktestUniverse,
    EquityPoint,
    UniversePeriod,
    calculate_metrics,
    calculate_round_trip_metrics,
    check_backtest_request,
    find_round_trips,
    queue_backtest,
    read_backtest_outcome,
    summarize_instruments,
)
from atrade.forward_test import forward_test_records, forward_test_store
from atrade.forward_test.backtest_comparison import FillComparisonRow, FillTotal, compare_fills
from atrade.forward_test.forward_test_records import ForwardTestFill
from atrade.forward_test.forward_test_store import ForwardTestInterruption, ForwardTestRow
from atrade.forward_test.http_routes import ForwardTestResponse, to_forward_test_response
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument


class SamePeriodBacktestResponse(BaseModel):
    backtest_id: int


class ComparedMetricsResponse(BaseModel):
    """The metrics of `GET /api/backtests/{id}` (docs/architecture/backtest.md section 10.9.2) and the Net profit: the
    final equity minus the start capital. A forward test has no split metrics and no robustness (section 12.10)."""

    final_equity_usd: Decimal
    net_profit_usd: Decimal
    total_return_percent: Decimal
    max_drawdown_percent: Decimal
    trade_count: int
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
    missing_reasons: dict[str, str]


class ComparedEquityPointResponse(BaseModel):
    time_utc: datetime
    equity_usd: Decimal


class ComparedBacktestSummaryResponse(BaseModel):
    id: int
    status: BacktestStatus
    error_message: str | None
    start_utc: datetime
    end_utc: datetime
    paper_capital_usd: Decimal
    metrics: ComparedMetricsResponse | None


class FillComparisonResponse(BaseModel):
    bar_end_utc: datetime
    side: Literal["BUY", "SELL"]
    symbol: str
    exchange: str
    forward_test_quantity_shares: Decimal | None
    forward_test_price_usd: Decimal | None
    backtest_quantity_shares: Decimal | None
    backtest_price_usd: Decimal | None
    price_difference_usd: Decimal | None


class ComparedInterruptionResponse(BaseModel):
    """A time without a running LiveNode (section 12.7). The chart marks it grey."""

    start_utc: datetime
    end_utc: datetime


class ForwardTestFillResponse(BaseModel):
    """A fill, or a stock split adjustment (section 12.16). A split adjustment has no price, the split ratio, and the
    cash in lieu as `amount_usd`. `side` gives the direction of the share change."""

    symbol: str
    exchange: str
    time_utc: datetime
    kind: Literal["fill", "split_adjustment"]
    side: Literal["BUY", "SELL"]
    quantity_shares: Decimal
    price_usd: Decimal | None
    commission_usd: Decimal
    # The quantity times the price of a fill, or the cash in lieu of a split adjustment.
    amount_usd: Decimal
    split_ratio: Decimal | None


class ForwardTestInstrumentResponse(BaseModel):
    """One member of a multi-instrument forward test: the Instruments tab (section 12.16)."""

    symbol: str
    exchange: str
    trade_count: int
    net_profit_usd: Decimal
    quarter_count: int


class ForwardTestDetailResponse(BaseModel):
    """The forward test page: the forward test, its records, and the backtests that "Backtest the same period" started,
    newest first."""

    forward_test: ForwardTestResponse
    # None until the forward test has a start balance.
    metrics: ComparedMetricsResponse | None
    equity_curve: list[ComparedEquityPointResponse]
    fills: list[ForwardTestFillResponse]
    # One row for each member of a multi-instrument forward test. Empty for a single-instrument forward test.
    instruments: list[ForwardTestInstrumentResponse]
    same_period_backtests: list[ComparedBacktestSummaryResponse]


class ForwardTestComparisonResponse(BaseModel):
    forward_test: ForwardTestResponse
    backtest: ComparedBacktestSummaryResponse
    # None until the forward test has a start balance.
    forward_test_metrics: ComparedMetricsResponse | None
    forward_test_equity_curve: list[ComparedEquityPointResponse]
    backtest_equity_curve: list[ComparedEquityPointResponse]
    fills: list[FillComparisonResponse]
    interruptions: list[ComparedInterruptionResponse]


def check_comparison_currency(request: BacktestRequest) -> str | None:
    """A forward test has no exchange rates: its equity and fills are in the instrument currency. A backtest of
    another currency converts to USD, so the two would not compare (docs/architecture/forward_test.md 12.10)."""
    currency = request.currency
    if currency == "USD":
        return None
    return (
        "A same-period backtest supports only USD instruments, because a forward test has no exchange rates."
        f" The instrument currency is {currency}."
    )


NO_ROUND_TRIPS_IN_PERIOD = "No round trips in the backtest period"


@dataclasses.dataclass(frozen=True)
class ForwardTestMetrics:
    """The metrics of a forward test with its start capital. `extra_reasons` replace reasons of `metrics`."""

    metrics: BacktestMetrics
    start_capital_usd: Decimal
    extra_reasons: dict[str, str] = dataclasses.field(default_factory=dict[str, str])


def to_metrics_response(
    metrics: BacktestMetrics | None, start_capital_usd: Decimal, extra_reasons: dict[str, str] | None = None
) -> ComparedMetricsResponse | None:
    """Only a metric that is None has a reason."""
    if metrics is None:
        return None
    reasons = metrics.missing_reasons | (extra_reasons or {})
    return ComparedMetricsResponse(
        **{field.name: getattr(metrics, field.name) for field in dataclasses.fields(metrics)},
        net_profit_usd=metrics.final_equity_usd - start_capital_usd,
        missing_reasons={name: reason for name, reason in reasons.items() if getattr(metrics, name) is None},
    )


def to_forward_test_metrics_response(metrics: ForwardTestMetrics | None) -> ComparedMetricsResponse | None:
    if metrics is None:
        return None
    return to_metrics_response(metrics.metrics, metrics.start_capital_usd, metrics.extra_reasons)


def to_equity_curve_response(equity_curve: list[EquityPoint]) -> list[ComparedEquityPointResponse]:
    return [ComparedEquityPointResponse(time_utc=point.time_utc, equity_usd=point.equity_usd) for point in equity_curve]


def read_quantity(total: FillTotal | None) -> Decimal | None:
    return None if total is None else total.quantity_shares


def read_price(total: FillTotal | None) -> Decimal | None:
    return None if total is None else total.price_usd


def to_fill_response(row: FillComparisonRow) -> FillComparisonResponse:
    return FillComparisonResponse(
        bar_end_utc=row.bar_end_utc,
        side=row.side,
        symbol=row.symbol,
        exchange=row.exchange,
        forward_test_quantity_shares=read_quantity(row.forward_test),
        forward_test_price_usd=read_price(row.forward_test),
        backtest_quantity_shares=read_quantity(row.backtest),
        backtest_price_usd=read_price(row.backtest),
        price_difference_usd=row.price_difference_usd,
    )


def to_interruption_response(
    interruption: ForwardTestInterruption, open_end_utc: datetime
) -> ComparedInterruptionResponse:
    """An interruption that still lasts ends at the forward test stop, or now."""
    return ComparedInterruptionResponse(
        start_utc=interruption.started_at_utc, end_utc=interruption.ended_at_utc or open_end_utc
    )


def to_compared_backtest(backtest: BacktestOutcome) -> ComparedBacktestSummaryResponse:
    return ComparedBacktestSummaryResponse(
        id=backtest.id,
        status=backtest.status,
        error_message=backtest.error_message,
        start_utc=backtest.request.time_range.start_utc,
        end_utc=backtest.request.time_range.end_utc,
        paper_capital_usd=backtest.request.paper_capital_usd,
        metrics=to_metrics_response(backtest.metrics, backtest.request.paper_capital_usd),
    )


def to_forward_test_fill_response(forward_test_fill: ForwardTestFill) -> ForwardTestFillResponse:
    fill = forward_test_fill.trade
    if forward_test_fill.kind == "split_adjustment":
        return ForwardTestFillResponse(
            symbol=forward_test_fill.instrument.symbol,
            exchange=forward_test_fill.instrument.exchange,
            time_utc=fill.time_utc,
            kind="split_adjustment",
            side=fill.side,
            quantity_shares=fill.quantity_shares,
            price_usd=None,
            commission_usd=Decimal(0),
            amount_usd=forward_test_fill.cash_in_lieu_usd or Decimal(0),
            split_ratio=forward_test_fill.split_ratio,
        )
    return ForwardTestFillResponse(
        symbol=forward_test_fill.instrument.symbol,
        exchange=forward_test_fill.instrument.exchange,
        time_utc=fill.time_utc,
        kind="fill",
        side=fill.side,
        quantity_shares=fill.quantity_shares,
        price_usd=fill.price_usd,
        commission_usd=fill.commission_usd,
        amount_usd=fill.quantity_shares * fill.price_usd,
        split_ratio=None,
    )


def to_instrument_responses(
    fills: list[BacktestTrade], members: dict[datetime, list[Instrument]]
) -> list[ForwardTestInstrumentResponse]:
    """The fills and the recorded quarters of each member (section 12.12)."""
    quarter_counts: dict[tuple[str, str], int] = {}
    for quarter_members in members.values():
        for member in quarter_members:
            key = (member.symbol, member.exchange)
            quarter_counts[key] = quarter_counts.get(key, 0) + 1
    return [
        ForwardTestInstrumentResponse(**dataclasses.asdict(instrument))
        for instrument in summarize_instruments(fills, quarter_counts)
    ]


def calculate_forward_test_metrics(
    row: ForwardTestRow, equity_curve: list[EquityPoint], fills: list[BacktestTrade], now_utc: datetime
) -> ForwardTestMetrics | None:
    """The range of a forward test goes from its start to its stop, or to now while it runs. The recorded equity
    points (one at each bar end) count as the bars of the exposure. The recorded fills are the trades."""
    if row.start_capital_usd is None:
        return None
    metrics = calculate_metrics(
        paper_capital_usd=row.start_capital_usd,
        time_range=TimeRange(start_utc=row.created_at_utc, end_utc=row.stopped_at_utc or now_utc),
        equity_curve=equity_curve,
        trades=fills,
    )
    return ForwardTestMetrics(metrics=metrics, start_capital_usd=row.start_capital_usd)


def calculate_win_rate_in_period(fills: list[BacktestTrade], period: TimeRange) -> Decimal | None:
    """The win rate of the round trips whose fills are all in the period (both ends included), or None without one.
    The round trips come from all fills, so a round trip that starts before the period does not change the pairs."""
    round_trips = [
        round_trip
        for round_trip in find_round_trips(fills)
        if period.start_utc <= round_trip.start_utc and round_trip.end_utc <= period.end_utc
    ]
    return calculate_round_trip_metrics(round_trips).win_rate_percent


def limit_win_rate_to_period(
    metrics: ForwardTestMetrics | None, fills: list[BacktestTrade], period: TimeRange
) -> ForwardTestMetrics | None:
    """The comparison counts only the forward test fills in the backtest period for the win rate (section 12.10)."""
    if metrics is None:
        return None
    win_rate_percent = calculate_win_rate_in_period(fills, period)
    return ForwardTestMetrics(
        metrics=dataclasses.replace(metrics.metrics, win_rate_percent=win_rate_percent),
        start_capital_usd=metrics.start_capital_usd,
        extra_reasons={} if win_rate_percent is not None else {"win_rate_percent": NO_ROUND_TRIPS_IN_PERIOD},
    )


def make_recorded_periods(members: dict[datetime, list[Instrument]], time_range: TimeRange) -> list[UniversePeriod]:
    """The universe periods of the same-period backtest of a multi-instrument forward test: one for each quarter that
    the forward test recorded (section 12.10). The quarter of the start begins at the backtest start, as the first
    period of a `rule` backtest (docs/architecture/backtest.md section 10.10.6)."""
    periods: list[UniversePeriod] = []
    for quarter_start_utc, quarter_members in sorted(members.items()):
        start_utc = max(quarter_start_utc, time_range.start_utc)
        if start_utc >= time_range.end_utc:
            continue
        if periods and periods[-1].start_utc == start_utc:
            periods.pop()
        periods.append(UniversePeriod(start_utc=start_utc, members=quarter_members))
    return periods


def is_same_setup(row: ForwardTestRow, backtest: BacktestOutcome) -> bool:
    """The strategy version, the bar period, and the instrument or the universe kind of the forward test."""
    request = backtest.request
    return (
        request.universe_kind == row.universe_kind
        and request.strategy_version_id == row.strategy_version_id
        and request.instrument == forward_test_store.read_single_instrument(row)
        and request.bar_period.value == row.bar_period
    )


def describe_other_setup(row: ForwardTestRow) -> str:
    instruments = "the instrument" if row.universe_kind == "single" else "the universe"
    return f"The backtest must use the strategy version, {instruments}, and the bar period of the forward test."


def name_fills(trades: list[BacktestTrade], instrument: Instrument | None) -> list[BacktestTrade]:
    """A fill without an instrument is a fill of the single instrument (BacktestTrade.symbol)."""
    if instrument is None:
        return trades
    return [
        trade
        if trade.symbol is not None
        else dataclasses.replace(trade, symbol=instrument.symbol, exchange=instrument.exchange)
        for trade in trades
    ]


class ComparisonRoutes:
    def __init__(self, *, database_url: str, clock: Clock) -> None:
        self.database_url = database_url
        self.clock = clock

    async def read_forward_test_row(self, forward_test_id: int) -> ForwardTestRow:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            row = await forward_test_store.select_forward_test(connection, forward_test_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forward test not found.")
        return row

    async def start_same_period_backtest(self, forward_test_id: int) -> SamePeriodBacktestResponse:
        """A normal backtest from the forward test start to its end, or to now while it runs."""
        row = await self.read_forward_test_row(forward_test_id)
        if row.start_capital_usd is None:
            detail = "The forward test has no start balance yet. The backtest uses it as the paper capital."
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        now_utc = self.clock.read_now_utc()
        time_range = TimeRange(start_utc=row.created_at_utc, end_utc=row.stopped_at_utc or now_utc)
        request = BacktestRequest(
            strategy_version_id=row.strategy_version_id,
            instrument=forward_test_store.read_single_instrument(row),
            bar_period=BarPeriod(row.bar_period),
            time_range=time_range,
            paper_capital_usd=row.start_capital_usd,
            # A forward test has no split, so its same-period backtest has none (docs/architecture/backtest.md 10.9.4).
            out_of_sample_share=0,
        )
        periods: list[UniversePeriod] = []
        if row.universe_kind != "single" and time_range.end_utc > time_range.start_utc:
            async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
                members = await forward_test_store.select_universe_members(connection, forward_test_id)
            periods = make_recorded_periods(members, time_range)
            if not periods:
                detail = "The forward test has no recorded members in its period."
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
            universe = BacktestUniverse(
                kind="rule" if row.universe_kind == "rule" else "list",
                currency=periods[0].members[0].currency,
                top_n=row.universe_top_n,
            )
            request = dataclasses.replace(request, universe=universe)
        refusal = check_backtest_request(request) or check_comparison_currency(request)
        if refusal is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=refusal)
        backtest_id = await queue_backtest(
            database_url=self.database_url, request=request, created_at_utc=now_utc, universe_periods=periods
        )
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            await forward_test_records.insert_same_period_backtest(
                connection, forward_test_id=forward_test_id, backtest_id=backtest_id
            )
        return SamePeriodBacktestResponse(backtest_id=backtest_id)

    async def read_forward_test_detail(self, forward_test_id: int) -> ForwardTestDetailResponse:
        row = await self.read_forward_test_row(forward_test_id)
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            forward_test_fills = await forward_test_records.select_forward_test_fills(
                connection,
                forward_test_id=forward_test_id,
                instrument=forward_test_store.read_single_instrument(row),
                uses_owner_ledger=row.allocated_capital_usd is not None,
            )
            fills = forward_test_records.list_trades(forward_test_fills)
            equity_curve = await forward_test_records.select_equity_curve(connection, forward_test_id)
            backtest_ids = await forward_test_records.select_same_period_backtest_ids(connection, forward_test_id)
            members = await forward_test_store.select_universe_members(connection, forward_test_id)
        backtests = [
            await read_backtest_outcome(database_url=self.database_url, backtest_id=backtest_id)
            for backtest_id in backtest_ids
        ]
        return ForwardTestDetailResponse(
            forward_test=await to_forward_test_response(self.database_url, row),
            metrics=to_forward_test_metrics_response(
                calculate_forward_test_metrics(row, equity_curve, fills, self.clock.read_now_utc())
            ),
            equity_curve=to_equity_curve_response(equity_curve),
            fills=[to_forward_test_fill_response(fill) for fill in forward_test_fills],
            instruments=to_instrument_responses(fills, members),
            same_period_backtests=[to_compared_backtest(backtest) for backtest in backtests if backtest is not None],
        )

    async def compare_with_backtest(self, forward_test_id: int, backtest_id: int) -> ForwardTestComparisonResponse:
        row = await self.read_forward_test_row(forward_test_id)
        backtest = await read_backtest_outcome(database_url=self.database_url, backtest_id=backtest_id)
        if backtest is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest not found.")
        if not is_same_setup(row, backtest):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=describe_other_setup(row))
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            forward_test_fills = await forward_test_records.select_forward_test_fills(
                connection,
                forward_test_id=forward_test_id,
                instrument=forward_test_store.read_single_instrument(row),
                uses_owner_ledger=row.allocated_capital_usd is not None,
            )
            fills = forward_test_records.list_trades(forward_test_fills)
            equity_curve = await forward_test_records.select_equity_curve(connection, forward_test_id)
            interruptions = await forward_test_store.select_interruptions(connection, forward_test_id)
        forward_test_metrics = limit_win_rate_to_period(
            calculate_forward_test_metrics(row, equity_curve, fills, self.clock.read_now_utc()),
            fills,
            backtest.request.time_range,
        )
        fill_rows = compare_fills(
            forward_test_fills=[
                dataclasses.replace(
                    forward_test_fill.trade,
                    symbol=forward_test_fill.instrument.symbol,
                    exchange=forward_test_fill.instrument.exchange,
                )
                for forward_test_fill in forward_test_fills
            ],
            backtest_fills=name_fills(backtest.trades, backtest.request.instrument),
            equity_curves=[equity_curve, backtest.equity_curve],
        )
        open_end_utc = row.stopped_at_utc or self.clock.read_now_utc()
        return ForwardTestComparisonResponse(
            forward_test=await to_forward_test_response(self.database_url, row),
            backtest=to_compared_backtest(backtest),
            forward_test_metrics=to_forward_test_metrics_response(forward_test_metrics),
            forward_test_equity_curve=to_equity_curve_response(equity_curve),
            backtest_equity_curve=to_equity_curve_response(backtest.equity_curve),
            fills=[to_fill_response(fill_row) for fill_row in fill_rows],
            interruptions=[to_interruption_response(interruption, open_end_utc) for interruption in interruptions],
        )


def create_forward_test_comparison_router(*, database_url: str, clock: Clock) -> APIRouter:
    routes = ComparisonRoutes(database_url=database_url, clock=clock)
    router = APIRouter(prefix="/api/forward-tests")
    router.add_api_route(
        "/{forward_test_id}/same-period-backtests",
        routes.start_same_period_backtest,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
    )
    router.add_api_route("/{forward_test_id}", routes.read_forward_test_detail, methods=["GET"])
    router.add_api_route("/{forward_test_id}/comparison/{backtest_id}", routes.compare_with_backtest, methods=["GET"])
    return router
