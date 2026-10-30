"""The daily bars of many instruments in one database read, and the daily bar summary (docs/architecture/market_data.md
section 8.11).

Both read through the global source order with the merge rule of section 8.7.2. The source order is read in the same
SQL statement, so a read of many instruments is one database query.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import psycopg
from psycopg import sql
from psycopg.rows import class_row

from atrade.foundation.bar import Bar, BarPeriod
from atrade.foundation.instrument import Instrument
from atrade.indicator import AverageTradingValue
from atrade.market_data.bar_source import DEFAULT_SOURCE_ORDER, BarSource, bar_table, saved_range_table

SUMMARY_BAR_COUNT = 20


@dataclass(frozen=True)
class DailyBarSummary:
    instrument: Instrument
    last_day_start_utc: datetime
    last_close: Decimal
    # The value of `AverageTradingValue(20)` for the last 20 daily bars. None: fewer than 20 daily bars.
    average_trading_value_20: float | None


@dataclass(frozen=True)
class InstrumentBarRow:
    instrument_position: int
    start_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


def create_range_contains_bar(bar_source: BarSource) -> sql.Composed:
    """True when a saved range of `bar_source` holds the start of the bar `bar`."""
    return sql.SQL("""
        EXISTS (
            SELECT 1 FROM {saved_range_table} AS saved_range
            WHERE saved_range.symbol = bar.symbol AND saved_range.exchange = bar.exchange
                AND saved_range.currency = bar.currency AND saved_range.bar_period = bar.bar_period
                AND saved_range.start_utc <= bar.start_utc AND saved_range.end_utc > bar.start_utc
        )""").format(saved_range_table=saved_range_table(bar_source))


def create_source_bars_query(bar_source: BarSource) -> sql.Composed:
    """The bars of one bar source that the merge rule keeps: inside a saved range of the bar source, and not inside a
    saved range of a bar source that is earlier in the source order."""
    earlier_source_conditions = [
        sql.SQL(
            "NOT (array_position(global_order.bar_sources, {other}) < array_position(global_order.bar_sources, {own})"
            " AND {contains})"
        ).format(
            other=sql.Literal(other_source.value),
            own=sql.Literal(bar_source.value),
            contains=create_range_contains_bar(other_source),
        )
        for other_source in BarSource
        if other_source != bar_source
    ]
    return sql.SQL("""
        SELECT bar.start_utc, bar.open, bar.high, bar.low, bar.close, bar.volume
        FROM {bar_table} AS bar
        WHERE bar.symbol = instrument.symbol AND bar.exchange = instrument.exchange
            AND bar.currency = instrument.currency AND bar.bar_period = %(bar_period)s
            AND (%(before_utc)s::timestamptz IS NULL OR bar.start_utc < %(before_utc)s::timestamptz)
            AND {own_range}
            {earlier_sources}
    """).format(
        bar_table=bar_table(bar_source),
        own_range=create_range_contains_bar(bar_source),
        earlier_sources=sql.SQL(" ").join(sql.SQL("AND ") + condition for condition in earlier_source_conditions),
    )


# For each instrument, the last `bar_count` daily bars of the merge. LIMIT in a LATERAL read uses the primary key.
LAST_DAILY_BARS_QUERY = sql.SQL("""
    WITH global_order AS (
        SELECT coalesce((SELECT bar_sources FROM source_order), %(default_source_order)s::text[]) AS bar_sources
    )
    SELECT instrument.position AS instrument_position, merged.start_utc, merged.open, merged.high, merged.low,
        merged.close, merged.volume
    FROM unnest(%(symbols)s::text[], %(exchanges)s::text[], %(currencies)s::text[])
            WITH ORDINALITY AS instrument (symbol, exchange, currency, position)
        CROSS JOIN global_order
        CROSS JOIN LATERAL (
            SELECT * FROM ({source_queries}) AS source_bar
            ORDER BY source_bar.start_utc DESC
            LIMIT %(bar_count)s
        ) AS merged
    ORDER BY instrument.position, merged.start_utc
