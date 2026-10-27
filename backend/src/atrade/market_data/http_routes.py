"""HTTP routes of market_data: instrument search and bars."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import AwareDatetime, BaseModel

from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection, GatewayRequestError
from atrade.market_data.bar_models import NOT_ONLY_SPACES_PATTERN, BarResponse, InstrumentField, to_bar_response
from atrade.market_data.bar_reading import BarReader, BarRequest, GatewayNotConnectedError
from atrade.market_data.live_bar_socket import create_live_bar_router

# IBKR symbols are short. A longer query is a mistake, so the route refuses it before it calls IBKR.
MAX_QUERY_LENGTH = 32


class InstrumentResponse(BaseModel):
    symbol: str
    exchange: str
    currency: str


class InstrumentSearchResponse(BaseModel):
    instruments: list[InstrumentResponse]


# One answer has at most this many bars, for example 13 days of 1 minute bars. This keeps IBKR requests few.
MAX_BARS_PER_REQUEST = 20_000
# The chart range when the request has no start. Each default range has at most about 4300 bars.
DEFAULT_RANGE_LENGTHS = {
    BarPeriod.ONE_MINUTE: timedelta(days=3),
    BarPeriod.FIVE_MINUTES: timedelta(days=10),
    BarPeriod.FIFTEEN_MINUTES: timedelta(days=30),
    BarPeriod.THIRTY_MINUTES: timedelta(days=60),
    BarPeriod.ONE_HOUR: timedelta(days=90),
    BarPeriod.ONE_DAY: timedelta(days=1096),
}


class ErrorResponse(BaseModel):
    detail: str


class BarsResponse(BaseModel):
    bars: list[BarResponse]


class BarsQuery(BaseModel):
    """The query parameters of GET /api/market-data/bars. Times need a time zone, for example `Z`."""

    symbol: InstrumentField
    exchange: InstrumentField
    currency: InstrumentField
    bar_period: BarPeriod
    # Without end_utc, the range ends now. Without start_utc, it starts DEFAULT_RANGE_LENGTHS before the end.
    start_utc: AwareDatetime | None = None
    end_utc: AwareDatetime | None = None


def create_market_data_router(
    *, gateway_connection: GatewayConnection, host: str, port: int, database_url: str, clock: Clock
) -> APIRouter:
    router = APIRouter()
    bar_reader = BarReader(database_url=database_url, clock=clock, gateway_connection=gateway_connection)

    @router.get(
        "/api/market-data/instrument-search",
        responses={
            status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
        },
    )
    async def search_instruments(  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        query: Annotated[str, Query(min_length=1, max_length=MAX_QUERY_LENGTH, pattern=NOT_ONLY_SPACES_PATTERN)],
    ) -> InstrumentSearchResponse:
        if not gateway_connection.is_connected():
            message = f"IB Gateway is not reachable at {host}:{port}. Instrument search needs IB Gateway."
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)
        try:
            instruments = await gateway_connection.search_instruments(query.strip())
        except GatewayRequestError as error:
            message = f"The instrument search failed: {error}"
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=message) from error
        instrument_responses = [
            InstrumentResponse(symbol=instrument.symbol, exchange=instrument.exchange, currency=instrument.currency)
            for instrument in instruments
        ]
        return InstrumentSearchResponse(instruments=instrument_responses)

    @router.get(
        "/api/market-data/bars",
        responses={
            status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
        },
    )
    async def read_bars(  # pyright: ignore[reportUnusedFunction] readability-exception: FastAPI registers the route through the decorator.
        bars_query: Annotated[BarsQuery, Query()],
    ) -> BarsResponse:
        """Returns the complete bars that start in the range, oldest first. Only missing ranges go to IBKR."""
        bar_period = bars_query.bar_period
        end_utc = bars_query.end_utc or clock.read_now_utc()
        start_utc = bars_query.start_utc or end_utc - DEFAULT_RANGE_LENGTHS[bar_period]
        if start_utc >= end_utc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="start_utc must be before end_utc.")
        if (end_utc - start_utc) / bar_period.length > MAX_BARS_PER_REQUEST:
            message = f"The range has more than {MAX_BARS_PER_REQUEST} bars of {bar_period.value}. Use a shorter range."
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)
        instrument = Instrument(
            symbol=bars_query.symbol.strip(), exchange=bars_query.exchange.strip(), currency=bars_query.currency.strip()
        )
        bar_request = BarRequest(instrument=instrument, bar_period=bar_period, time_range=TimeRange(start_utc, end_utc))
        try:
            bars = await bar_reader.read_bars(bar_request)
        except GatewayNotConnectedError as error:
            message = f"IB Gateway is not reachable at {host}:{port}. Bars that are not saved need IB Gateway."
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=message) from error
        except GatewayRequestError as error:
            message = f"Reading bars from IB Gateway failed: {error}"
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=message) from error
        return BarsResponse(bars=[to_bar_response(bar) for bar in bars])

    router.include_router(create_live_bar_router(gateway_connection=gateway_connection, host=host, port=port))
    return router
