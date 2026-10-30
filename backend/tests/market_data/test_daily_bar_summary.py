"""The daily bars of many instruments in one read, and the daily bar summary that each save of daily bars updates.

Real PostgreSQL, the IBKR fake, and hand-made DBN files (docs/architecture/market_data.md section 8.11).
"""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
from psycopg import sql

from atrade.app.web import create_web_app
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from atrade.indicator import AverageTradingValue
from atrade.market_data import (
    BarRequest,
    DailyBarSummary,
    import_databento_files,
    read_daily_bar_summaries,
    read_last_daily_bars,
    save_received_bars,
    save_received_bars_blocking,
)
from tests.fakes.clock import FixedClock
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
from tests.fakes.ibkr import FakeGatewayConnection

APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
MICROSOFT = Instrument(symbol="MSFT", exchange="NASDAQ", currency="USD")
TENCENT = Instrument(symbol="700", exchange="SEHK", currency="HKD")
IBKR_CLOSE = Decimal(100)
DATABENTO_CLOSE = Decimal(200)


def day(number: int) -> datetime:
    return datetime(2025, 12, number, tzinfo=UTC)


def save_source_bars(  # noqa: PLR0913, PLR0917 readability-exception: a test helper with one value for each column group.
    database_url: str,
    bar_source: str,
    instrument: Instrument,
    saved_range: TimeRange,
    bar_days: list[int],
    close: Decimal,
) -> None:
    """Saves daily bars and one saved range in the tables of one bar source, like its writer does."""
    key = {
        "symbol": instrument.symbol,
        "exchange": instrument.exchange,
        "currency": instrument.currency,
        "bar_period": "1-DAY",
    }
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            sql.SQL("""
                INSERT INTO {} (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
                VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, %(start_utc)s, %(close)s,
                    %(close)s, %(close)s, %(close)s, 1000)
            """).format(sql.Identifier(f"{bar_source}_bar")),
            [{**key, "start_utc": day(number), "close": close} for number in bar_days],
        )
        cursor.execute(
            sql.SQL("""
                INSERT INTO {} (symbol, exchange, currency, bar_period, start_utc, end_utc)
                VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, %(start_utc)s, %(end_utc)s)
            """).format(sql.Identifier(f"{bar_source}_bar_saved_range")),
            {**key, "start_utc": saved_range.start_utc, "end_utc": saved_range.end_utc},
        )


def save_apple_and_microsoft_bars(database_url: str) -> None:
    # IBKR saved APPLE 5..8 December. 6 December is a holiday: IBKR has no bar. Databento saved 5..10 December.
    save_source_bars(database_url, "ibkr", APPLE, TimeRange(day(5), day(8)), [5, 7], IBKR_CLOSE)
    save_source_bars(database_url, "databento", APPLE, TimeRange(day(5), day(10)), [5, 6, 7, 8, 9], DATABENTO_CLOSE)
    save_source_bars(database_url, "databento", MICROSOFT, TimeRange(day(1), day(10)), [1, 2, 3, 4], DATABENTO_CLOSE)


def set_source_order(database_url: str, bar_sources: list[str]) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO source_order (id, bar_sources, changed_at_utc) VALUES (true, %(bar_sources)s, now())
            ON CONFLICT (id) DO UPDATE SET bar_sources = excluded.bar_sources
            """,
            {"bar_sources": bar_sources},
        )


def closes_by_day(bars: list[Bar]) -> list[tuple[int, Decimal]]:
    return [(bar.start_utc.day, bar.close) for bar in bars]


@pytest.fixture
def query_count(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Counts the SQL statements that async cursors send."""
    count = [0]
    original_execute = psycopg.AsyncCursor.execute

    async def count_execute(self: psycopg.AsyncCursor[Any], *args: Any, **kwargs: Any) -> psycopg.AsyncCursor[Any]:
        count[0] += 1
        return await original_execute(self, *args, **kwargs)

    monkeypatch.setattr(psycopg.AsyncCursor, "execute", count_execute)
    return count


