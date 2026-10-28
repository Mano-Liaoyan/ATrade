"""SQL for the exchange_rate and exchange_rate_saved_range tables. Only the market_data capability reads or writes
them."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import LiteralString

import psycopg
from psycopg.rows import class_row

from atrade.foundation.bar import TimeRange


@dataclass(frozen=True)
class SavedExchangeRate:
    """`usd_per_unit` USD for 1 currency unit at the close of the day that starts at `day_start_utc`."""

    day_start_utc: datetime
    usd_per_unit: Decimal


@dataclass(frozen=True)
class SavedRangeRow:
    start_utc: datetime
    end_utc: datetime


async def select_exchange_rates(
    connection: psycopg.AsyncConnection, currency: str, time_range: TimeRange
) -> list[SavedExchangeRate]:
    async with connection.cursor(row_factory=class_row(SavedExchangeRate)) as cursor:
        await cursor.execute(
            """
            SELECT day_start_utc, usd_per_unit
            FROM exchange_rate
            WHERE currency = %(currency)s AND day_start_utc >= %(start_utc)s AND day_start_utc < %(end_utc)s
            ORDER BY day_start_utc
            """,
            {"currency": currency, "start_utc": time_range.start_utc, "end_utc": time_range.end_utc},
        )
        return await cursor.fetchall()


async def select_saved_ranges(
    connection: psycopg.AsyncConnection, currency: str, time_range: TimeRange
) -> list[TimeRange]:
    """Returns the saved ranges that overlap `time_range`, ordered by start."""
    async with connection.cursor(row_factory=class_row(SavedRangeRow)) as cursor:
        await cursor.execute(
            """
            SELECT start_utc, end_utc
            FROM exchange_rate_saved_range
            WHERE currency = %(currency)s AND start_utc < %(end_utc)s AND end_utc > %(start_utc)s
            ORDER BY start_utc
            """,
            {"currency": currency, "start_utc": time_range.start_utc, "end_utc": time_range.end_utc},
        )
        rows = await cursor.fetchall()
    return [TimeRange(start_utc=row.start_utc, end_utc=row.end_utc) for row in rows]


INSERT_EXCHANGE_RATES_QUERY: LiteralString = """
    INSERT INTO exchange_rate (currency, day_start_utc, usd_per_unit)
    SELECT %(currency)s, new_rate.*
    FROM unnest(%(day_start_utc)s::timestamptz[], %(usd_per_unit)s::numeric[]) AS new_rate (day_start_utc, usd_per_unit)
    ON CONFLICT (currency, day_start_utc) DO UPDATE SET usd_per_unit = excluded.usd_per_unit
"""

# Join the new range with each saved range that overlaps or touches it, so the table stays small.
JOIN_SAVED_RANGE_QUERY: LiteralString = """
    WITH joined AS (
        DELETE FROM exchange_rate_saved_range
        WHERE currency = %(currency)s AND start_utc <= %(end_utc)s AND end_utc >= %(start_utc)s
        RETURNING start_utc, end_utc
    )
    INSERT INTO exchange_rate_saved_range (currency, start_utc, end_utc)
    SELECT %(currency)s, least(%(start_utc)s, min(joined.start_utc)), greatest(%(end_utc)s, max(joined.end_utc))
    FROM joined
"""


async def save_exchange_rates_of_range(
    connection: psycopg.AsyncConnection, currency: str, time_range: TimeRange, rates: list[SavedExchangeRate]
) -> None:
    """Saves the rates that IBKR returned for `time_range`, and records the range as saved. One transaction."""
    # One statement cannot update a row twice, so a later rate of the same day wins.
    rates_by_day = {rate.day_start_utc: rate for rate in rates}
    async with connection.transaction(), connection.cursor() as cursor:
        await cursor.execute(
            INSERT_EXCHANGE_RATES_QUERY,
            {
                "currency": currency,
                "day_start_utc": list(rates_by_day),
                "usd_per_unit": [rate.usd_per_unit for rate in rates_by_day.values()],
            },
        )
        await cursor.execute(
            JOIN_SAVED_RANGE_QUERY,
            {"currency": currency, "start_utc": time_range.start_utc, "end_utc": time_range.end_utc},
        )
