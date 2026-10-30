"""HTTP routes of the backtest capability: start a backtest, list backtests, read one backtest with its results,
and read or change the backtest limits (timeout and concurrency).

A new backtest waits in the queue. The backtest runner of the Web process starts it (backtest_runner.py).
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, HTTPException, status
from pydantic import AwareDatetime, BaseModel, Field

from atrade.backtest import backtest_store
from atrade.backtest.backtest_access import (
    add_global_source_order,
    check_backtest_request,
    check_saved_bars,
    has_survivorship_bias,
)
from atrade.backtest.backtest_exchange_rates import save_exchange_rates
from atrade.backtest.backtest_limits import (
    MAX_CONCURRENCY,
    MAX_TIMEOUT_SECONDS,
    BacktestLimits,
    read_backtest_limits,
    save_backtest_limits,
)
from atrade.backtest.backtest_metrics import (
    PERCENT,
    BacktestMetrics,
    BacktestTrade,
    EquityPoint,
    SplitMetrics,
    calculate_split_metrics,
    round_value,
)
from atrade.backtest.backtest_robustness import SharpeProbabilityKind, read_robustness
from atrade.backtest.backtest_store import BacktestRequest, BacktestRow, BacktestStatus
from atrade.backtest.sharpe_probability import SharpeProbabilityStatus
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.clock import Clock
from atrade.foundation.error_response import ERROR_RESPONSE, REFUSED_OR_NOT_VALID_RESPONSE
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarSource, ExchangeRateReader
from atrade.strategy import read_strategy_version, read_strategy_versions

MAX_INSTRUMENT_FIELD_LENGTH = 32
DEFAULT_OUT_OF_SAMPLE_SHARE = 30
MAX_OUT_OF_SAMPLE_SHARE = 50

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
    # The last percent of the range that is out of sample (docs/architecture/backtest.md section 10.9.4). 0 is no split.
    out_of_sample_share: Annotated[int, Field(ge=0, le=MAX_OUT_OF_SAMPLE_SHARE)] = DEFAULT_OUT_OF_SAMPLE_SHARE
    # Only for this backtest. Without it, the global source order (docs/architecture/backtest.md section 10.12).
    source_order: list[BarSource] | None = None


class BacktestLimitsBody(BaseModel):
    """The request and the response of the backtest limits routes."""

    timeout_seconds: Annotated[int, Field(ge=1, le=MAX_TIMEOUT_SECONDS)]
    concurrency: Annotated[int, Field(ge=1, le=MAX_CONCURRENCY)]


class BacktestMetricsResponse(BaseModel):
    """The metrics of docs/architecture/backtest.md section 10.9.2. A metric without a meaning is null, and
    `missing_reasons` gives its reason by its field name (section 10.9.3). The page shows "–" with the reason."""

    final_equity_usd: Decimal
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
    out_of_sample_share: int
    split_time_utc: datetime | None
    metrics: BacktestMetricsResponse | None
    # Null for a backtest from before the source order. The bar counts are null until the backtest finishes.
    source_order: list[BarSource] | None
    bar_count_by_source: dict[BarSource, int] | None
    survivorship_bias: bool


class SplitMetricsResponse(BaseModel):
    in_sample: BacktestMetricsResponse
    out_of_sample: BacktestMetricsResponse


class EquityPointResponse(BaseModel):
    time_utc: datetime
    equity_usd: Decimal


class TradeResponse(BaseModel):
    time_utc: datetime
    side: Literal["BUY", "SELL"]
    quantity_shares: Decimal
    price_usd: Decimal
    commission_usd: Decimal


class BacktestRobustnessResponse(BaseModel):
    """The robustness checks of docs/architecture/backtest.md sections 10.9.4 and 10.9.5, calculated at each read. A
    value without a meaning is null. `missing_reasons` gives the reason of a null `sharpe_probability_percent`."""

    trial_count: int
    sharpe_probability_percent: Decimal | None
    sharpe_probability_kind: SharpeProbabilityKind
    sharpe_probability_status: SharpeProbabilityStatus | None
    missing_reasons: dict[str, str]
    # Null without a split, when a Sharpe ratio is null, or when the in-sample Sharpe ratio is 0 or below.
    out_of_sample_to_in_sample_sharpe_percent: Decimal | None
    # Null without a split.
    out_of_sample_use_count: int | None


class BacktestDetailResponse(BacktestResponse):
    equity_curve: list[EquityPointResponse]
    trades: list[TradeResponse]
    split_metrics: SplitMetricsResponse | None
    robustness: BacktestRobustnessResponse


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
    return to_present_metrics_response(metrics)


def to_present_metrics_response(metrics: BacktestMetrics) -> BacktestMetricsResponse:
    return BacktestMetricsResponse(
        final_equity_usd=metrics.final_equity_usd,
        total_return_percent=metrics.total_return_percent,
        max_drawdown_percent=metrics.max_drawdown_percent,
        trade_count=metrics.trade_count,
        cagr_percent=metrics.cagr_percent,
        annual_volatility_percent=metrics.annual_volatility_percent,
        sharpe_ratio=metrics.sharpe_ratio,
        sortino_ratio=metrics.sortino_ratio,
        calmar_ratio=metrics.calmar_ratio,
        profit_factor=metrics.profit_factor,
        average_win_usd=metrics.average_win_usd,
        average_win_percent=metrics.average_win_percent,
        average_loss_usd=metrics.average_loss_usd,
        exposure_percent=metrics.exposure_percent,
        turnover_per_year=metrics.turnover_per_year,
        win_rate_percent=metrics.win_rate_percent,
        missing_reasons=metrics.missing_reasons,
    )


def calculate_finished_split_metrics(
    row: BacktestRow, equity_curve: list[EquityPoint], trades: list[BacktestTrade]
) -> SplitMetrics | None:
    """The split metrics from the saved equity curve and fills, or None without a split or a result."""
    if row.split_time_utc is None or backtest_store.read_metrics(row) is None:
        return None
    return calculate_split_metrics(
        paper_capital_usd=row.paper_capital_usd,
        time_range=TimeRange(start_utc=row.start_utc, end_utc=row.end_utc),
        equity_curve=equity_curve,
        trades=trades,
        split_time_utc=row.split_time_utc,
    )


def calculate_sharpe_percent(split_metrics: SplitMetrics | None) -> Decimal | None:
    """The out-of-sample Sharpe ratio as a percent of the in-sample Sharpe ratio. None when the in-sample Sharpe ratio
    is 0 or below, because a percent of such a value has no meaning."""
    if split_metrics is None:
        return None
    in_sample_sharpe = split_metrics.in_sample.sharpe_ratio
    out_of_sample_sharpe = split_metrics.out_of_sample.sharpe_ratio
    if in_sample_sharpe is None or out_of_sample_sharpe is None or in_sample_sharpe <= 0:
        return None
    return round_value(out_of_sample_sharpe / in_sample_sharpe * PERCENT)


class BacktestRoutes:
    """The route functions. They share the database URL and the clock."""

    def __init__(self, *, database_url: str, clock: Clock, exchange_rate_reader: ExchangeRateReader) -> None:
        self.database_url = database_url
        self.clock = clock
        self.exchange_rate_reader = exchange_rate_reader

    async def to_backtest_response(self, row: BacktestRow) -> BacktestResponse:
        strategy_version = await read_strategy_version(
            database_url=self.database_url, strategy_version_id=row.strategy_version_id
        )
        if strategy_version is None:
            message = f"Backtest {row.id} refers to strategy version {row.strategy_version_id}, which is missing."
            raise RuntimeError(message)
        request = backtest_store.read_request(row)
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
            out_of_sample_share=row.out_of_sample_share,
            split_time_utc=row.split_time_utc,
            metrics=to_metrics_response(backtest_store.read_metrics(row)),
            source_order=request.source_order,
            bar_count_by_source=None
            if row.bar_count_by_source is None
            else {BarSource(value): count for value, count in row.bar_count_by_source.items()},
            survivorship_bias=has_survivorship_bias(request),
        )

    async def start_backtest(self, request: StartBacktestRequest) -> BacktestResponse:
        backtest_request = BacktestRequest(
            strategy_version_id=request.strategy_version_id,
            instrument=Instrument(symbol=request.symbol, exchange=request.exchange, currency=request.currency),
            bar_period=request.bar_period,
            time_range=TimeRange(start_utc=request.start_utc, end_utc=request.end_utc),
            paper_capital_usd=request.paper_capital_usd,
            out_of_sample_share=request.out_of_sample_share,
            source_order=request.source_order,
        )
        refusal = check_backtest_request(backtest_request)
        if refusal is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=refusal)
        strategy_version = await read_strategy_version(
            database_url=self.database_url, strategy_version_id=request.strategy_version_id
        )
        if strategy_version is None:
            detail = f"Strategy version {request.strategy_version_id} does not exist."
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        backtest_request = await add_global_source_order(database_url=self.database_url, request=backtest_request)
        # Refuse before the row exists: a backtest without saved bars can only fail (docs/architecture/backtest.md 10.3).
        missing_bars = await check_saved_bars(database_url=self.database_url, request=backtest_request)
        if missing_bars is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=missing_bars)
        # The child never calls IBKR, so the rates of an instrument that is not in USD are saved first (section 10.8).
        missing_rates = await save_exchange_rates(
            database_url=self.database_url, exchange_rate_reader=self.exchange_rate_reader, request=backtest_request
        )
        if missing_rates is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=missing_rates)
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
            out_of_sample_use_count = await self.count_out_of_sample_uses(connection, row)
        backtest = await self.to_backtest_response(row)
        split_metrics = calculate_finished_split_metrics(row, equity_curve, trades)
        robustness = await read_robustness(
            database_url=self.database_url, row=row, strategy_id=backtest.strategy_id, equity_curve=equity_curve
        )
        return BacktestDetailResponse(
            **backtest.model_dump(),
            robustness=BacktestRobustnessResponse(
                trial_count=robustness.trial_count,
                sharpe_probability_percent=robustness.sharpe_probability_percent,
                sharpe_probability_kind=robustness.sharpe_probability_kind,
                sharpe_probability_status=robustness.sharpe_probability_status,
                missing_reasons=robustness.missing_reasons,
                out_of_sample_to_in_sample_sharpe_percent=calculate_sharpe_percent(split_metrics),
                out_of_sample_use_count=out_of_sample_use_count,
            ),
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
            split_metrics=(
                None
                if split_metrics is None
                else SplitMetricsResponse(
                    in_sample=to_present_metrics_response(split_metrics.in_sample),
                    out_of_sample=to_present_metrics_response(split_metrics.out_of_sample),
                )
            ),
        )

    async def count_out_of_sample_uses(self, connection: psycopg.AsyncConnection, row: BacktestRow) -> int | None:
        """The finished backtests of the same strategy (all versions), instrument, and bar period whose out-of-sample
        part overlaps the out-of-sample part of `row`. The count includes `row`. None without a split."""
        if row.split_time_utc is None:
            return None
        overlapping = await backtest_store.select_overlapping_out_of_sample_parts(connection, row)
        versions = await read_strategy_versions(
            database_url=self.database_url,
            strategy_version_ids=sorted({backtest.strategy_version_id for backtest in overlapping}),
        )
        strategy_id = versions[row.strategy_version_id].strategy_id
        return sum(versions[backtest.strategy_version_id].strategy_id == strategy_id for backtest in overlapping)

    async def read_limits(self) -> BacktestLimitsBody:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            limits = await read_backtest_limits(connection)
        return BacktestLimitsBody(timeout_seconds=limits.timeout_seconds, concurrency=limits.concurrency)

    async def change_limits(self, request: BacktestLimitsBody) -> BacktestLimitsBody:
        limits = BacktestLimits(timeout_seconds=request.timeout_seconds, concurrency=request.concurrency)
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            await save_backtest_limits(connection, limits)
        return request


def create_backtest_router(*, database_url: str, clock: Clock, exchange_rate_reader: ExchangeRateReader) -> APIRouter:
    routes = BacktestRoutes(database_url=database_url, clock=clock, exchange_rate_reader=exchange_rate_reader)
    router = APIRouter(prefix="/api")
    refused: dict[int | str, dict[str, Any]] = {status.HTTP_422_UNPROCESSABLE_CONTENT: REFUSED_OR_NOT_VALID_RESPONSE}
    not_found: dict[int | str, dict[str, Any]] = {status.HTTP_404_NOT_FOUND: ERROR_RESPONSE}
    router.add_api_route(
        "/backtests",
        routes.start_backtest,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        responses=refused,
    )
    router.add_api_route("/backtests", routes.list_backtests, methods=["GET"])
    router.add_api_route("/backtests/{backtest_id}", routes.read_backtest, methods=["GET"], responses=not_found)
    router.add_api_route("/backtest-limits", routes.read_limits, methods=["GET"])
    router.add_api_route("/backtest-limits", routes.change_limits, methods=["PUT"])
    router.add_api_route(
        "/backtests/{first_backtest_id}/comparison/{second_backtest_id}",
        routes.compare_backtests,
        methods=["GET"],
        responses={**refused, **not_found},
    )
    return router
