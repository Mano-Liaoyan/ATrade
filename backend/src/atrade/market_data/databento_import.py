"""Databento import: saves the daily bars of the bought DBN files in databento_bar, with one saved range for each
instrument and bar period (docs/architecture/market_data.md section 8.8).

The records go to temporary tables first, and SQL makes the bars. Thus the import does not keep the millions of
records of a full purchase in memory. One transaction: a failed import saves nothing.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import LiteralString
from zoneinfo import ZoneInfo

import databento
import databento_dbn
import psycopg
from databento.common.symbology import InstrumentMap

from atrade.foundation.bar import BarPeriod, TimeRange, ceil_to_bar_start, floor_to_bar_start
from atrade.foundation.instrument import Instrument
from atrade.market_data import databento_import_sql
from atrade.market_data.bar_source import BarSource, saved_range_table
from atrade.market_data.bar_store import JOIN_SAVED_RANGE_TEMPLATE, create_key_parameters
from atrade.market_data.daily_bar_summary import update_daily_bar_summaries_blocking

NEW_YORK = ZoneInfo("America/New_York")
NANOSECONDS_PER_SECOND = 10**9
NASDAQ_DATASET = "XNAS.ITCH"
NYSE_DATASET = "XNYS.PILLAR"
SUMMARY_DATASET = "EQUS.SUMMARY"
DAILY_SCHEMA = "ohlcv-1d"
STATISTICS_SCHEMA = "statistics"
# The 4 files of the daily bars before 2024-07-01 (section 8.8.1). The import needs all 4 together, because the high,
# the low, and the volume come from both exchanges.
HISTORY_FILE_KINDS = frozenset(
    {
        (NASDAQ_DATASET, DAILY_SCHEMA),
        (NYSE_DATASET, DAILY_SCHEMA),
        (NASDAQ_DATASET, STATISTICS_SCHEMA),
        (NYSE_DATASET, STATISTICS_SCHEMA),
    }
)
SUMMARY_FILE_KIND = (SUMMARY_DATASET, DAILY_SCHEMA)
# The `statistics` stat_type of the official open and the official close. INSERT_HISTORY_BARS uses the same values.
OFFICIAL_PRICE_STAT_TYPES = frozenset({1, 11})
NEW_STATISTIC_ACTION = 1
JOIN_DATABENTO_SAVED_RANGE_QUERY = JOIN_SAVED_RANGE_TEMPLATE.format(
    saved_range_table=saved_range_table(BarSource.DATABENTO)
)


class DatabentoImportError(Exception):
    """The files cannot be imported. The message tells which file or which file kind is the problem."""


@dataclass(frozen=True)
class DatabentoImportReport:
    """`saved_bar_count` counts the bars that the import wrote, also bars that were saved before.

    `symbols_without_official_close`: symbols with daily bars before 2024-07-01 but no `stat_type` 11 in the
    `statistics` of XNAS.ITCH or XNYS.PILLAR. The import saves no bar for them (#141).
    `symbols_without_listing_exchange`: EQUS.SUMMARY symbols without an earlier Databento daily bar. The import does
    not know their listing exchange and saves no bar for them.
    """

    saved_bar_count: int
    symbols_without_official_close: list[str]
    symbols_without_listing_exchange: list[str]


def to_price(fixed_price: int) -> Decimal:
    """DBN prices are integers in units of 1e-9."""
    return Decimal(fixed_price).scaleb(-9)


def to_day(nanoseconds: int, time_zone: ZoneInfo | None = None) -> date:
    return datetime.fromtimestamp(nanoseconds // NANOSECONDS_PER_SECOND, tz=time_zone or UTC).date()


def to_time_range(start_ns: int, end_ns: int) -> TimeRange:
    return TimeRange(
        datetime.fromtimestamp(start_ns // NANOSECONDS_PER_SECOND, tz=UTC),
        datetime.fromtimestamp(end_ns // NANOSECONDS_PER_SECOND, tz=UTC),
    )


def create_daily_row(dataset: str, record: databento_dbn.OHLCVMsg, instrument_map: InstrumentMap) -> tuple[object, ...]:
    # An ohlcv-1d bar starts at 00:00 UTC of its trading day (section 8.4).
    trading_day = to_day(record.ts_event)
    symbol = instrument_map.resolve(record.instrument_id, trading_day)
    if symbol is None:
        return ()
    prices = (to_price(record.open), to_price(record.high), to_price(record.low), to_price(record.close))
    return (dataset, symbol, trading_day, *prices, record.volume)


def create_statistic_row(
    dataset: str, record: databento_dbn.StatMsg, instrument_map: InstrumentMap
) -> tuple[object, ...]:
    """Only the official open and close, and only new values: an update of a statistic is a new record."""
    stat_type = int(record.stat_type)
    if stat_type not in OFFICIAL_PRICE_STAT_TYPES or record.price == databento_dbn.UNDEF_PRICE:
        return ()
    if int(record.update_action) != NEW_STATISTIC_ACTION:
        return ()
    # The exchange sends the official prices during the trading day in New York.
    trading_day = to_day(record.ts_event, NEW_YORK)
    symbol = instrument_map.resolve(record.instrument_id, trading_day)
    if symbol is None:
        return ()
    return (dataset, symbol, trading_day, stat_type, to_price(record.price), record.ts_recv)


def copy_rows(
    connection: psycopg.Connection, copy_statement: LiteralString, rows: Iterable[tuple[object, ...]]
) -> None:
    with connection.cursor() as cursor, cursor.copy(copy_statement) as copy:
        for row in rows:
            if row:
                copy.write_row(row)


def copy_file_records(connection: psycopg.Connection, path: Path) -> tuple[tuple[str, str], TimeRange]:
    """Copies the records of one DBN file to the temporary tables. Returns the file kind and its time range."""
    store = databento.DBNStore.from_file(path)
    metadata = store.metadata
    file_kind = (metadata.dataset, str(metadata.schema))
    if file_kind not in HISTORY_FILE_KINDS and file_kind != SUMMARY_FILE_KIND:
        message = f"{path.name}: the import does not read {file_kind[0]} {file_kind[1]} files."
        raise DatabentoImportError(message)
    instrument_map = InstrumentMap()
    instrument_map.insert_metadata(metadata)
    if file_kind[1] == STATISTICS_SCHEMA:
        statistic_rows = (
            create_statistic_row(metadata.dataset, record, instrument_map)
            for record in store
            if isinstance(record, databento_dbn.StatMsg)
        )
        copy_rows(connection, databento_import_sql.COPY_STATISTICS, statistic_rows)
    else:
        daily_rows = (
            create_daily_row(metadata.dataset, record, instrument_map)
            for record in store
            if isinstance(record, databento_dbn.OHLCVMsg)
        )
        copy_rows(connection, databento_import_sql.COPY_DAILY_RECORDS, daily_rows)
    return file_kind, to_time_range(metadata.start, metadata.end)


def find_kind_range(time_ranges: list[TimeRange]) -> TimeRange:
    """A batch job can split one purchase into many files. The kind covers the earliest start to the latest end."""
    return TimeRange(
        min(time_range.start_utc for time_range in time_ranges), max(time_range.end_utc for time_range in time_ranges)
    )


def to_whole_days(time_range: TimeRange) -> TimeRange:
    return TimeRange(
        floor_to_bar_start(time_range.start_utc, BarPeriod.ONE_DAY),
        ceil_to_bar_start(time_range.end_utc, BarPeriod.ONE_DAY),
    )


def find_history_range(kind_ranges: dict[tuple[str, str], TimeRange]) -> TimeRange | None:
    """The time range that all 4 history files cover, or None without history files."""
    history_kinds = HISTORY_FILE_KINDS & kind_ranges.keys()
    if not history_kinds:
        return None
    missing_kinds = sorted(HISTORY_FILE_KINDS - history_kinds)
    if missing_kinds:
        names = ", ".join(f"{dataset} {schema}" for dataset, schema in missing_kinds)
        message = f"The daily bars before 2024-07-01 need all 4 history files. Missing: {names}."
        raise DatabentoImportError(message)
    ranges = [kind_ranges[kind] for kind in HISTORY_FILE_KINDS]
    start_utc = max(time_range.start_utc for time_range in ranges)
    end_utc = min(time_range.end_utc for time_range in ranges)
    return to_whole_days(TimeRange(start_utc, end_utc))


def read_symbols(connection: psycopg.Connection, query: LiteralString, time_range: TimeRange) -> list[str]:
    rows = connection.execute(query, {"start_utc": time_range.start_utc, "end_utc": time_range.end_utc}).fetchall()
    return [str(row[0]) for row in rows]


def save_bars(connection: psycopg.Connection, query: LiteralString, time_range: TimeRange) -> int:
    cursor = connection.execute(query, {"start_utc": time_range.start_utc, "end_utc": time_range.end_utc})
    return cursor.rowcount


def save_saved_ranges(connection: psycopg.Connection, time_range: TimeRange) -> list[Instrument]:
    """Records the bought time range for each instrument with a daily bar in it. A day without a bar in the range is
    a day without trading, so the bars route does not ask IBKR for it."""
    rows = connection.execute(
        databento_import_sql.SELECT_INSTRUMENTS,
        {"start_utc": time_range.start_utc, "end_utc": time_range.end_utc},
    ).fetchall()
    instruments = [Instrument(symbol=str(row[0]), exchange=str(row[1]), currency=str(row[2])) for row in rows]
    with connection.cursor() as cursor:
        cursor.executemany(
            JOIN_DATABENTO_SAVED_RANGE_QUERY,
            [
                {
                    **create_key_parameters(instrument, BarPeriod.ONE_DAY),
                    "start_utc": time_range.start_utc,
                    "end_utc": time_range.end_utc,
                }
                for instrument in instruments
            ],
        )
    return instruments


def read_file_kinds(connection: psycopg.Connection, file_paths: list[Path]) -> dict[tuple[str, str], TimeRange]:
    ranges_by_kind: dict[tuple[str, str], list[TimeRange]] = {}
    for path in file_paths:
        file_kind, time_range = copy_file_records(connection, path)
        ranges_by_kind.setdefault(file_kind, []).append(time_range)
    return {file_kind: find_kind_range(time_ranges) for file_kind, time_ranges in ranges_by_kind.items()}


def import_databento_files(*, database_url: str, file_paths: list[Path]) -> DatabentoImportReport:
    """Imports the DBN files of the daily bar purchase (section 8.8.1). A second import of the same files adds no
    row: a saved bar gets the same values, and the saved ranges join. The daily bar summary of each imported instrument
    changes in the same transaction."""
    with psycopg.connect(database_url) as connection, connection.transaction():
        connection.execute(databento_import_sql.CREATE_TEMPORARY_TABLES)
        kind_ranges = read_file_kinds(connection, file_paths)
        saved_bar_count = 0
        symbols_without_official_close: list[str] = []
        symbols_without_listing_exchange: list[str] = []
        saved_instruments: list[Instrument] = []
        history_range = find_history_range(kind_ranges)
        if history_range is not None:
            saved_bar_count += save_bars(connection, databento_import_sql.INSERT_HISTORY_BARS, history_range)
            symbols_without_official_close = read_symbols(
                connection, databento_import_sql.SELECT_SYMBOLS_WITHOUT_OFFICIAL_CLOSE, history_range
            )
            saved_instruments += save_saved_ranges(connection, history_range)
        if SUMMARY_FILE_KIND in kind_ranges:
            summary_range = to_whole_days(kind_ranges[SUMMARY_FILE_KIND])
            saved_bar_count += save_bars(connection, databento_import_sql.INSERT_SUMMARY_BARS, summary_range)
            symbols_without_listing_exchange = read_symbols(
                connection, databento_import_sql.SELECT_SYMBOLS_WITHOUT_LISTING_EXCHANGE, summary_range
            )
            saved_instruments += save_saved_ranges(connection, summary_range)
        update_daily_bar_summaries_blocking(connection, saved_instruments)
    return DatabentoImportReport(
        saved_bar_count=saved_bar_count,
        symbols_without_official_close=symbols_without_official_close,
        symbols_without_listing_exchange=symbols_without_listing_exchange,
    )
