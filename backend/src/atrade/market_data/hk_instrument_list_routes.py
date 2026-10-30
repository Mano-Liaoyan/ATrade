"""HTTP routes of the HK instrument list: add pasted symbols, list, and delete (market_data.md section 8.10)."""

from datetime import datetime
from typing import Annotated

import psycopg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, StringConstraints

from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.market_data import hk_instrument_list_store
from atrade.market_data.instrument_lookup import (
    GatewayNotReachableError,
    InstrumentLookup,
    InstrumentLookupFailedError,
)

HK_EXCHANGE = "SEHK"
HK_CURRENCY = "HKD"
# The same limit as the CHECK constraint of the hk_instrument_list_member table.
MAX_SYMBOL_LENGTH = 32

Symbol = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SYMBOL_LENGTH)]


class AddHkInstrumentsRequest(BaseModel):
    symbols: Annotated[list[Symbol], Field(min_length=1)]


class AddHkInstrumentsResponse(BaseModel):
    """The pasted symbols in their order. A symbol that is pasted 2 times is in already_in_list the second time."""

    added: list[str]
    not_found: list[str]
    already_in_list: list[str]


class HkInstrumentResponse(BaseModel):
    id: int
    symbol: str
    exchange: str
    currency: str
    added_at_utc: datetime


class HkInstrumentListResponse(BaseModel):
    instruments: list[HkInstrumentResponse]


class HkInstrumentListErrorResponse(BaseModel):
    detail: str


class HkInstrumentListRoutes:
    """The route functions. They share the database URL, the clock, and the instrument lookup."""

    def __init__(self, *, database_url: str, clock: Clock, instrument_lookup: InstrumentLookup) -> None:
        self.database_url = database_url
        self.clock = clock
        self.instrument_lookup = instrument_lookup

    async def find_hk_instrument(self, symbol: str) -> Instrument | None:
        instrument = Instrument(symbol=symbol, exchange=HK_EXCHANGE, currency=HK_CURRENCY)
        try:
            return await self.instrument_lookup.find_instrument(instrument)
        except GatewayNotReachableError as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except InstrumentLookupFailedError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    async def add_instruments(self, request: AddHkInstrumentsRequest) -> AddHkInstrumentsResponse:
        """Checks all new symbols through IBKR first. On a 502 or 503, the list does not change."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            listed_symbols = {member.symbol for member in await hk_instrument_list_store.select_members(connection)}
        found: list[Instrument] = []
        not_found: list[str] = []
        already_in_list: list[str] = []
        for symbol in request.symbols:
            if symbol in listed_symbols:
                already_in_list.append(symbol)
                continue
            listed_symbols.add(symbol)
            instrument = await self.find_hk_instrument(symbol)
            if instrument is None:
                not_found.append(symbol)
            else:
                found.append(instrument)
        added: list[str] = []
        added_at_utc = self.clock.read_now_utc()
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            for instrument in found:
                is_added = await hk_instrument_list_store.insert_member(
                    connection, instrument=instrument, added_at_utc=added_at_utc
                )
                (added if is_added else already_in_list).append(instrument.symbol)
            await connection.commit()
        return AddHkInstrumentsResponse(added=added, not_found=not_found, already_in_list=already_in_list)

    async def list_instruments(self) -> HkInstrumentListResponse:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            members = await hk_instrument_list_store.select_members(connection)
        instruments = [
            HkInstrumentResponse(
                id=member.id,
                symbol=member.symbol,
                exchange=member.exchange,
                currency=member.currency,
                added_at_utc=member.added_at_utc,
            )
            for member in members
        ]
        return HkInstrumentListResponse(instruments=instruments)

    async def delete_instrument(self, member_id: int) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            is_deleted = await hk_instrument_list_store.delete_member(connection, member_id)
        if not is_deleted:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="This instrument is not in the HK instrument list.")


def create_hk_instrument_list_router(
    *, database_url: str, clock: Clock, instrument_lookup: InstrumentLookup
) -> APIRouter:
    routes = HkInstrumentListRoutes(database_url=database_url, clock=clock, instrument_lookup=instrument_lookup)
    router = APIRouter(prefix="/api/market-data/hk-instrument-list")
    router.add_api_route(
        "",
        routes.add_instruments,
        methods=["POST"],
        responses={
            status.HTTP_502_BAD_GATEWAY: {"model": HkInstrumentListErrorResponse},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HkInstrumentListErrorResponse},
        },
    )
    router.add_api_route("", routes.list_instruments, methods=["GET"])
    router.add_api_route(
        "/{member_id}",
        routes.delete_instrument,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
        responses={status.HTTP_404_NOT_FOUND: {"model": HkInstrumentListErrorResponse}},
    )
    return router
