"""Databento hourly bars: the purchase list and the import of the XNAS.ITCH `ohlcv-1h` bars
(docs/architecture/market_data.md sections 8.8.1, 8.8.2, and 8.14).

The import keeps the 7 bars that start from 9:00 to 15:00 ET, and only in the quarters in which the instrument is in
the quarterly US universe. The 9:00 ET bar starts at 9:30 ET, the start of the first IBKR regular-hours bar. Its open
is the official open: the open of the Databento daily bar of that day.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import LiteralString

import psycopg

from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data.bar_source import BarSource, saved_range_table
from atrade.market_data.bar_store import JOIN_SAVED_RANGE_TEMPLATE, create_key_parameters

QUARTER_MONTHS = 3
JOIN_HOURLY_SAVED_RANGE_QUERY = JOIN_SAVED_RANGE_TEMPLATE.format(
    saved_range_table=saved_range_table(BarSource.DATABENTO)
)

COPY_HOURLY_RECORDS: LiteralString = """
    COPY databento_hourly_record (symbol, start_utc, open, high, low, close, volume) FROM STDIN
"""

SELECT_SYMBOL_LINKS: LiteralString = """
    SELECT old_symbol, new_symbol, change_day FROM databento_symbol_link ORDER BY change_day, id
"""

# Section 8.8.4: the history of an old symbol is under its new symbol.
MOVE_HOURLY_TO_NEW_SYMBOL: LiteralString = """
    UPDATE databento_hourly_record SET symbol = %(new_symbol)s
    WHERE symbol = %(old_symbol)s AND start_utc < %(change_day)s::timestamp AT TIME ZONE 'UTC'
"""

HOURLY_RECORD_IN_NEW_YORK: LiteralString = """
    WITH hourly AS (
        SELECT symbol, start_utc, open, high, low, close, volume,
            (start_utc AT TIME ZONE 'America/New_York') AS start_new_york
        FROM databento_hourly_record
        WHERE start_utc >= %(start_utc)s AND start_utc < %(end_utc)s
    ), daily AS (
        SELECT symbol, exchange, currency, start_utc FROM databento_import_bar WHERE bar_period = '1-DAY'
        UNION
        SELECT symbol, exchange, currency, start_utc FROM databento_bar WHERE bar_period = '1-DAY'
    ), regular_hours AS (
        SELECT hourly.*, member.exchange, member.currency,
            EXISTS (
                SELECT FROM daily
                WHERE daily.symbol = hourly.symbol AND daily.exchange = member.exchange
                    AND daily.currency = member.currency
                    AND daily.start_utc = hourly.start_new_york::date::timestamp AT TIME ZONE 'UTC'
            ) AS has_daily_bar
        FROM hourly JOIN us_universe_member AS member ON member.symbol = hourly.symbol
            AND date_trunc('quarter', member.quarter_start_utc AT TIME ZONE 'UTC')
                = date_trunc('quarter', hourly.start_new_york)
        WHERE hourly.start_new_york::time BETWEEN '09:00' AND '15:00'
    )
"""

# A bar of a day without a Databento daily bar has no official open, so the import does not save it.
INSERT_HOURLY_BARS: LiteralString = (
    HOURLY_RECORD_IN_NEW_YORK
    + """
    INSERT INTO databento_import_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
    SELECT symbol, exchange, currency, '1-HOUR',
        CASE WHEN start_new_york::time = '09:00' THEN start_utc + interval '30 minutes' ELSE start_utc END,
        open, high, low, close, volume
    FROM regular_hours
    WHERE has_daily_bar
    ON CONFLICT (symbol, exchange, currency, bar_period, start_utc) DO UPDATE SET
        open = excluded.open, high = excluded.high, low = excluded.low,
        close = excluded.close, volume = excluded.volume
    """
)

SELECT_SYMBOLS_WITHOUT_DAILY_BAR: LiteralString = (
    HOURLY_RECORD_IN_NEW_YORK
    + """
    SELECT DISTINCT symbol FROM regular_hours WHERE NOT has_daily_bar ORDER BY symbol
    """
)

# After the stock split adjustment: the daily bar of this import, else the saved daily bar, has the same adjustment.
# The high and the low include the official open.
SET_OFFICIAL_OPEN: LiteralString = """
    UPDATE databento_import_bar AS hourly
    SET open = daily.open, high = greatest(hourly.high, daily.open), low = least(hourly.low, daily.open)
    FROM (
        SELECT DISTINCT ON (symbol, exchange, currency, start_utc) symbol, exchange, currency, start_utc, open
        FROM (
            SELECT symbol, exchange, currency, start_utc, open, 0 AS priority
            FROM databento_import_bar WHERE bar_period = '1-DAY'
            UNION ALL
            SELECT symbol, exchange, currency, start_utc, open, 1 AS priority
            FROM databento_bar WHERE bar_period = '1-DAY'
        ) AS any_daily
        ORDER BY symbol, exchange, currency, start_utc, priority
    ) AS daily
    WHERE hourly.bar_period = '1-HOUR'
        AND (hourly.start_utc AT TIME ZONE 'America/New_York')::time = '09:30'
        AND daily.symbol = hourly.symbol AND daily.exchange = hourly.exchange AND daily.currency = hourly.currency
        AND daily.start_utc = (hourly.start_utc AT TIME ZONE 'America/New_York')::date::timestamp AT TIME ZONE 'UTC'
