"""SQL for the bar table and the saved-range table of each bar source. Only the market_data capability reads or
writes them."""

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg import sql
from psycopg.rows import class_row

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data.bar_source import BarSource, bar_table, saved_range_table


@dataclass(frozen=True)
class SavedBarCoverage:
    """The first and the last saved bar of one bar source, one instrument, and one bar period."""

    bar_source: BarSource
    bar_period: BarPeriod
    first_start_utc: datetime
    last_start_utc: datetime


@dataclass(frozen=True)
class SavedBarCoverageRow:
    instrument_position: int
    bar_period: str
    first_start_utc: datetime
    last_start_utc: datetime


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


def create_range_parameters(instrument: Instrument, bar_period: BarPeriod, time_range: TimeRange) -> dict[str, object]:
    return {
        **create_key_parameters(instrument, bar_period),
        "start_utc": time_range.start_utc,
        "end_utc": time_range.end_utc,
    }


async def select_bars(
    connection: psycopg.AsyncConnection,
    bar_source: BarSource,
    instrument: Instrument,
    bar_period: BarPeriod,
    time_range: TimeRange,
) -> list[Bar]:
    async with connection.cursor(row_factory=class_row(Bar)) as cursor:
        await cursor.execute(
            sql.SQL("""
            SELECT start_utc, open, high, low, close, volume
            FROM {bar_table}
            WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
                AND bar_period = %(bar_period)s AND start_utc >= %(start_utc)s AND start_utc < %(end_utc)s
            ORDER BY start_utc
            """).format(bar_table=bar_table(bar_source)),
            create_range_parameters(instrument, bar_period, time_range),
        )
        return await cursor.fetchall()


async def has_bars(
    connection: psycopg.AsyncConnection,
    bar_source: BarSource,
    instrument: Instrument,
    bar_period: BarPeriod,
    time_range: TimeRange,
) -> bool:
    """True when at least one bar starts in `time_range`. The same rows as `select_bars`, without reading them."""
    async with connection.cursor() as cursor:
        await cursor.execute(
            sql.SQL("""
            SELECT EXISTS (
                SELECT 1
                FROM {bar_table}
                WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
                    AND bar_period = %(bar_period)s AND start_utc >= %(start_utc)s AND start_utc < %(end_utc)s
            )
            """).format(bar_table=bar_table(bar_source)),
            create_range_parameters(instrument, bar_period, time_range),
        )
        row = await cursor.fetchone()
    return row is not None and bool(row[0])


async def select_saved_bar_coverage(
    connection: psycopg.AsyncConnection, source_order: list[BarSource], instruments: list[Instrument]
) -> list[list[SavedBarCoverage]]:
    """Returns, for each instrument, the bar sources and bar periods that have saved bars: in the order of BarPeriod,
    then in the source order.

    One query for each bar source. min() and max() of each instrument and bar period use the primary key.
    """
    coverage: list[list[SavedBarCoverage]] = [[] for _ in instruments]
    for bar_source in source_order:
        rows = await select_saved_bar_coverage_rows(connection, bar_source, instruments)
        for row in rows:
            # WITH ORDINALITY counts from 1.
            coverage[row.instrument_position - 1].append(
                SavedBarCoverage(
                    bar_source=bar_source,
                    bar_period=BarPeriod(row.bar_period),
                    first_start_utc=row.first_start_utc,
                    last_start_utc=row.last_start_utc,
                )
            )
    bar_periods = list(BarPeriod)
    # sort() keeps the source order inside one bar period.
    for instrument_coverage in coverage:
        instrument_coverage.sort(key=lambda item: bar_periods.index(item.bar_period))
    return coverage


async def select_saved_bar_coverage_rows(
    connection: psycopg.AsyncConnection, bar_source: BarSource, instruments: list[Instrument]
) -> list[SavedBarCoverageRow]:
    async with connection.cursor(row_factory=class_row(SavedBarCoverageRow)) as cursor:
        await cursor.execute(
            sql.SQL("""
            SELECT instrument.position AS instrument_position, period.bar_period,
                coverage.first_start_utc, coverage.last_start_utc
            FROM unnest(%(symbols)s::text[], %(exchanges)s::text[], %(currencies)s::text[])
                    WITH ORDINALITY AS instrument (symbol, exchange, currency, position)
                CROSS JOIN unnest(%(bar_periods)s::text[]) WITH ORDINALITY AS period (bar_period, position)
                CROSS JOIN LATERAL (
                    SELECT min(bar.start_utc) AS first_start_utc, max(bar.start_utc) AS last_start_utc
                    FROM {bar_table} AS bar
                    WHERE bar.symbol = instrument.symbol AND bar.exchange = instrument.exchange
                        AND bar.currency = instrument.currency AND bar.bar_period = period.bar_period
                ) AS coverage
            WHERE coverage.first_start_utc IS NOT NULL
            ORDER BY instrument.position, period.position
            """).format(bar_table=bar_table(bar_source)),
            {
                "symbols": [instrument.symbol for instrument in instruments],
                "exchanges": [instrument.exchange for instrument in instruments],
                "currencies": [instrument.currency for instrument in instruments],
                "bar_periods": [bar_period.value for bar_period in BarPeriod],
            },
        )
        return await cursor.fetchall()


