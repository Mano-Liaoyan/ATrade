"""Databento import: the daily bars of the bought DBN files go to databento_bar with their saved ranges.

Real PostgreSQL and hand-made DBN files of the Databento fake (docs/architecture/market_data.md section 8.8).
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import LiteralString

import psycopg
import pytest

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import (
    BarRequest,
    BarSource,
    DatabentoImportError,
    import_databento_files,
    read_saved_bars,
)
from tests.fakes.databento import (
    CLOSE_PRICE,
    DAILY_SCHEMA,
    OPENING_PRICE,
    STATISTICS_SCHEMA,
    DailyRecord,
    DbnFile,
    StatisticRecord,
    write_dbn_files,
)

APPLE_NASDAQ = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
IBM_NYSE = Instrument(symbol="IBM", exchange="NYSE", currency="USD")
PURCHASE_START = date(2018, 5, 1)
EQUS_START = date(2024, 7, 1)
PURCHASE_END = date(2026, 10, 28)
# Only Databento in the source order reads: IBKR has no saved range in these tests.
SOURCE_ORDER = [BarSource.IBKR, BarSource.DATABENTO]
TRADING_DAY = date(2020, 1, 2)


def utc_day(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def daily_record(symbol: str, day: date, prices: str, volume: int) -> DailyRecord:
    """`prices` is "open high low close"."""
    open_price, high, low, close = (Decimal(price) for price in prices.split())
    return DailyRecord(symbol=symbol, trading_day=day, open=open_price, high=high, low=low, close=close, volume=volume)


def official_prices(symbol: str, day: date, open_price: str, close: str) -> list[StatisticRecord]:
    return [
        StatisticRecord(symbol=symbol, trading_day=day, stat_type=OPENING_PRICE, price=Decimal(open_price)),
        StatisticRecord(symbol=symbol, trading_day=day, stat_type=CLOSE_PRICE, price=Decimal(close)),
    ]


def create_history_files(
    nasdaq_daily: list[DailyRecord],
    nyse_daily: list[DailyRecord],
    nasdaq_statistics: list[StatisticRecord],
    nyse_statistics: list[StatisticRecord],
) -> list[DbnFile]:
    """The 4 files of the daily bars before 2024-07-01 (section 8.8.1)."""
    return [
        DbnFile("XNAS.ITCH", DAILY_SCHEMA, PURCHASE_START, EQUS_START, daily_records=nasdaq_daily),
        DbnFile("XNYS.PILLAR", DAILY_SCHEMA, PURCHASE_START, EQUS_START, daily_records=nyse_daily),
        DbnFile("XNAS.ITCH", STATISTICS_SCHEMA, PURCHASE_START, EQUS_START, statistic_records=nasdaq_statistics),
        DbnFile("XNYS.PILLAR", STATISTICS_SCHEMA, PURCHASE_START, EQUS_START, statistic_records=nyse_statistics),
    ]


async def read_databento_bars(database_url: str, instrument: Instrument, start: date, end: date) -> list[Bar]:
    bar_request = BarRequest(instrument, BarPeriod.ONE_DAY, TimeRange(utc_day(start), utc_day(end)))
    saved_bars = await read_saved_bars(database_url=database_url, bar_request=bar_request, source_order=SOURCE_ORDER)
    return saved_bars.bars


@pytest.fixture
def history_files() -> list[DbnFile]:
    """AAPL is listed on NASDAQ: only XNAS.ITCH has its official open and close. Both exchanges trade it."""
    return create_history_files(
        nasdaq_daily=[daily_record("AAPL", TRADING_DAY, "74.06 75.15 73.80 75.20", 1000)],
        nyse_daily=[daily_record("AAPL", TRADING_DAY, "74.10 75.30 73.70 75.25", 300)],
        nasdaq_statistics=official_prices("AAPL", TRADING_DAY, "74.06", "75.09"),
        nyse_statistics=[],
    )


@pytest.mark.anyio
async def test_a_bar_before_2024_07_01_has_the_official_open_and_close_of_the_listing_exchange(
    database_url: str, tmp_path: Path, history_files: list[DbnFile]
) -> None:
    import_databento_files(database_url=database_url, file_paths=write_dbn_files(tmp_path, history_files))

    bars = await read_databento_bars(database_url, APPLE_NASDAQ, TRADING_DAY, date(2020, 1, 3))

    # The close is the official close 75.09, not the ohlcv-1d close 75.20 with the trades after the close.
    assert [(bar.open, bar.close) for bar in bars] == [(Decimal("74.06"), Decimal("75.09"))]


@pytest.mark.anyio
async def test_the_high_and_the_low_come_from_both_exchanges_and_the_volume_is_their_sum(
    database_url: str, tmp_path: Path
) -> None:
    """IBM is listed on NYSE: only XNYS.PILLAR has its official prices. XNAS.ITCH has the higher high."""
    files = create_history_files(
        nasdaq_daily=[daily_record("IBM", TRADING_DAY, "130.00 136.50 129.80 135.10", 200)],
        nyse_daily=[daily_record("IBM", TRADING_DAY, "130.10 135.90 129.50 135.30", 4000)],
        nasdaq_statistics=[],
        nyse_statistics=official_prices("IBM", TRADING_DAY, "130.20", "135.42"),
    )
    import_databento_files(database_url=database_url, file_paths=write_dbn_files(tmp_path, files))

    bars = await read_databento_bars(database_url, IBM_NYSE, TRADING_DAY, date(2020, 1, 3))

    assert bars == [
        Bar(
            start_utc=datetime(2020, 1, 2, tzinfo=UTC),
            open=Decimal("130.2"),
            high=Decimal("136.5"),
            low=Decimal("129.5"),
            close=Decimal("135.42"),
            volume=Decimal(4200),
        )
    ]


@pytest.mark.anyio
async def test_a_bar_from_2024_07_01_is_the_equs_summary_bar_on_the_listing_exchange_of_the_history(
    database_url: str, tmp_path: Path, history_files: list[DbnFile]
) -> None:
    summary_day = date(2025, 3, 3)
    summary_file = DbnFile(
        "EQUS.SUMMARY",
        DAILY_SCHEMA,
        EQUS_START,
        PURCHASE_END,
        daily_records=[daily_record("AAPL", summary_day, "241.79 244.03 236.11 238.03", 47184000)],
    )
    import_databento_files(
        database_url=database_url, file_paths=write_dbn_files(tmp_path, [*history_files, summary_file])
    )

    bars = await read_databento_bars(database_url, APPLE_NASDAQ, summary_day, date(2025, 3, 4))

    assert bars == [
        Bar(
            start_utc=datetime(2025, 3, 3, tzinfo=UTC),
            open=Decimal("241.79"),
            high=Decimal("244.03"),
            low=Decimal("236.11"),
            close=Decimal("238.03"),
            volume=Decimal(47184000),
        )
    ]


def read_table(database_url: str, query: LiteralString) -> list[tuple[object, ...]]:
    with psycopg.connect(database_url) as connection:
        return connection.execute(query).fetchall()


def test_the_import_records_the_bought_time_range_for_each_instrument_and_bar_period(
    database_url: str, tmp_path: Path, history_files: list[DbnFile]
) -> None:
    summary_file = DbnFile(
        "EQUS.SUMMARY",
        DAILY_SCHEMA,
        EQUS_START,
        PURCHASE_END,
        daily_records=[daily_record("AAPL", date(2025, 3, 3), "241.79 244.03 236.11 238.03", 47184000)],
    )
    import_databento_files(
        database_url=database_url, file_paths=write_dbn_files(tmp_path, [*history_files, summary_file])
    )

    saved_ranges = read_table(
        database_url,
        "SELECT symbol, exchange, currency, bar_period, start_utc, end_utc FROM databento_bar_saved_range",
    )

    # The two bought ranges touch, so they join.
    assert saved_ranges == [("AAPL", "NASDAQ", "USD", "1-DAY", utc_day(PURCHASE_START), utc_day(PURCHASE_END))]


def test_a_second_import_of_the_same_files_adds_no_row(
    database_url: str, tmp_path: Path, history_files: list[DbnFile]
) -> None:
    file_paths = write_dbn_files(tmp_path, history_files)
    import_databento_files(database_url=database_url, file_paths=file_paths)

    import_databento_files(database_url=database_url, file_paths=file_paths)

    counts = read_table(
        database_url,
        "SELECT (SELECT count(*) FROM databento_bar), (SELECT count(*) FROM databento_bar_saved_range)",
    )
    assert counts == [(1, 1)]


def test_the_report_names_the_symbols_without_an_official_close_and_saves_no_bar_for_them(
    database_url: str, tmp_path: Path
) -> None:
    """An NYSE American symbol: the purchase has no statistics of its exchange (#141)."""
    files = create_history_files(
        nasdaq_daily=[daily_record("AMEX1", TRADING_DAY, "5.00 5.20 4.90 5.10", 100)],
        nyse_daily=[daily_record("AMEX1", TRADING_DAY, "5.00 5.30 4.80 5.05", 50)],
        nasdaq_statistics=[],
        nyse_statistics=[],
    )

    report = import_databento_files(database_url=database_url, file_paths=write_dbn_files(tmp_path, files))

    assert report.symbols_without_official_close == ["AMEX1"]
    assert read_table(database_url, "SELECT count(*) FROM databento_bar") == [(0,)]


def test_the_report_names_the_equs_summary_symbols_without_a_listing_exchange(
    database_url: str, tmp_path: Path
) -> None:
    """A symbol listed after 2024-07-01 has no history bar, so the import does not know its listing exchange."""
    summary_file = DbnFile(
        "EQUS.SUMMARY",
        DAILY_SCHEMA,
        EQUS_START,
        PURCHASE_END,
        daily_records=[daily_record("NEW1", date(2025, 3, 3), "10.00 10.50 9.90 10.20", 1000)],
    )

    report = import_databento_files(database_url=database_url, file_paths=write_dbn_files(tmp_path, [summary_file]))

    assert report.symbols_without_listing_exchange == ["NEW1"]
    assert read_table(database_url, "SELECT count(*) FROM databento_bar") == [(0,)]


def test_the_import_refuses_history_files_without_all_4_file_kinds(
    database_url: str, tmp_path: Path, history_files: list[DbnFile]
) -> None:
    with pytest.raises(DatabentoImportError, match=r"Missing: XNYS\.PILLAR statistics"):
        import_databento_files(database_url=database_url, file_paths=write_dbn_files(tmp_path, history_files[:3]))