""").format(
    source_queries=sql.SQL(" UNION ALL ").join(create_source_bars_query(bar_source) for bar_source in BarSource)
)


def create_last_daily_bars_parameters(
    instruments: list[Instrument], before_utc: datetime | None, bar_count: int
) -> dict[str, object]:
    return {
        "default_source_order": [bar_source.value for bar_source in DEFAULT_SOURCE_ORDER],
        "symbols": [instrument.symbol for instrument in instruments],
        "exchanges": [instrument.exchange for instrument in instruments],
        "currencies": [instrument.currency for instrument in instruments],
        "bar_period": BarPeriod.ONE_DAY.value,
        "before_utc": before_utc,
        "bar_count": bar_count,
    }


def group_bar_rows(instruments: list[Instrument], rows: list[InstrumentBarRow]) -> dict[Instrument, list[Bar]]:
    bars_by_instrument: defaultdict[Instrument, list[Bar]] = defaultdict(list)
    for row in rows:
        # WITH ORDINALITY counts from 1.
        bars_by_instrument[instruments[row.instrument_position - 1]].append(
            Bar(
                start_utc=row.start_utc,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
            )
        )
    return {instrument: bars_by_instrument[instrument] for instrument in instruments}


async def select_last_daily_bars(
    connection: psycopg.AsyncConnection, instruments: list[Instrument], before_utc: datetime | None, bar_count: int
) -> dict[Instrument, list[Bar]]:
    unique_instruments = list(dict.fromkeys(instruments))
    async with connection.cursor(row_factory=class_row(InstrumentBarRow)) as cursor:
        await cursor.execute(
            LAST_DAILY_BARS_QUERY, create_last_daily_bars_parameters(unique_instruments, before_utc, bar_count)
        )
        rows = await cursor.fetchall()
    return group_bar_rows(unique_instruments, rows)


def select_last_daily_bars_blocking(
    connection: psycopg.Connection, instruments: list[Instrument], before_utc: datetime | None, bar_count: int
) -> dict[Instrument, list[Bar]]:
    unique_instruments = list(dict.fromkeys(instruments))
    with connection.cursor(row_factory=class_row(InstrumentBarRow)) as cursor:
        cursor.execute(
            LAST_DAILY_BARS_QUERY, create_last_daily_bars_parameters(unique_instruments, before_utc, bar_count)
        )
        rows = cursor.fetchall()
    return group_bar_rows(unique_instruments, rows)


async def read_last_daily_bars(
    *, database_url: str, instruments: list[Instrument], before_utc: datetime, bar_count: int
) -> dict[Instrument, list[Bar]]:
    """For each instrument, the last `bar_count` daily bars that start before `before_utc`, oldest first, merged in
    the global source order. One database query for all instruments. No IBKR call."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await select_last_daily_bars(connection, instruments, before_utc, bar_count)


def calculate_daily_bar_summary(instrument: Instrument, bars: list[Bar]) -> DailyBarSummary:
    """The summary of the daily bars of one instrument, oldest first. The indicator class calculates the average
    trading value, so screens and strategies get the same value (ADR 0001)."""
    average_trading_value = AverageTradingValue(SUMMARY_BAR_COUNT)
    for bar in bars[-SUMMARY_BAR_COUNT:]:
        average_trading_value.update(bar)
    last_bar = bars[-1]
    return DailyBarSummary(
        instrument=instrument,
        last_day_start_utc=last_bar.start_utc,
        last_close=last_bar.close,
        average_trading_value_20=average_trading_value.value,
    )


UPSERT_SUMMARIES_QUERY = sql.SQL("""
    INSERT INTO daily_bar_summary (
        symbol, exchange, currency, last_day_start_utc, last_close, average_trading_value_20
    )
    SELECT * FROM unnest(
        %(symbols)s::text[], %(exchanges)s::text[], %(currencies)s::text[], %(last_day_start_utc)s::timestamptz[],
        %(last_close)s::numeric[], %(average_trading_value_20)s::double precision[]
    )
    ON CONFLICT (symbol, exchange, currency) DO UPDATE SET
        last_day_start_utc = excluded.last_day_start_utc, last_close = excluded.last_close,
        average_trading_value_20 = excluded.average_trading_value_20
""")

# An instrument without daily bars has no summary row.
DELETE_SUMMARIES_QUERY = sql.SQL("""
    DELETE FROM daily_bar_summary AS summary
    USING unnest(%(symbols)s::text[], %(exchanges)s::text[], %(currencies)s::text[])
        AS instrument (symbol, exchange, currency)
    WHERE summary.symbol = instrument.symbol AND summary.exchange = instrument.exchange
        AND summary.currency = instrument.currency
""")


