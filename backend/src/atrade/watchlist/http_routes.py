"""HTTP routes of the watchlist capability: add, delete, and list the instruments that the user saves."""

from datetime import datetime
from typing import Annotated

import psycopg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, StringConstraints

from atrade.foundation.bar import BarPeriod
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.market_data import (
    BarSource,
    GatewayNotReachableError,
    InstrumentLookup,
    InstrumentLookupFailedError,
    read_saved_bar_coverage,
)
from atrade.watchlist import watchlist_store

# The same limits as the CHECK constraints of the watchlist_instrument table.
MAX_SYMBOL_LENGTH = 32
MAX_EXCHANGE_LENGTH = 32
MAX_CURRENCY_LENGTH = 8

Symbol = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SYMBOL_LENGTH)]
Exchange = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_EXCHANGE_LENGTH)]
Currency = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_CURRENCY_LENGTH)]


class AddInstrumentRequest(BaseModel):
    symbol: Symbol
    exchange: Exchange
    currency: Currency


class SavedBarsResponse(BaseModel):
    """The saved bars of one bar source and one bar period: the start of the first and of the last saved bar."""

    bar_source: BarSource
    bar_period: BarPeriod
    first_start_utc: datetime
    last_start_utc: datetime


class WatchlistInstrumentResponse(BaseModel):
    id: int
    symbol: str
    exchange: str
    currency: str
    added_at_utc: datetime
    # Only the bar sources and bar periods with saved bars, in the order of BarPeriod, then in the global source order.
    # The backtest form offers only these bar periods.
    saved_bars: list[SavedBarsResponse]


class WatchlistResponse(BaseModel):
    instruments: list[WatchlistInstrumentResponse]


class WatchlistErrorResponse(BaseModel):
    detail: str


async def to_instrument_responses(
    database_url: str, records: list[watchlist_store.WatchlistInstrumentRecord]
) -> list[WatchlistInstrumentResponse]:
    instruments = [
        Instrument(symbol=record.symbol, exchange=record.exchange, currency=record.currency) for record in records
    ]
    coverage = await read_saved_bar_coverage(database_url=database_url, instruments=instruments)
    return [
        WatchlistInstrumentResponse(
            id=record.id,
            symbol=record.symbol,
            exchange=record.exchange,
            currency=record.currency,
            added_at_utc=record.added_at_utc,
            saved_bars=[
                SavedBarsResponse(
                    bar_source=item.bar_source,
                    bar_period=item.bar_period,
                    first_start_utc=item.first_start_utc,
                    last_start_utc=item.last_start_utc,
                )
                for item in instrument_coverage
            ],
        )
        for record, instrument_coverage in zip(records, coverage, strict=True)
    ]


class WatchlistRoutes:
    """The route functions. They share the database URL, the clock, and the instrument lookup."""

    def __init__(self, *, database_url: str, clock: Clock, instrument_lookup: InstrumentLookup) -> None:
        self.database_url = database_url
        self.clock = clock
        self.instrument_lookup = instrument_lookup

    async def add_instrument(self, request: AddInstrumentRequest) -> WatchlistInstrumentResponse:
        """Checks the instrument through market_data first, so the watchlist holds only instruments that IBKR knows."""
        requested_instrument = Instrument(symbol=request.symbol, exchange=request.exchange, currency=request.currency)
        try:
            found_instrument = await self.instrument_lookup.find_instrument(requested_instrument)
        except GatewayNotReachableError as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except InstrumentLookupFailedError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
        if found_instrument is None:
            message = (
                f"IBKR has no instrument {request.symbol} / {request.exchange} / {request.currency}. "
                "Add an instrument from the instrument search."
            )
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=message)
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            record = await watchlist_store.insert_instrument(
                connection, instrument=found_instrument, added_at_utc=self.clock.read_now_utc()
            )
            await connection.commit()
        if record is None:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="This instrument is already in the watchlist.")
        [response] = await to_instrument_responses(self.database_url, [record])
        return response

    async def list_instruments(self) -> WatchlistResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            records = await watchlist_store.select_instruments(connection)
        return WatchlistResponse(instruments=await to_instrument_responses(self.database_url, records))

    async def delete_instrument(self, watchlist_instrument_id: int) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            is_deleted = await watchlist_store.delete_instrument(connection, watchlist_instrument_id)
        if not is_deleted:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="This instrument is not in the watchlist.")


def create_watchlist_router(*, database_url: str, clock: Clock, instrument_lookup: InstrumentLookup) -> APIRouter:
    routes = WatchlistRoutes(database_url=database_url, clock=clock, instrument_lookup=instrument_lookup)
    router = APIRouter(prefix="/api/watchlist")
    router.add_api_route(
        "",
        routes.add_instrument,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_404_NOT_FOUND: {"model": WatchlistErrorResponse},
            status.HTTP_409_CONFLICT: {"model": WatchlistErrorResponse},
            status.HTTP_502_BAD_GATEWAY: {"model": WatchlistErrorResponse},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": WatchlistErrorResponse},
        },
    )
    router.add_api_route("", routes.list_instruments, methods=["GET"])
    router.add_api_route(
        "/{watchlist_instrument_id}",
        routes.delete_instrument,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses={status.HTTP_404_NOT_FOUND: {"model": WatchlistErrorResponse}},
    )
    return router
