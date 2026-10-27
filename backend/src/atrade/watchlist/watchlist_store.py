"""SQL for the watchlist_instrument table. Only the watchlist capability reads or writes it."""

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import class_row

from atrade.foundation.instrument import Instrument


@dataclass(frozen=True)
class WatchlistInstrumentRecord:
    id: int
    symbol: str
    exchange: str
    currency: str
    added_at_utc: datetime


async def insert_instrument(
    connection: psycopg.AsyncConnection, *, instrument: Instrument, added_at_utc: datetime
) -> WatchlistInstrumentRecord | None:
    """Returns None when the instrument is already in the watchlist."""
    async with connection.cursor(row_factory=class_row(WatchlistInstrumentRecord)) as cursor:
        await cursor.execute(
            """
            INSERT INTO watchlist_instrument (symbol, exchange, currency, added_at_utc)
            VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(added_at_utc)s)
            ON CONFLICT (symbol, exchange, currency) DO NOTHING
            RETURNING id, symbol, exchange, currency, added_at_utc
            """,
            {
                "symbol": instrument.symbol,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
                "added_at_utc": added_at_utc,
            },
        )
        return await cursor.fetchone()


async def select_instruments(connection: psycopg.AsyncConnection) -> list[WatchlistInstrumentRecord]:
    async with connection.cursor(row_factory=class_row(WatchlistInstrumentRecord)) as cursor:
        await cursor.execute(
            "SELECT id, symbol, exchange, currency, added_at_utc FROM watchlist_instrument ORDER BY id"
        )
        return await cursor.fetchall()


async def delete_instrument(connection: psycopg.AsyncConnection, watchlist_instrument_id: int) -> bool:
    """Returns False when no watchlist instrument has this ID."""
    cursor = await connection.execute(
        "DELETE FROM watchlist_instrument WHERE id = %(id)s", {"id": watchlist_instrument_id}
    )
    return cursor.rowcount > 0
