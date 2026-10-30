"""The members of a screen result for a fixed-list backtest (docs/architecture/screen.md section 24.9)."""

import psycopg

from atrade.foundation.instrument import Instrument
from atrade.screen import screen_store


async def read_screen_result_members(*, database_url: str, screen_result_id: int) -> list[Instrument] | None:
    """The instruments of the screen result in position order. None when the screen result is missing."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        if await screen_store.select_screen_result(connection, screen_result_id) is None:
            return None
        cursor = await connection.execute(
            "SELECT symbol, exchange, currency FROM screen_result_row WHERE screen_result_id = %(id)s"
            " ORDER BY position",
            {"id": screen_result_id},
        )
        rows = await cursor.fetchall()
    return [Instrument(symbol=row[0], exchange=row[1], currency=row[2]) for row in rows]
