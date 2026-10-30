"""Databento import of the XNAS.ITCH hourly bars: the 7 regular-hours bars of the universe quarters.

Real PostgreSQL, hand-made DBN files of the Databento fake, and the IBKR fake
(docs/architecture/market_data.md sections 8.8.2 and 8.14).
"""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import psycopg
import pytest

from atrade.app.web import create_web_app
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from atrade.market_data import (
    BarRequest,
    BarSource,
    DatabentoImportReport,
    import_databento_files_with_ibkr,
    read_saved_bars,
)
from tests.fakes.clock import FixedClock
from tests.fakes.databento import (
    CLOSE_PRICE,
    DAILY_SCHEMA,
    HOURLY_SCHEMA,
    OPENING_PRICE,
    STATISTICS_SCHEMA,
    DailyRecord,
    DbnFile,
    HourlyRecord,
    StatisticRecord,
    write_dbn_files,
)
from tests.fakes.ibkr import FakeGatewayConnection

NEW_YORK = ZoneInfo("America/New_York")
PURCHASE_START = date(2018, 5, 1)
PURCHASE_END = date(2024, 7, 1)
HOURLY_START = date(2020, 1, 1)
HOURLY_END = date(2020, 7, 1)
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
# Thursday. New York is UTC-5 on this day.
TRADING_DAY = date(2020, 1, 9)
FIRST_QUARTER_START = date(2020, 1, 2)
SECOND_QUARTER_START = date(2020, 4, 1)
OFFICIAL_OPEN = Decimal("74.06")
OFFICIAL_CLOSE = Decimal("75.09")