@pytest.mark.anyio
async def test_reads_the_last_daily_bars_of_many_instruments_in_one_query_through_the_source_order(
    database_url: str, query_count: list[int]
) -> None:
    save_apple_and_microsoft_bars(database_url)

    bars = await read_last_daily_bars(
        database_url=database_url, instruments=[APPLE, MICROSOFT, TENCENT], before_utc=day(9), bar_count=3
    )

    assert query_count == [1]
    # IBKR gives 5..7 December, also the holiday 6 December without a bar. Databento gives 8 December.
    assert {instrument: closes_by_day(instrument_bars) for instrument, instrument_bars in bars.items()} == {
        APPLE: [(5, IBKR_CLOSE), (7, IBKR_CLOSE), (8, DATABENTO_CLOSE)],
        MICROSOFT: [(2, DATABENTO_CLOSE), (3, DATABENTO_CLOSE), (4, DATABENTO_CLOSE)],
        TENCENT: [],
    }


@pytest.mark.anyio
async def test_the_read_of_many_instruments_follows_a_changed_source_order(database_url: str) -> None:
    save_apple_and_microsoft_bars(database_url)
    set_source_order(database_url, ["databento", "ibkr"])

    bars = await read_last_daily_bars(database_url=database_url, instruments=[APPLE], before_utc=day(9), bar_count=3)

    assert closes_by_day(bars[APPLE]) == [(6, DATABENTO_CLOSE), (7, DATABENTO_CLOSE), (8, DATABENTO_CLOSE)]


def create_varied_bars(count: int) -> list[Bar]:
    return [
        Bar(
            start_utc=day(1) + timedelta(days=index),
            open=Decimal(50),
            high=Decimal(60),
            low=Decimal(40),
            close=Decimal(50) + Decimal(index) / 4,
            volume=Decimal(1000 + 37 * index),
        )
        for index in range(count)
    ]


def december_request(instrument: Instrument) -> BarRequest:
    return BarRequest(instrument=instrument, bar_period=BarPeriod.ONE_DAY, time_range=TimeRange(day(1), day(31)))


@pytest.mark.anyio
async def test_the_average_trading_value_20_is_the_value_of_the_indicator_class(database_url: str) -> None:
    bars = create_varied_bars(25)
    indicator = AverageTradingValue(20)
    for bar in bars:
        indicator.update(bar)

    await save_received_bars(database_url=database_url, bar_request=december_request(APPLE), bars=bars)

    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE])
    assert [summary.average_trading_value_20 for summary in summaries] == [indicator.value]


@pytest.mark.anyio
async def test_save_received_bars_updates_the_summary_of_the_instrument(database_url: str) -> None:
    # Close 10 and volume 100 on each day: the average trading value is 1000.
    bars = [
        Bar(day(number), Decimal(10), Decimal(10), Decimal(10), Decimal(10), Decimal(100)) for number in range(1, 21)
    ]
    bars[-1] = Bar(day(20), Decimal(10), Decimal(30), Decimal(10), Decimal(30), Decimal(100))

    await save_received_bars(database_url=database_url, bar_request=december_request(APPLE), bars=bars)

    # 19 bars of 1000 and 1 bar of 3000.
    assert await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE]) == [
        DailyBarSummary(
            instrument=APPLE, last_day_start_utc=day(20), last_close=Decimal(30), average_trading_value_20=1100.0
        )
    ]


@pytest.mark.anyio
async def test_a_summary_with_fewer_than_20_daily_bars_has_no_average_trading_value(database_url: str) -> None:
    save_received_bars_blocking(
        database_url=database_url, bar_request=december_request(APPLE), bars=create_varied_bars(19)
    )

    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE, MICROSOFT])

    assert [(summary.instrument, summary.average_trading_value_20) for summary in summaries] == [(APPLE, None)]


@pytest.mark.anyio
async def test_a_save_of_hourly_bars_does_not_change_the_summary(database_url: str) -> None:
    bar_request = BarRequest(instrument=APPLE, bar_period=BarPeriod.ONE_HOUR, time_range=TimeRange(day(1), day(2)))

    await save_received_bars(database_url=database_url, bar_request=bar_request, bars=create_varied_bars(1))

    assert await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE]) == []