async def select_saved_ranges(
    connection: psycopg.AsyncConnection,
    bar_source: BarSource,
    instrument: Instrument,
    bar_period: BarPeriod,
    time_range: TimeRange,
) -> list[TimeRange]:
    """Returns the saved ranges of one bar source that overlap `time_range`, ordered by start."""
    async with connection.cursor(row_factory=class_row(SavedRangeRow)) as cursor:
        await cursor.execute(
            sql.SQL("""
            SELECT start_utc, end_utc
            FROM {saved_range_table}
            WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
                AND bar_period = %(bar_period)s AND start_utc < %(end_utc)s AND end_utc > %(start_utc)s
            ORDER BY start_utc
            """).format(saved_range_table=saved_range_table(bar_source)),
            create_range_parameters(instrument, bar_period, time_range),
        )
        rows = await cursor.fetchall()
    return [TimeRange(start_utc=row.start_utc, end_utc=row.end_utc) for row in rows]


# One statement for all bars of a range: a row-by-row insert of a few thousand bars took seconds on a loaded host.
# The bars route, forward tests, and the other IBKR readers write ibkr_bar. The Databento import has its own SQL.
INSERT_BARS_QUERY = sql.SQL("""
    INSERT INTO {bar_table} (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
    SELECT %(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, new_bar.*
    FROM unnest(
        %(start_utc)s::timestamptz[], %(open)s::numeric[], %(high)s::numeric[], %(low)s::numeric[],
        %(close)s::numeric[], %(volume)s::numeric[]
    ) AS new_bar (start_utc, open, high, low, close, volume)
    ON CONFLICT (symbol, exchange, currency, bar_period, start_utc) DO UPDATE SET
        open = excluded.open, high = excluded.high, low = excluded.low,
        close = excluded.close, volume = excluded.volume
""").format(bar_table=bar_table(BarSource.IBKR))

# Join the new range with each saved range that overlaps or touches it, so the table stays small.
JOIN_SAVED_RANGE_TEMPLATE = sql.SQL("""
    WITH joined AS (
        DELETE FROM {saved_range_table}
        WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
            AND bar_period = %(bar_period)s AND start_utc <= %(end_utc)s AND end_utc >= %(start_utc)s
        RETURNING start_utc, end_utc
    )
    INSERT INTO {saved_range_table} (symbol, exchange, currency, bar_period, start_utc, end_utc)
    SELECT %(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s,
        least(%(start_utc)s, min(joined.start_utc)), greatest(%(end_utc)s, max(joined.end_utc))
    FROM joined
""")
JOIN_SAVED_RANGE_QUERY = JOIN_SAVED_RANGE_TEMPLATE.format(saved_range_table=saved_range_table(BarSource.IBKR))


def create_bars_parameters(key_parameters: dict[str, str], bars: list[Bar]) -> dict[str, object]:
    """One array for each column. One statement cannot update a row twice, so a later bar with the same start wins."""
    bars_by_start = {bar.start_utc: bar for bar in bars}
    unique_bars = list(bars_by_start.values())
    return {
        **key_parameters,
        "start_utc": [bar.start_utc for bar in unique_bars],
        "open": [bar.open for bar in unique_bars],
        "high": [bar.high for bar in unique_bars],
        "low": [bar.low for bar in unique_bars],
        "close": [bar.close for bar in unique_bars],
        "volume": [bar.volume for bar in unique_bars],
    }


async def save_bars_of_range(
    connection: psycopg.AsyncConnection,
    instrument: Instrument,
    bar_period: BarPeriod,
    time_range: TimeRange,
    bars: list[Bar],
) -> None:
    """Saves the bars that IBKR returned for `time_range` in ibkr_bar, and records the range as saved. One transaction.

    A bar that is already saved gets the new values, so a second save of the same bars adds no row.
    """
    key_parameters = create_key_parameters(instrument, bar_period)
    async with connection.transaction(), connection.cursor() as cursor:
        await cursor.execute(INSERT_BARS_QUERY, create_bars_parameters(key_parameters, bars))
        await cursor.execute(
            JOIN_SAVED_RANGE_QUERY,
            {**key_parameters, "start_utc": time_range.start_utc, "end_utc": time_range.end_utc},
        )


def save_bars_of_range_blocking(
    connection: psycopg.Connection,
    instrument: Instrument,
    bar_period: BarPeriod,
    time_range: TimeRange,
    bars: list[Bar],
) -> None:
    """`save_bars_of_range` for synchronous callers, for example a NautilusTrader actor in `on_bar`."""
    key_parameters = create_key_parameters(instrument, bar_period)
    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute(INSERT_BARS_QUERY, create_bars_parameters(key_parameters, bars))
        cursor.execute(
            JOIN_SAVED_RANGE_QUERY,
            {**key_parameters, "start_utc": time_range.start_utc, "end_utc": time_range.end_utc},
        )
