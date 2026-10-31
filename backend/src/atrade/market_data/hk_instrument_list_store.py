"""SQL for the hk_instrument_list_member table. Only market_data reads or writes it."""

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import class_row

from atrade.foundation.instrument import Instrument


@dataclass(frozen=True)
class HkInstrumentListMemberRecord:
    id: int
    symbol: str
    exchange: str
    currency: str
    added_at_utc: datetime


async def insert_member(connection: psycopg.AsyncConnection, *, instrument: Instrument, added_at_utc: datetime) -> bool:
    """Returns False when the instrument is already in the HK instrument list."""
    cursor = await connection.execute(
        """
        INSERT INTO hk_instrument_list_member (symbol, exchange, currency, added_at_utc)
        VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(added_at_utc)s)
        ON CONFLICT (symbol, exchange, currency) DO NOTHING
        """,
        {
            "symbol": instrument.symbol,
            "exchange": instrument.exchange,
            "currency": instrument.currency,
            "added_at_utc": added_at_utc,
        },
    )
    return cursor.rowcount > 0


async def select_members(connection: psycopg.AsyncConnection) -> list[HkInstrumentListMemberRecord]:
    async with connection.cursor(row_factory=class_row(HkInstrumentListMemberRecord)) as cursor:
        await cursor.execute(
            "SELECT id, symbol, exchange, currency, added_at_utc FROM hk_instrument_list_member ORDER BY id"
        )
        return await cursor.fetchall()


async def delete_member(connection: psycopg.AsyncConnection, member_id: int) -> bool:
    """Returns False when no member of the HK instrument list has this ID."""
    cursor = await connection.execute("DELETE FROM hk_instrument_list_member WHERE id = %(id)s", {"id": member_id})
    return cursor.rowcount > 0


async def read_hk_instrument_list(*, database_url: str) -> list[Instrument]:
    """The instruments of the HK instrument list, in the order of adding. An HK screen starts from them."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        members = await select_members(connection)
    return [Instrument(symbol=member.symbol, exchange=member.exchange, currency=member.currency) for member in members]
