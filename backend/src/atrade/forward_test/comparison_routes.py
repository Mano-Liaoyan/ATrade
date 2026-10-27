"""HTTP routes of the forward test comparison: start a backtest of the same period, and compare the forward test with
a backtest (docs/architecture/forward_test.md section 12.10).
"""

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
    EquityPoint,
    calculate_metrics,
    check_backtest_request,
    queue_backtest,
    read_backtest_outcome,
)
from atrade.forward_test import forward_test_records, forward_test_store
from atrade.forward_test.backtest_comparison import (
    FillComparisonRow,
    FillTotal,
    Interruption,
    compare_fills,
    find_interruptions,
)
from atrade.forward_test.forward_test_store import ForwardTestRow
from atrade.forward_test.http_routes import ForwardTestResponse, to_forward_test_response
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.clock import Clock


class SamePeriodBacktestResponse(BaseModel):
    backtest_id: int


class ComparedMetricsResponse(BaseModel):
    final_equity_usd: Decimal
    total_return_percent: Decimal
    max_drawdown_percent: Decimal
    trade_count: int


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
    forward_test_quantity_shares: Decimal | None
    forward_test_price_usd: Decimal | None
    backtest_quantity_shares: Decimal | None
    backtest_price_usd: Decimal | None
    price_difference_usd: Decimal | None


class InterruptionResponse(BaseModel):
    start_utc: datetime
    end_utc: datetime


class ForwardTestComparisonResponse(BaseModel):
    forward_test: ForwardTestResponse
    backtest: ComparedBacktestSummaryResponse
    # None until the forward test has a start balance.
    forward_test_metrics: ComparedMetricsResponse | None
    forward_test_equity_curve: list[ComparedEquityPointResponse]
    backtest_equity_curve: list[ComparedEquityPointResponse]
    fills: list[FillComparisonResponse]
    interruptions: list[InterruptionResponse]


def to_metrics_response(metrics: BacktestMetrics | None) -> ComparedMetricsResponse | None:
    if metrics is None:
        return None
    return ComparedMetricsResponse(
        final_equity_usd=metrics.final_equity_usd,
        total_return_percent=metrics.total_return_percent,
        max_drawdown_percent=metrics.max_drawdown_percent,
        trade_count=metrics.trade_count,
    )


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
        forward_test_quantity_shares=read_quantity(row.forward_test),
        forward_test_price_usd=read_price(row.forward_test),
        backtest_quantity_shares=read_quantity(row.backtest),
        backtest_price_usd=read_price(row.backtest),
        price_difference_usd=row.price_difference_usd,
    )


def to_interruption_response(interruption: Interruption) -> InterruptionResponse:
    return InterruptionResponse(start_utc=interruption.start_utc, end_utc=interruption.end_utc)


def to_compared_backtest(backtest: BacktestOutcome) -> ComparedBacktestSummaryResponse:
    return ComparedBacktestSummaryResponse(
        id=backtest.id,
        status=backtest.status,
        error_message=backtest.error_message,
        start_utc=backtest.request.time_range.start_utc,
        end_utc=backtest.request.time_range.end_utc,
        paper_capital_usd=backtest.request.paper_capital_usd,
        metrics=to_metrics_response(backtest.metrics),
    )


def is_same_setup(row: ForwardTestRow, backtest: BacktestOutcome) -> bool:
    request = backtest.request
    return (
        request.strategy_version_id == row.strategy_version_id
        and request.instrument == forward_test_store.read_instrument(row)
        and request.bar_period.value == row.bar_period
    )


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
        if row.start_balance_usd is None:
            detail = "The forward test has no start balance yet. The backtest uses it as the paper capital."
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        now_utc = self.clock.read_now_utc()
        request = BacktestRequest(
            strategy_version_id=row.strategy_version_id,
            instrument=forward_test_store.read_instrument(row),
            bar_period=BarPeriod(row.bar_period),
            time_range=TimeRange(start_utc=row.created_at_utc, end_utc=row.stopped_at_utc or now_utc),
            paper_capital_usd=row.start_balance_usd,
        )
        refusal = check_backtest_request(request)
        if refusal is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=refusal)
        backtest_id = await queue_backtest(database_url=self.database_url, request=request, created_at_utc=now_utc)
        return SamePeriodBacktestResponse(backtest_id=backtest_id)

    async def compare_with_backtest(self, forward_test_id: int, backtest_id: int) -> ForwardTestComparisonResponse:
        row = await self.read_forward_test_row(forward_test_id)
        backtest = await read_backtest_outcome(database_url=self.database_url, backtest_id=backtest_id)
        if backtest is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest not found.")
        if not is_same_setup(row, backtest):
            detail = (
                "The backtest must use the strategy version, the instrument, and the bar period of the forward test."
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            fills = await forward_test_records.select_fills(connection, forward_test_id)
            equity_curve = await forward_test_records.select_equity_curve(connection, forward_test_id)
        forward_test_metrics = None
        if row.start_balance_usd is not None:
            forward_test_metrics = calculate_metrics(
                paper_capital_usd=row.start_balance_usd, equity_curve=equity_curve, trade_count=len(fills)
            )
        fill_rows = compare_fills(
            forward_test_fills=fills,
            backtest_fills=backtest.trades,
            equity_curves=[equity_curve, backtest.equity_curve],
        )
        interruptions = find_interruptions(
            forward_test_curve=equity_curve, backtest_curve=backtest.equity_curve, bar_period=BarPeriod(row.bar_period)
        )
        return ForwardTestComparisonResponse(
            forward_test=await to_forward_test_response(self.database_url, row),
            backtest=to_compared_backtest(backtest),
            forward_test_metrics=to_metrics_response(forward_test_metrics),
            forward_test_equity_curve=to_equity_curve_response(equity_curve),
            backtest_equity_curve=to_equity_curve_response(backtest.equity_curve),
            fills=[to_fill_response(fill_row) for fill_row in fill_rows],
            interruptions=[to_interruption_response(interruption) for interruption in interruptions],
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
    router.add_api_route("/{forward_test_id}/comparison/{backtest_id}", routes.compare_with_backtest, methods=["GET"])
    return router
