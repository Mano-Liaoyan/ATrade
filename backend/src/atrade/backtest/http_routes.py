"""HTTP routes of the backtest capability: start a backtest, list backtests, and read one backtest with its results.

A new backtest waits in the queue. The backtest runner of the Web process starts it (backtest_runner.py).
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

import psycopg
from fastapi import APIRouter, HTTPException, status
from pydantic import AwareDatetime, BaseModel, Field

from atrade.backtest import backtest_store
from atrade.backtest.backtest_metrics import BacktestMetrics
from atrade.backtest.backtest_store import BacktestRequest, BacktestRow, BacktestStatus
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.strategy import read_strategy_version

# A backtest has no exchange rates, so the paper capital in USD can only buy USD instruments.
SUPPORTED_CURRENCY = "USD"
MAX_INSTRUMENT_FIELD_LENGTH = 32

InstrumentField = Annotated[str, Field(min_length=1, max_length=MAX_INSTRUMENT_FIELD_LENGTH)]


class StartBacktestRequest(BaseModel):
    strategy_version_id: int
    symbol: InstrumentField
    exchange: InstrumentField
    currency: InstrumentField
    bar_period: BarPeriod
    start_utc: AwareDatetime
    end_utc: AwareDatetime
    # Required, with no default: a backtest never starts with an unknown amount (docs/architecture.md section 10).
    paper_capital_usd: Annotated[Decimal, Field(gt=0)]


class BacktestMetricsResponse(BaseModel):
    final_equity_usd: Decimal
    total_return_percent: Decimal
    max_drawdown_percent: Decimal
    trade_count: int


class BacktestResponse(BaseModel):
    id: int
    strategy_version_id: int
    strategy_id: int
    strategy_name: str
    version_number: int
    symbol: str
    exchange: str
    currency: str
    bar_period: BarPeriod
    start_utc: datetime
    end_utc: datetime
    paper_capital_usd: Decimal
    status: BacktestStatus
    error_message: str | None
    created_at_utc: datetime
    started_at_utc: datetime | None
    ended_at_utc: datetime | None
    metrics: BacktestMetricsResponse | None


class EquityPointResponse(BaseModel):
    time_utc: datetime
    equity_usd: Decimal


class TradeResponse(BaseModel):
    time_utc: datetime
    side: Literal["BUY", "SELL"]
    quantity_shares: Decimal
    price_usd: Decimal
    commission_usd: Decimal


class BacktestDetailResponse(BacktestResponse):
    equity_curve: list[EquityPointResponse]
    trades: list[TradeResponse]


class ComparedBacktestResponse(BacktestDetailResponse):
    code: str


class BacktestComparisonResponse(BaseModel):
    strategy_id: int
    strategy_name: str
    first: ComparedBacktestResponse
    second: ComparedBacktestResponse


def to_metrics_response(metrics: BacktestMetrics | None) -> BacktestMetricsResponse | None:
    if metrics is None:
        return None
    return BacktestMetricsResponse(
        final_equity_usd=metrics.final_equity_usd,
        total_return_percent=metrics.total_return_percent,
        max_drawdown_percent=metrics.max_drawdown_percent,
        trade_count=metrics.trade_count,
    )


class BacktestRoutes:
    """The route functions. They share the database URL and the clock."""

    def __init__(self, *, database_url: str, clock: Clock) -> None:
        self.database_url = database_url
        self.clock = clock

    async def to_backtest_response(self, row: BacktestRow) -> BacktestResponse:
        strategy_version = await read_strategy_version(
            database_url=self.database_url, strategy_version_id=row.strategy_version_id
        )
        if strategy_version is None:
            message = f"Backtest {row.id} refers to strategy version {row.strategy_version_id}, which is missing."
            raise RuntimeError(message)
        return BacktestResponse(
            id=row.id,
            strategy_version_id=row.strategy_version_id,
            strategy_id=strategy_version.strategy_id,
            strategy_name=strategy_version.strategy_name,
            version_number=strategy_version.version_number,
            symbol=row.symbol,
            exchange=row.exchange,
            currency=row.currency,
            bar_period=BarPeriod(row.bar_period),
            start_utc=row.start_utc,
            end_utc=row.end_utc,
            paper_capital_usd=row.paper_capital_usd,
            status=row.status,
            error_message=row.error_message,
            created_at_utc=row.created_at_utc,
            started_at_utc=row.started_at_utc,
            ended_at_utc=row.ended_at_utc,
            metrics=to_metrics_response(backtest_store.read_metrics(row)),
        )

    async def start_backtest(self, request: StartBacktestRequest) -> BacktestResponse:
        if request.currency != SUPPORTED_CURRENCY:
            detail = f"A backtest supports only USD instruments. The instrument currency is {request.currency}."
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        if request.end_utc <= request.start_utc:
            detail = "The time range must end after it starts."
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        strategy_version = await read_strategy_version(
            database_url=self.database_url, strategy_version_id=request.strategy_version_id
        )
        if strategy_version is None:
            detail = f"Strategy version {request.strategy_version_id} does not exist."
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        backtest_request = BacktestRequest(
            strategy_version_id=request.strategy_version_id,
            instrument=Instrument(symbol=request.symbol, exchange=request.exchange, currency=request.currency),
            bar_period=request.bar_period,
            time_range=TimeRange(start_utc=request.start_utc, end_utc=request.end_utc),
            paper_capital_usd=request.paper_capital_usd,
        )
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            row = await backtest_store.insert_backtest(
                connection, request=backtest_request, created_at_utc=self.clock.read_now_utc()
            )
        return await self.to_backtest_response(row)

    async def list_backtests(self) -> list[BacktestResponse]:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            rows = await backtest_store.select_backtests(connection)
        return [await self.to_backtest_response(row) for row in rows]

    async def compare_backtests(self, first_backtest_id: int, second_backtest_id: int) -> BacktestComparisonResponse:
        """Compare two backtests of the same strategy: two versions, or one version with other request fields."""
        if first_backtest_id == second_backtest_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Select two different backtests."
            )
        first = await self.read_backtest(first_backtest_id)
        second = await self.read_backtest(second_backtest_id)
        if first.strategy_id != second.strategy_id:
            detail = (
                "Only backtests of the same strategy can be compared. "
                f"These backtests use {first.strategy_name} and {second.strategy_name}."
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        return BacktestComparisonResponse(
            strategy_id=first.strategy_id,
            strategy_name=first.strategy_name,
            first=await self.add_code(first),
            second=await self.add_code(second),
        )

    async def add_code(self, backtest: BacktestDetailResponse) -> ComparedBacktestResponse:
        strategy_version = await read_strategy_version(
            database_url=self.database_url, strategy_version_id=backtest.strategy_version_id
        )
        if strategy_version is None:
            message = (
                f"Backtest {backtest.id} refers to strategy version {backtest.strategy_version_id}, which is missing."
            )
            raise RuntimeError(message)
        return ComparedBacktestResponse(**backtest.model_dump(), code=strategy_version.code)

    async def read_backtest(self, backtest_id: int) -> BacktestDetailResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            row = await backtest_store.select_backtest(connection, backtest_id)
            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest not found.")
            equity_curve = await backtest_store.select_equity_curve(connection, backtest_id)
            trades = await backtest_store.select_trades(connection, backtest_id)
        backtest = await self.to_backtest_response(row)
        return BacktestDetailResponse(
            **backtest.model_dump(),
            equity_curve=[
                EquityPointResponse(time_utc=point.time_utc, equity_usd=point.equity_usd) for point in equity_curve
            ],
            trades=[
                TradeResponse(
                    time_utc=trade.time_utc,
                    side=trade.side,
                    quantity_shares=trade.quantity_shares,
                    price_usd=trade.price_usd,
                    commission_usd=trade.commission_usd,
                )
                for trade in trades
            ],
        )


def create_backtest_router(*, database_url: str, clock: Clock) -> APIRouter:
    routes = BacktestRoutes(database_url=database_url, clock=clock)
    router = APIRouter(prefix="/api/backtests")
    router.add_api_route("", routes.start_backtest, methods=["POST"], status_code=status.HTTP_201_CREATED)
    router.add_api_route("", routes.list_backtests, methods=["GET"])
    router.add_api_route("/{backtest_id}", routes.read_backtest, methods=["GET"])
    router.add_api_route(
        "/{first_backtest_id}/comparison/{second_backtest_id}", routes.compare_backtests, methods=["GET"]
    )
    return router