@pytest.fixture
async def client(database_url: str, clock: FixedClock, frontend_build_dir: Path) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    gateway_connection.connected = True
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


@pytest.mark.anyio
async def test_the_bars_route_updates_the_summary_after_it_saves_daily_bars(
    client: httpx.AsyncClient, database_url: str
) -> None:
    response = await client.get(
        "/api/market-data/bars",
        params={
            "symbol": TENCENT.symbol,
            "exchange": TENCENT.exchange,
            "currency": TENCENT.currency,
            "bar_period": "1-DAY",
            "start_utc": day(1).isoformat(),
            "end_utc": day(3).isoformat(),
        },
    )

    assert response.status_code == 200
    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[TENCENT])
    # The fake bar of 2025-12-02 is day 20424 from the epoch: open 100 + 20424 % 50 = 124, close 124.5.
    assert [(summary.last_day_start_utc, summary.last_close) for summary in summaries] == [(day(2), Decimal("124.5"))]


async def read_last_day_and_close(database_url: str) -> list[tuple[datetime, Decimal]]:
    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE])
    return [(summary.last_day_start_utc, summary.last_close) for summary in summaries]


@pytest.mark.anyio
async def test_a_change_of_the_source_order_calculates_the_summaries_again(
    client: httpx.AsyncClient, database_url: str
) -> None:
    # IBKR saved 5..10 December without bars after 7 December. Databento has bars to 9 December.
    save_source_bars(database_url, "ibkr", APPLE, TimeRange(day(5), day(10)), [5], IBKR_CLOSE)
    save_source_bars(database_url, "databento", APPLE, TimeRange(day(5), day(10)), [5, 6, 7, 8, 9], DATABENTO_CLOSE)
    seventh_bar = Bar(day(7), IBKR_CLOSE, IBKR_CLOSE, IBKR_CLOSE, IBKR_CLOSE, Decimal(1000))
    await save_received_bars(
        database_url=database_url,
        bar_request=BarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(day(7), day(8))),
        bars=[seventh_bar],
    )
    assert await read_last_day_and_close(database_url) == [(day(7), IBKR_CLOSE)]

    response = await client.put("/api/market-data/source-order", json={"source_order": ["databento", "ibkr"]})

    assert response.status_code == 200
    assert await read_last_day_and_close(database_url) == [(day(9), DATABENTO_CLOSE)]


@pytest.mark.anyio
async def test_the_databento_import_updates_the_summary_of_each_imported_instrument(
    database_url: str, tmp_path: Path
) -> None:
    """The 4 files of the daily bars before 2024-07-01 (section 8.8.1). AAPL is listed on NASDAQ."""
    trading_day = date(2020, 1, 2)
    start, end = date(2018, 5, 1), date(2024, 7, 1)
    daily = DailyRecord(
        symbol="AAPL",
        trading_day=trading_day,
        open=Decimal(74),
        high=Decimal(76),
        low=Decimal(73),
        close=Decimal(75),
        volume=1000,
    )
    official_prices = [
        StatisticRecord(symbol="AAPL", trading_day=trading_day, stat_type=OPENING_PRICE, price=Decimal(74)),
        StatisticRecord(symbol="AAPL", trading_day=trading_day, stat_type=CLOSE_PRICE, price=Decimal("75.5")),
    ]
    files = [
        DbnFile("XNAS.ITCH", DAILY_SCHEMA, start, end, daily_records=[daily]),
        DbnFile("XNYS.PILLAR", DAILY_SCHEMA, start, end),
        DbnFile("XNAS.ITCH", STATISTICS_SCHEMA, start, end, statistic_records=official_prices),
        DbnFile("XNYS.PILLAR", STATISTICS_SCHEMA, start, end),
    ]

    import_databento_files(database_url=database_url, file_paths=write_dbn_files(tmp_path, files))

    assert await read_last_day_and_close(database_url) == [(datetime(2020, 1, 2, tzinfo=UTC), Decimal("75.5"))]