"""

SELECT_HOURLY_QUARTERS: LiteralString = """
    SELECT DISTINCT symbol, exchange, currency, date_trunc('quarter', start_utc AT TIME ZONE 'America/New_York')::date
    FROM databento_import_bar
    WHERE bar_period = '1-HOUR'
    ORDER BY 1, 2, 3, 4
"""

# Section 8.8.1: the instruments of each quarter, with the old symbols that were in use in the quarter.
SELECT_PURCHASE_SYMBOLS: LiteralString = """
    WITH RECURSIVE member AS (
        SELECT quarter_start_utc, symbol FROM us_universe_member WHERE currency = 'USD'
    ), old_symbol AS (
        SELECT member.quarter_start_utc, link.old_symbol AS symbol, link.change_day
        FROM member JOIN databento_symbol_link AS link ON link.new_symbol = member.symbol
        UNION
        SELECT old_symbol.quarter_start_utc, link.old_symbol, link.change_day
        FROM old_symbol JOIN databento_symbol_link AS link ON link.new_symbol = old_symbol.symbol
    )
    SELECT quarter_start_utc, symbol FROM member
    UNION
    SELECT quarter_start_utc, symbol FROM old_symbol
    WHERE change_day::timestamp AT TIME ZONE 'UTC' > quarter_start_utc
    ORDER BY quarter_start_utc, symbol
"""


@dataclass(frozen=True)
class HourlyPurchase:
    """The hourly bars to buy for one quarter: `start` (included) to `end` (not included)."""

    start: date
    end: date
    symbols: list[str]


def add_quarter(day: date) -> date:
    month_index = day.month - 1 + QUARTER_MONTHS
    return date(day.year + month_index // 12, month_index % 12 + 1, 1)


def quarter_of(day: date) -> date:
    return date(day.year, (day.month - 1) // QUARTER_MONTHS * QUARTER_MONTHS + 1, 1)


def list_hourly_purchases(*, database_url: str, end_day: date) -> list[HourlyPurchase]:
    """The purchase list of the hourly bars: for each quarter of `us_universe_member`, its members. The last quarter
    ends at `end_day` (not included)."""
    with psycopg.connect(database_url) as connection:
        rows = connection.execute(SELECT_PURCHASE_SYMBOLS).fetchall()
    symbols_by_start: dict[date, list[str]] = {}
    for quarter_start_utc, symbol in rows:
        symbols_by_start.setdefault(quarter_start_utc.astimezone(UTC).date(), []).append(str(symbol))
    purchases: list[HourlyPurchase] = []
    for start, symbols in symbols_by_start.items():
        end = min(add_quarter(quarter_of(start)), end_day)
        if start < end:
            purchases.append(HourlyPurchase(start, end, symbols))
    return purchases


def to_utc_day(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def move_hourly_to_new_symbols(connection: psycopg.Connection) -> None:
    for old_symbol, new_symbol, change_day in connection.execute(SELECT_SYMBOL_LINKS).fetchall():
        connection.execute(
            MOVE_HOURLY_TO_NEW_SYMBOL, {"old_symbol": old_symbol, "new_symbol": new_symbol, "change_day": change_day}
        )


def insert_hourly_bars(connection: psycopg.Connection, time_range: TimeRange) -> list[str]:
    """Adds the regular-hours bars of the universe quarters to the bars of the import. Returns the symbols with hourly
    bars on a day without a Databento daily bar."""
    move_hourly_to_new_symbols(connection)
    parameters = {"start_utc": time_range.start_utc, "end_utc": time_range.end_utc}
    connection.execute(INSERT_HOURLY_BARS, parameters)
    return [str(row[0]) for row in connection.execute(SELECT_SYMBOLS_WITHOUT_DAILY_BAR, parameters).fetchall()]


def set_official_open(connection: psycopg.Connection) -> None:
    connection.execute(SET_OFFICIAL_OPEN)


def save_hourly_saved_ranges(connection: psycopg.Connection, time_range: TimeRange) -> None:
    """Records the bought time range of each instrument and quarter with hourly bars in the import."""
    parameters: list[dict[str, object]] = []
    for symbol, exchange, currency, quarter_start in connection.execute(SELECT_HOURLY_QUARTERS).fetchall():
        instrument = Instrument(symbol=str(symbol), exchange=str(exchange), currency=str(currency))
        start_utc = max(to_utc_day(quarter_start), time_range.start_utc)
        end_utc = min(to_utc_day(add_quarter(quarter_start)), time_range.end_utc)
        if start_utc < end_utc:
            key = create_key_parameters(instrument, BarPeriod.ONE_HOUR)
            parameters.append({**key, "start_utc": start_utc, "end_utc": end_utc})
    with connection.cursor() as cursor:
        cursor.executemany(JOIN_HOURLY_SAVED_RANGE_QUERY, parameters)
