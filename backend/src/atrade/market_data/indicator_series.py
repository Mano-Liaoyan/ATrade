"""Indicators on bar charts: the catalog route and the indicator series route (indicator.md section 23.9.6).

The series route reads only saved bars and never calls IBKR. The chart first reads its bars with the bars route,
which saves them. For each indicator the route also reads the last `screen_look_back_bars(parameters)` saved bars
before the range (the warm-up), gives all bars to `update(bar)` of the indicator class, and returns the values of the
range. So a chart value is equal to the screen value at the same daily bar.
"""

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, Literal, cast

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, JsonValue

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.indicator import INDICATOR_CATALOG, IndicatorProblem, check_indicator_reference, create_indicator
from atrade.market_data.bar_models import InstrumentField, find_range_problem
from atrade.market_data.bar_reading import BarRequest, limit_to_complete_bars, read_saved_bars
from atrade.market_data.bar_source import BarSource, check_source_order, read_source_order

# The warm-up read range, as the look-back of a backtest (backtest.md section 10.3.1): a daily bar comes on about 252
# of 365 days, an intraday bar only in the trading hours. The range is at least 7 days.
DAILY_CALENDAR_FACTOR = 2
INTRADAY_CALENDAR_FACTOR = 6
MIN_WARM_UP_LENGTH = timedelta(days=7)


class IndicatorParameterResponse(BaseModel):
    name: str
    value_type: Literal["int", "float"]
    default: int | float
    minimum: int | float
    maximum: int | float
    # False for a parameter that the UI name does not show (bars_per_year).
    is_in_name: bool


class IndicatorResponse(BaseModel):
    """One indicator of the catalog (indicator.md sections 23.3 and 23.9.2)."""

    key: str
    name: str
    # The legend name of a bar chart starts with it, for example `BB`.
    short_name: str
    # `price`: on the price pane of a bar chart. `own`: in an own pane.
    chart_placement: Literal["price", "own"]
    parameters: list[IndicatorParameterResponse]
    outputs: list[str]
    # The meaning, the range, and the unit of the value.
    value_description: str


def list_indicator_catalog() -> list[IndicatorResponse]:
    """The indicator catalog in its own order. The screen page and the bar charts read it."""
    return [
        IndicatorResponse(
            key=definition.key,
            name=definition.name,
            short_name=definition.short_name,
            chart_placement=definition.chart_placement,
            parameters=[
                IndicatorParameterResponse(
                    name=parameter.name,
                    value_type="int" if parameter.value_type is int else "float",
                    default=parameter.default,
                    minimum=parameter.minimum,
                    maximum=parameter.maximum,
                    is_in_name=parameter.is_in_name,
                )
                for parameter in definition.parameters
            ],
            outputs=list(definition.outputs),
            value_description=definition.value_description,
        )
        for definition in INDICATOR_CATALOG.values()
    ]


class IndicatorSeriesBody(BaseModel):
    symbol: InstrumentField
    exchange: InstrumentField
    currency: InstrumentField
    bar_period: BarPeriod
    start_utc: AwareDatetime
    end_utc: AwareDatetime
    # Without source_order, the route reads through the global source order.
    source_order: list[BarSource] | None = None
    # Each item is `{"indicator", "parameters"}`. The route checks them with `check_indicator_reference`, so that each
    # problem has its location.
    indicators: list[JsonValue]


class IndicatorSeries(BaseModel):
    indicator: str
    # All parameters, with the defaults.
    parameters: dict[str, int | float]
    # One value for each time of the answer. None is "no value".
    outputs: dict[str, list[float | None]]


class IndicatorSeriesResponse(BaseModel):
    # The start (UNIX seconds) of each saved bar of the range, oldest first.
    times: list[int]
    series: list[IndicatorSeries]


class IndicatorProblemResponse(BaseModel):
    # The path in the request body, for example ["indicators", 0, "parameters", "period"].
    location: list[str | int]
    message: str


class IndicatorCheckFailedResponse(BaseModel):
    problems: list[IndicatorProblemResponse]


def find_warm_up_length(bar_period: BarPeriod, bar_count: int) -> timedelta:
    """The read range before the start that holds `bar_count` saved bars of `bar_period`."""
    factor = DAILY_CALENDAR_FACTOR if bar_period == BarPeriod.ONE_DAY else INTRADAY_CALENDAR_FACTOR
    return max(bar_period.length * bar_count * factor, MIN_WARM_UP_LENGTH)


