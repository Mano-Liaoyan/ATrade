"""SQL for the bar and bar_saved_range tables. Only the market_data capability reads or writes them."""

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import class_row

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument


@dataclass(frozen=True)
class SavedBarCoverage:
    """The first and the last saved bar of one instrument and one bar period."""

    bar_period: BarPeriod
    first_start_utc: datetime
    last_start_utc: datetime


@dataclass(frozen=True)
class SavedBarCoverageRow:
    bar_period: str
    first_start_utc: datetime | None
    last_start_utc: datetime | None


@dataclass(frozen=True)
class SavedRangeRow:
    start_utc: datetime
    end_utc: datetime


def create_key_parameters(instrument: Instrument, bar_period: BarPeriod) -> dict[str, str]:
    return {
        "symbol": instrument.symbol,
        "exchange": instrument.exchange,
        "currency": instrument.currency,
        "bar_period": bar_period.value,
    }


async def select_bars(
    connection: psycopg.AsyncConnection, instrument: Instrument, bar_period: BarPeriod, time_range: TimeRange
) -> list[Bar]:
    async with connection.cursor(row_factory=class_row(Bar)) as cursor:
        await cursor.execute(
            """
            SELECT start_utc, open, high, low, close, volume
            FROM bar
            WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
                AND bar_period = %(bar_period)s AND start_utc >= %(start_utc)s AND start_utc < %(end_utc)s
            ORDER BY start_utc
            """,
            {
                **create_key_parameters(instrument, bar_period),
                "start_utc": time_range.start_utc,
                "end_utc": time_range.end_utc,
            },
        )
        return await cursor.fetchall()


async def has_bars(
    connection: psycopg.AsyncConnection, instrument: Instrument, bar_period: BarPeriod, time_range: TimeRange
) -> bool:
    """True when at least one bar starts in `time_range`. The same rows as `select_bars`, without reading them."""
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM bar
                WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
                    AND bar_period = %(bar_period)s AND start_utc >= %(start_utc)s AND start_utc < %(end_utc)s
            )
            """,
            {
                **create_key_parameters(instrument, bar_period),
                "start_utc": time_range.start_utc,
                "end_utc": time_range.end_utc,
            },
        )
        row = await cursor.fetchone()
    return row is not None and bool(row[0])


async def select_saved_bar_coverage(
    connection: psycopg.AsyncConnection, instrument: Instrument
) -> list[SavedBarCoverage]:
    """Returns the bar periods that have saved bars, in the order of BarPeriod. min() and max() use the primary key."""
    async with connection.cursor(row_factory=class_row(SavedBarCoverageRow)) as cursor:
        await cursor.execute(
            """
            SELECT
                period.bar_period,
                (SELECT min(bar.start_utc) FROM bar
                    WHERE bar.symbol = %(symbol)s AND bar.exchange = %(exchange)s AND bar.currency = %(currency)s
                        AND bar.bar_period = period.bar_period) AS first_start_utc,
                (SELECT max(bar.start_utc) FROM bar
                    WHERE bar.symbol = %(symbol)s AND bar.exchange = %(exchange)s AND bar.currency = %(currency)s
                        AND bar.bar_period = period.bar_period) AS last_start_utc
            FROM unnest(%(bar_periods)s::text[]) WITH ORDINALITY AS period (bar_period, position)
            ORDER BY period.position
            """,
            {
                "symbol": instrument.symbol,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
                "bar_periods": [bar_period.value for bar_period in BarPeriod],
            },
        )
        rows = await cursor.fetchall()
    return [
        SavedBarCoverage(
            bar_period=BarPeriod(row.bar_period), first_start_utc=row.first_start_utc, last_start_utc=row.last_start_utc
        )
        for row in rows
        if row.first_start_utc is not None and row.last_start_utc is not None
    ]


async def select_saved_ranges(
    connection: psycopg.AsyncConnection, instrument: Instrument, bar_period: BarPeriod, time_range: TimeRange
) -> list[TimeRange]:
    """Returns the saved ranges that overlap `time_range`, ordered by start."""
    async with connection.cursor(row_factory=class_row(SavedRangeRow)) as cursor:
        await cursor.execute(
            """
            SELECT start_utc, end_utc
            FROM bar_saved_range
            WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
                AND bar_period = %(bar_period)s AND start_utc < %(end_utc)s AND end_utc > %(start_utc)s
            ORDER BY start_utc
            """,
            {
                **create_key_parameters(instrument, bar_period),
                "start_utc": time_range.start_utc,
                "end_utc": time_range.end_utc,
            },
        )
        rows = await cursor.fetchall()
    return [TimeRange(start_utc=row.start_utc, end_utc=row.end_utc) for row in rows]


async def save_bars_of_range(
    connection: psycopg.AsyncConnection,
    instrument: Instrument,
    bar_period: BarPeriod,
    time_range: TimeRange,
    bars: list[Bar],
) -> None:
    """Saves the bars that IBKR returned for `time_range`, and records the range as saved. One transaction."""
    key_parameters = create_key_parameters(instrument, bar_period)
    async with connection.transaction(), connection.cursor() as cursor:
        await cursor.executemany(
            """
            INSERT INTO bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, %(start_utc)s,
                %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
            ON CONFLICT (symbol, exchange, currency, bar_period, start_utc) DO UPDATE SET
                open = excluded.open, high = excluded.high, low = excluded.low,
                close = excluded.close, volume = excluded.volume
            """,
            [
                {
                    **key_parameters,
                    "start_utc": bar.start_utc,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in bars
            ],
        )
        # Join the new range with each saved range that overlaps or touches it, so the table stays small.
        await cursor.execute(
            """
            WITH joined AS (
                DELETE FROM bar_saved_range
                WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
                    AND bar_period = %(bar_period)s AND start_utc <= %(end_utc)s AND end_utc >= %(start_utc)s
                RETURNING start_utc, end_utc
            )
            INSERT INTO bar_saved_range (symbol, exchange, currency, bar_period, start_utc, end_utc)
            SELECT %(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s,
                least(%(start_utc)s, min(joined.start_utc)), greatest(%(end_utc)s, max(joined.end_utc))
            FROM joined
            """,
            {**key_parameters, "start_utc": time_range.start_utc, "end_utc": time_range.end_utc},
        )