def utc_day(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def new_york(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=NEW_YORK)


def daily_files(symbol: str, days: list[date], prices: list[tuple[str, str, int]]) -> list[DbnFile]:
    """The 4 history files of a NASDAQ symbol. `prices` holds (official open, official close, volume) for each day."""
    daily_records: list[DailyRecord] = []
    statistic_records: list[StatisticRecord] = []
    for day, (open_price, close, volume) in zip(days, prices, strict=True):
        high = max(Decimal(open_price), Decimal(close))
        low = min(Decimal(open_price), Decimal(close))
        daily_records.append(DailyRecord(symbol, day, Decimal(open_price), high, low, Decimal(close), volume))
        statistic_records += [
            StatisticRecord(symbol, day, OPENING_PRICE, Decimal(open_price)),
            StatisticRecord(symbol, day, CLOSE_PRICE, Decimal(close)),
        ]
    return [
        DbnFile("XNAS.ITCH", DAILY_SCHEMA, PURCHASE_START, PURCHASE_END, daily_records=daily_records),
        DbnFile("XNYS.PILLAR", DAILY_SCHEMA, PURCHASE_START, PURCHASE_END),
        DbnFile("XNAS.ITCH", STATISTICS_SCHEMA, PURCHASE_START, PURCHASE_END, statistic_records=statistic_records),
        DbnFile("XNYS.PILLAR", STATISTICS_SCHEMA, PURCHASE_START, PURCHASE_END),
    ]


def hourly_records(symbol: str, day: date, hours: range, price: str = "75", volume: int = 1000) -> list[HourlyRecord]:
    return [
        HourlyRecord(
            symbol, new_york(day, hour), Decimal(price), Decimal(price), Decimal(price), Decimal(price), volume
        )
        for hour in hours
    ]


def hourly_file(records: list[HourlyRecord]) -> DbnFile:
    return DbnFile("XNAS.ITCH", HOURLY_SCHEMA, HOURLY_START, HOURLY_END, hourly_records=records)


def insert_member(database_url: str, quarter_start: date, rank: int, instrument: Instrument) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO us_universe_member (
                quarter_start_utc, rank, symbol, exchange, currency, average_trading_value, last_ranking_day_utc
            )
            VALUES (%(quarter_start_utc)s, %(rank)s, %(symbol)s, %(exchange)s, %(currency)s, 1000000,
                %(quarter_start_utc)s)
            """,
            {
                "quarter_start_utc": utc_day(quarter_start),
                "rank": rank,
                "symbol": instrument.symbol,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
            },
        )


@pytest.fixture
async def gateway() -> FakeGatewayConnection:
    connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    await connection.connect()
    return connection


async def run_import(
    database_url: str, directory: Path, gateway: FakeGatewayConnection, files: list[DbnFile]
) -> DatabentoImportReport:
    return await import_databento_files_with_ibkr(
        database_url=database_url, file_paths=write_dbn_files(directory, files), gateway=gateway
    )


async def import_apple_day(database_url: str, tmp_path: Path, gateway: FakeGatewayConnection) -> None:
    """The purchase order of section 8.8.1: the daily bars first, then the hourly bars of the universe quarters."""
    insert_member(database_url, FIRST_QUARTER_START, 1, APPLE)
    await run_import(
        database_url,
        tmp_path / "daily",
        gateway,
        daily_files("AAPL", [TRADING_DAY], [(str(OFFICIAL_OPEN), str(OFFICIAL_CLOSE), 30000)]),
    )
    records = hourly_records("AAPL", TRADING_DAY, range(4, 20))
    records[5] = HourlyRecord(
        "AAPL", new_york(TRADING_DAY, 9), Decimal("73.50"), Decimal("75.80"), Decimal("72.90"), Decimal("74.40"), 9000
    )
    await run_import(database_url, tmp_path / "hourly", gateway, [hourly_file(records)])


async def read_hourly_bars(database_url: str, instrument: Instrument, day: date) -> list[Bar]:
    time_range = TimeRange(utc_day(day), utc_day(day + timedelta(days=1)))
    saved_bars = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(instrument, BarPeriod.ONE_HOUR, time_range),
        source_order=[BarSource.DATABENTO, BarSource.IBKR],
    )
    return saved_bars.bars


@pytest.mark.anyio
async def test_the_import_keeps_the_7_regular_hours_bars_and_starts_the_first_at_9_30_et(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    await import_apple_day(database_url, tmp_path, gateway)

    bars = await read_hourly_bars(database_url, APPLE, TRADING_DAY)
    assert [bar.start_utc for bar in bars] == [
        datetime(2020, 1, 9, 14, 30, tzinfo=UTC),
        *(datetime(2020, 1, 9, hour, tzinfo=UTC) for hour in range(15, 21)),
    ]


@pytest.mark.anyio
async def test_the_9_30_et_bar_has_the_official_open_and_the_high_and_low_from_9_00_et(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    await import_apple_day(database_url, tmp_path, gateway)

    first_bar = (await read_hourly_bars(database_url, APPLE, TRADING_DAY))[0]
    assert (first_bar.open, first_bar.high, first_bar.low, first_bar.close, first_bar.volume) == (
        OFFICIAL_OPEN,
        Decimal("75.80"),
        Decimal("72.90"),
        Decimal("74.40"),
        Decimal(9000),
    )


@pytest.mark.anyio
async def test_a_summer_day_starts_the_7_bars_at_9_30_et_in_utc(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """New York is UTC-4 on 2020-06-11 (daylight saving time), so 9:30 ET is 13:30 UTC."""
    summer_day = date(2020, 6, 11)
    insert_member(database_url, SECOND_QUARTER_START, 1, APPLE)
    files = [
        *daily_files("AAPL", [summer_day], [("74", "75", 30000)]),
        hourly_file(hourly_records("AAPL", summer_day, range(4, 20))),
    ]

    await run_import(database_url, tmp_path, gateway, files)

    bars = await read_hourly_bars(database_url, APPLE, summer_day)
    assert [bar.start_utc for bar in bars] == [
        datetime(2020, 6, 11, 13, 30, tzinfo=UTC),
        *(datetime(2020, 6, 11, hour, tzinfo=UTC) for hour in range(14, 20)),
    ]


@pytest.mark.anyio
async def test_two_files_with_the_same_hourly_bars_save_each_bar_one_time(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """For example, a current-quarter purchase that the user buys again later from the quarter start."""
    insert_member(database_url, FIRST_QUARTER_START, 1, APPLE)
    records = hourly_records("AAPL", TRADING_DAY, range(9, 16))
    later_purchase = DbnFile("XNAS.ITCH", HOURLY_SCHEMA, TRADING_DAY, HOURLY_END, hourly_records=records)
    files = [*daily_files("AAPL", [TRADING_DAY], [("74", "75", 30000)]), hourly_file(records), later_purchase]

    await run_import(database_url, tmp_path, gateway, files)

    assert len(await read_hourly_bars(database_url, APPLE, TRADING_DAY)) == 7


@pytest.mark.anyio
async def test_the_import_keeps_only_the_quarters_in_which_the_instrument_is_in_the_universe(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """AAPL is a member in the first quarter of 2020 only. ZZZZ is never a member."""
    later_day = date(2020, 4, 9)
    microsoft = Instrument(symbol="MSFT", exchange="NASDAQ", currency="USD")
    insert_member(database_url, FIRST_QUARTER_START, 1, APPLE)
    insert_member(database_url, SECOND_QUARTER_START, 1, microsoft)
    daily_prices = [("74", "75", 30000), ("60", "61", 30000)]
    files = [
        *daily_files("AAPL", [TRADING_DAY, later_day], daily_prices),
        hourly_file(
            [
                *hourly_records("AAPL", TRADING_DAY, range(9, 16)),
                *hourly_records("AAPL", later_day, range(9, 16)),
                *hourly_records("ZZZZ", TRADING_DAY, range(9, 16)),
            ]
        ),
    ]

    await run_import(database_url, tmp_path, gateway, files)

    assert len(await read_hourly_bars(database_url, APPLE, TRADING_DAY)) == 7
    assert await read_hourly_bars(database_url, APPLE, later_day) == []
    zzzz = Instrument(symbol="ZZZZ", exchange="NASDAQ", currency="USD")
    assert await read_hourly_bars(database_url, zzzz, TRADING_DAY) == []


@pytest.mark.anyio
async def test_the_hourly_bars_before_the_ex_date_are_adjusted_by_the_split_ratio(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """A 2-for-1 split on 2020-01-08 that the IBKR closes show."""
    days = [date(2020, 1, 7), date(2020, 1, 8), TRADING_DAY]
    insert_member(database_url, FIRST_QUARTER_START, 1, APPLE)
    gateway.historical_bars[APPLE] = [
        Bar(utc_day(day), Decimal(close), Decimal(close), Decimal(close), Decimal(close), Decimal(1000))
        for day, close in zip(days, ["101", "102", "103"], strict=True)
    ]
    daily_prices = [("200", "202", 1000), ("102", "102", 2000), ("103", "103", 2000)]
    files = [
        *daily_files("AAPL", days, daily_prices),
        hourly_file([*hourly_records("AAPL", days[0], range(9, 16), "201", 100)]),
    ]

    await run_import(database_url, tmp_path, gateway, files)

    bars = await read_hourly_bars(database_url, APPLE, days[0])
    assert [(bar.open, bar.close, bar.volume) for bar in bars] == [
        (Decimal(100), Decimal("100.5"), Decimal(200)),
        *([(Decimal("100.5"), Decimal("100.5"), Decimal(200))] * 6),
    ]


@pytest.fixture
async def client(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, gateway: FakeGatewayConnection
) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


@pytest.mark.anyio
async def test_the_bars_route_reads_the_hourly_bars_from_9_30_et_without_a_missing_part(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection, client: httpx.AsyncClient
) -> None:
    await import_apple_day(database_url, tmp_path, gateway)
    gateway.historical_bar_requests.clear()

    response = await client.get(
        "/api/market-data/bars",
        params={
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "currency": "USD",
            "bar_period": "1-HOUR",
            "start_utc": datetime(2020, 1, 9, 14, 30, tzinfo=UTC).isoformat(),
            "end_utc": datetime(2020, 1, 9, 21, tzinfo=UTC).isoformat(),
        },
    )

    assert response.status_code == 200
    times = [bar["time"] for bar in response.json()["bars"]]
    assert times == [int(datetime(2020, 1, 9, 14, 30, tzinfo=UTC).timestamp())] + [
        int(datetime(2020, 1, 9, hour, tzinfo=UTC).timestamp()) for hour in range(15, 21)
    ]
    assert gateway.historical_bar_requests == []