def check_indicator_list(indicators: list[JsonValue]) -> list[IndicatorProblemResponse]:
    problems: list[IndicatorProblemResponse] = []
    for index, reference in enumerate(indicators):
        indicator_problems: list[IndicatorProblem] = check_indicator_reference(reference, has_output=False)
        problems.extend(
            IndicatorProblemResponse(location=["indicators", index, *problem.location], message=problem.message)
            for problem in indicator_problems
        )
    return problems


def calculate_series(reference: Mapping[str, Any], warm_up_bars: list[Bar], bars: list[Bar]) -> IndicatorSeries:
    """Gives the last `screen_look_back_bars` warm-up bars and then the bars to `update(bar)` of a new indicator.
    Returns the outputs at the bars only."""
    definition = INDICATOR_CATALOG[reference["indicator"]]
    parameters = definition.with_defaults(reference.get("parameters", {}))
    indicator = create_indicator({"indicator": definition.key, "parameters": parameters}, has_output=False)
    warm_up_count = definition.screen_look_back_bars(parameters)
    for bar in warm_up_bars[-warm_up_count:]:
        indicator.update(bar)
    outputs: dict[str, list[float | None]] = {output: [] for output in definition.outputs}
    for bar in bars:
        indicator.update(bar)
        for output, values in outputs.items():
            value = cast("float | None", getattr(indicator, output))
            values.append(None if value is None else float(value))
    return IndicatorSeries(indicator=definition.key, parameters=parameters, outputs=outputs)


def create_indicator_series_router(*, database_url: str, clock: Clock) -> APIRouter:
    router = APIRouter()

    @router.get("/api/market-data/indicators")
    async def list_indicators(  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
    ) -> list[IndicatorResponse]:
        return list_indicator_catalog()

    @router.post(
        "/api/market-data/indicator-series",
        response_model=IndicatorSeriesResponse,
        responses={status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": IndicatorCheckFailedResponse}},
    )
    async def read_indicator_series(  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        body: IndicatorSeriesBody,
    ) -> IndicatorSeriesResponse | JSONResponse:
        """Reads only saved bars. A `422` for an indicator has the problem list. Other `422` answers have `detail`."""
        range_problem = find_range_problem(body.bar_period, body.start_utc, body.end_utc)
        if range_problem is not None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=range_problem)
        source_order_problem = None if body.source_order is None else check_source_order(body.source_order)
        if source_order_problem is not None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=source_order_problem)
        problems = check_indicator_list(body.indicators)
        if problems:
            failure = IndicatorCheckFailedResponse(problems=problems)
            return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=failure.model_dump())
        source_order = body.source_order or await read_source_order(database_url=database_url)
        instrument = Instrument(
            symbol=body.symbol.strip(), exchange=body.exchange.strip(), currency=body.currency.strip()
        )
        complete_range = limit_to_complete_bars(TimeRange(body.start_utc, body.end_utc), body.bar_period, clock)
        if complete_range is None:
            return IndicatorSeriesResponse(times=[], series=[])
        bars = await read_bars(database_url, source_order, BarRequest(instrument, body.bar_period, complete_range))
        references = [cast("Mapping[str, Any]", reference) for reference in body.indicators]
        warm_up_count = max(
            (
                INDICATOR_CATALOG[reference["indicator"]].screen_look_back_bars(reference.get("parameters", {}))
                for reference in references
            ),
            default=0,
        )
        warm_up_bars = await read_warm_up_bars(
            database_url, source_order, BarRequest(instrument, body.bar_period, complete_range), warm_up_count
        )
        return IndicatorSeriesResponse(
            times=[int(bar.start_utc.timestamp()) for bar in bars],
            series=[calculate_series(reference, warm_up_bars, bars) for reference in references],
        )

    return router


async def read_bars(database_url: str, source_order: list[BarSource], bar_request: BarRequest) -> list[Bar]:
    saved_bars = await read_saved_bars(database_url=database_url, bar_request=bar_request, source_order=source_order)
    return saved_bars.bars


async def read_warm_up_bars(
    database_url: str, source_order: list[BarSource], bar_request: BarRequest, bar_count: int
) -> list[Bar]:
    """The last `bar_count` saved bars before the start of the range. One read for all indicators of the request."""
    if bar_count == 0:
        return []
    start_utc: datetime = bar_request.time_range.start_utc
    warm_up_range = TimeRange(start_utc - find_warm_up_length(bar_request.bar_period, bar_count), start_utc)
    warm_up_request = BarRequest(bar_request.instrument, bar_request.bar_period, warm_up_range)
    return (await read_bars(database_url, source_order, warm_up_request))[-bar_count:]
