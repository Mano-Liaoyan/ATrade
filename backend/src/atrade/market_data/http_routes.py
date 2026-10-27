"""GET /api/market-data/instrument-search: finds instruments by symbol through IB Gateway."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from atrade.ibkr import GatewayConnection, GatewayRequestError

# IBKR symbols are short. A longer query is a mistake, so the route refuses it before it calls IBKR.
MAX_QUERY_LENGTH = 32
# The query must have at least one character that is not a space.
NOT_ONLY_SPACES_PATTERN = r"\S"


class InstrumentResponse(BaseModel):
    symbol: str
    exchange: str
    currency: str


class InstrumentSearchResponse(BaseModel):
    instruments: list[InstrumentResponse]


class ErrorResponse(BaseModel):
    detail: str


def create_market_data_router(*, gateway_connection: GatewayConnection, host: str, port: int) -> APIRouter:
    router = APIRouter()

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

    return router