def create_instrument_parameters(instruments: list[Instrument]) -> dict[str, list[str]]:
    return {
        "symbols": [instrument.symbol for instrument in instruments],
        "exchanges": [instrument.exchange for instrument in instruments],
        "currencies": [instrument.currency for instrument in instruments],
    }


def create_summary_statements(
    bars_by_instrument: dict[Instrument, list[Bar]],
) -> list[tuple[sql.Composed | sql.SQL, dict[str, object]]]:
    summaries = [
        calculate_daily_bar_summary(instrument, bars) for instrument, bars in bars_by_instrument.items() if bars
    ]
    instruments_without_bars = [instrument for instrument, bars in bars_by_instrument.items() if not bars]
    upsert_parameters: dict[str, object] = {
        **create_instrument_parameters([summary.instrument for summary in summaries]),
        "last_day_start_utc": [summary.last_day_start_utc for summary in summaries],
        "last_close": [summary.last_close for summary in summaries],
        "average_trading_value_20": [summary.average_trading_value_20 for summary in summaries],
    }
    return [
        (UPSERT_SUMMARIES_QUERY, upsert_parameters),
        (DELETE_SUMMARIES_QUERY, {**create_instrument_parameters(instruments_without_bars)}),
    ]


async def update_daily_bar_summaries(connection: psycopg.AsyncConnection, instruments: list[Instrument]) -> None:
    """Calculates the summary rows of `instruments` again from their saved daily bars."""
    if not instruments:
        return
    bars_by_instrument = await select_last_daily_bars(connection, instruments, None, SUMMARY_BAR_COUNT)
    async with connection.cursor() as cursor:
        for query, parameters in create_summary_statements(bars_by_instrument):
            await cursor.execute(query, parameters)


def update_daily_bar_summaries_blocking(connection: psycopg.Connection, instruments: list[Instrument]) -> None:
    """`update_daily_bar_summaries` for synchronous callers: the Databento import and the forward test DataActor."""
    if not instruments:
        return
    bars_by_instrument = select_last_daily_bars_blocking(connection, instruments, None, SUMMARY_BAR_COUNT)
    with connection.cursor() as cursor:
        for query, parameters in create_summary_statements(bars_by_instrument):
            cursor.execute(query, parameters)


async def update_all_daily_bar_summaries(connection: psycopg.AsyncConnection) -> None:
    """Calculates all summary rows again, for example after a change of the global source order. It reads each
    instrument with a saved daily range in a bar source, so daily bars saved before the summary table existed also
    get a row."""
    instrument_queries = [
        sql.SQL("SELECT symbol, exchange, currency FROM {} WHERE bar_period = %(bar_period)s").format(
            saved_range_table(bar_source)
        )
        for bar_source in BarSource
    ]
    query = sql.SQL(" UNION ").join(
        [*instrument_queries, sql.SQL("SELECT symbol, exchange, currency FROM daily_bar_summary")]
    )
    async with connection.cursor() as cursor:
        await cursor.execute(query, {"bar_period": BarPeriod.ONE_DAY.value})
        rows = await cursor.fetchall()
    instruments = [Instrument(symbol=str(row[0]), exchange=str(row[1]), currency=str(row[2])) for row in rows]
    await update_daily_bar_summaries(connection, instruments)


async def read_daily_bar_summaries(*, database_url: str, instruments: list[Instrument]) -> list[DailyBarSummary]:
    """The summary rows of `instruments`, in the order of `instruments`. An instrument without daily bars has no
    row."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection, connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT summary.symbol, summary.exchange, summary.currency, summary.last_day_start_utc,
                summary.last_close, summary.average_trading_value_20
            FROM unnest(%(symbols)s::text[], %(exchanges)s::text[], %(currencies)s::text[])
                    WITH ORDINALITY AS instrument (symbol, exchange, currency, position)
                JOIN daily_bar_summary AS summary USING (symbol, exchange, currency)
            ORDER BY instrument.position
            """,
            create_instrument_parameters(instruments),
        )
        rows = await cursor.fetchall()
    return [
        DailyBarSummary(
            instrument=Instrument(symbol=str(row[0]), exchange=str(row[1]), currency=str(row[2])),
            last_day_start_utc=row[3],
            last_close=row[4],
            average_trading_value_20=row[5],
        )
        for row in rows
    ]
