"""Bar sources: the tables of each bar source, the source order route, and reads through the source order.

Real PostgreSQL and the IBKR fake (docs/architecture/market_data.md section 8.7).
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql

from atrade.app.database_migrations import MIGRATIONS_DIR
from atrade.app.web import create_web_app
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from atrade.market_data import BarRequest, BarSource, has_saved_bars, read_saved_bars
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, HistoricalBarRequest

SOURCE_ORDER_PATH = "/api/market-data/source-order"
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
IBKR_CLOSE = Decimal(100)
DATABENTO_CLOSE = Decimal(200)
PREVIOUS_REVISION = "c4a8e2f6b913"


def day(number: int) -> datetime:
    return datetime(2025, 12, number, tzinfo=UTC)


def save_source_bars(
    database_url: str, bar_source: str, saved_range: TimeRange, bar_days: list[int], close: Decimal
) -> None:
    """Saves daily APPLE bars and one saved range in the tables of one bar source, like its writer does."""
    key = {"symbol": APPLE.symbol, "exchange": APPLE.exchange, "currency": APPLE.currency, "bar_period": "1-DAY"}
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


def save_ibkr_range_with_a_holiday_and_a_longer_databento_range(database_url: str) -> None:
    # IBKR saved 5..8 December. 6 December is a holiday: IBKR has no bar. Databento saved 5..10 December, all days.
    save_source_bars(database_url, "ibkr", TimeRange(day(5), day(8)), [5, 7], IBKR_CLOSE)
    save_source_bars(database_url, "databento", TimeRange(day(5), day(10)), [5, 6, 7, 8, 9], DATABENTO_CLOSE)


DECEMBER_REQUEST = BarRequest(instrument=APPLE, bar_period=BarPeriod.ONE_DAY, time_range=TimeRange(day(1), day(20)))


@pytest.fixture
def gateway_connection() -> FakeGatewayConnection:
    connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    connection.connected = True
    return connection


@pytest.fixture
async def client(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, gateway_connection: FakeGatewayConnection
) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


def test_the_migration_keeps_the_bars_and_adds_the_databento_tables_and_the_source_order(database_url: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["database_url"] = database_url
    command.downgrade(config, PREVIOUS_REVISION)
    try:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute("""
                INSERT INTO bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
                VALUES ('AAPL', 'NASDAQ', 'USD', '1-DAY', '2025-12-05Z', 1, 2, 0.5, 1.5, 10)
            """)
            connection.execute("""
                INSERT INTO bar_saved_range (symbol, exchange, currency, bar_period, start_utc, end_utc)
                VALUES ('AAPL', 'NASDAQ', 'USD', '1-DAY', '2025-12-05Z', '2025-12-06Z')
            """)
    finally:
        command.upgrade(config, "head")

    with psycopg.connect(database_url, autocommit=True) as connection:
        bars = connection.execute("SELECT symbol, close FROM ibkr_bar").fetchall()
        saved_ranges = connection.execute("SELECT symbol, start_utc FROM ibkr_bar_saved_range").fetchall()
        source_order = connection.execute("SELECT bar_sources FROM source_order").fetchall()
        databento_counts = connection.execute(
            "SELECT (SELECT count(*) FROM databento_bar), (SELECT count(*) FROM databento_bar_saved_range)"
        ).fetchall()
    assert bars == [("AAPL", Decimal("1.5"))]
    assert saved_ranges == [("AAPL", day(5))]
    assert source_order == [(["ibkr", "databento"],)]
    assert databento_counts == [(0, 0)]


@pytest.mark.anyio
async def test_reads_the_default_source_order(client: httpx.AsyncClient) -> None:
    response = await client.get(SOURCE_ORDER_PATH)

    assert response.status_code == 200
    assert response.json() == {"source_order": ["ibkr", "databento"]}


@pytest.mark.anyio
async def test_saves_a_new_source_order(client: httpx.AsyncClient) -> None:
    put_response = await client.put(SOURCE_ORDER_PATH, json={"source_order": ["databento", "ibkr"]})
    get_response = await client.get(SOURCE_ORDER_PATH)

    assert put_response.status_code == 200
    assert put_response.json() == {"source_order": ["databento", "ibkr"]}
    assert get_response.json() == {"source_order": ["databento", "ibkr"]}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "source_order",
    [[], ["ibkr", "ibkr"], ["ibkr", "databento", "ibkr"], ["ibkr", "yahoo"], ["databento"]],
)
async def test_refuses_a_source_order_that_is_empty_has_a_value_two_times_or_an_unknown_value(
    client: httpx.AsyncClient, source_order: list[str]
) -> None:
    response = await client.put(SOURCE_ORDER_PATH, json={"source_order": source_order})

    assert response.status_code == 422
    assert (await client.get(SOURCE_ORDER_PATH)).json() == {"source_order": ["ibkr", "databento"]}


@pytest.mark.anyio
async def test_the_first_bar_source_that_saved_a_range_gives_all_its_bars_and_holidays_stay_empty(
    database_url: str,
) -> None:
    save_ibkr_range_with_a_holiday_and_a_longer_databento_range(database_url)

    saved_bars = await read_saved_bars(
        database_url=database_url, bar_request=DECEMBER_REQUEST, source_order=[BarSource.IBKR, BarSource.DATABENTO]
    )

    assert [(bar.start_utc, bar.close) for bar in saved_bars.bars] == [
        (day(5), IBKR_CLOSE),
        (day(7), IBKR_CLOSE),
        (day(8), DATABENTO_CLOSE),
        (day(9), DATABENTO_CLOSE),
    ]
    assert saved_bars.bar_counts == {BarSource.IBKR: 2, BarSource.DATABENTO: 2}


@pytest.mark.anyio
async def test_read_saved_bars_counts_the_bars_of_each_bar_source_in_the_source_order(database_url: str) -> None:
    save_ibkr_range_with_a_holiday_and_a_longer_databento_range(database_url)

    saved_bars = await read_saved_bars(
        database_url=database_url, bar_request=DECEMBER_REQUEST, source_order=[BarSource.DATABENTO, BarSource.IBKR]
    )

    assert [bar.start_utc for bar in saved_bars.bars] == [day(5), day(6), day(7), day(8), day(9)]
    assert {bar.close for bar in saved_bars.bars} == {DATABENTO_CLOSE}
    assert list(saved_bars.bar_counts.items()) == [(BarSource.DATABENTO, 5), (BarSource.IBKR, 0)]


@pytest.mark.anyio
async def test_has_saved_bars_is_false_in_a_holiday_that_the_first_bar_source_saved(database_url: str) -> None:
    save_ibkr_range_with_a_holiday_and_a_longer_databento_range(database_url)
    holiday_request = BarRequest(instrument=APPLE, bar_period=BarPeriod.ONE_DAY, time_range=TimeRange(day(6), day(7)))

    ibkr_first = await has_saved_bars(
        database_url=database_url, bar_request=holiday_request, source_order=[BarSource.IBKR, BarSource.DATABENTO]
    )
    databento_first = await has_saved_bars(
        database_url=database_url, bar_request=holiday_request, source_order=[BarSource.DATABENTO, BarSource.IBKR]
    )

    assert (ibkr_first, databento_first) == (False, True)


@pytest.mark.anyio
async def test_the_bars_route_asks_ibkr_only_for_parts_that_no_bar_source_saved(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_ibkr_range_with_a_holiday_and_a_longer_databento_range(database_url)
    end_utc = day(12)

    response = await client.get(
        "/api/market-data/bars",
        params={
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "currency": "USD",
            "bar_period": "1-DAY",
            "start_utc": day(5).isoformat(),
            "end_utc": end_utc.isoformat(),
        },
    )

    assert response.status_code == 200
    assert gateway_connection.historical_bar_requests == [
        HistoricalBarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(day(10), end_utc))
    ]
    bar_times = [bar["time"] for bar in response.json()["bars"]]
    expected_days = [day(5), day(7), day(8), day(9), day(10), day(11)]
    assert bar_times == [int(time_utc.timestamp()) for time_utc in expected_days]
    with psycopg.connect(database_url, autocommit=True) as connection:
        ibkr_ranges = connection.execute("SELECT start_utc, end_utc FROM ibkr_bar_saved_range").fetchall()
    assert ibkr_ranges == [(day(5), day(8)), (day(10), day(10) + timedelta(days=2))]


@pytest.mark.anyio
async def test_the_watchlist_lists_saved_bars_by_bar_period_then_by_the_source_order(
    client: httpx.AsyncClient, database_url: str
) -> None:
    save_ibkr_range_with_a_holiday_and_a_longer_databento_range(database_url)
    await client.post("/api/watchlist", json={"symbol": "AAPL", "exchange": "NASDAQ", "currency": "USD"})
    await client.put(SOURCE_ORDER_PATH, json={"source_order": ["databento", "ibkr"]})

    response = await client.get("/api/watchlist")

    assert response.json()["instruments"][0]["saved_bars"] == [
        {
            "bar_source": "databento",
            "bar_period": "1-DAY",
            "first_start_utc": "2025-12-05T00:00:00Z",
            "last_start_utc": "2025-12-09T00:00:00Z",
        },
        {
            "bar_source": "ibkr",
            "bar_period": "1-DAY",
            "first_start_utc": "2025-12-05T00:00:00Z",
            "last_start_utc": "2025-12-07T00:00:00Z",
        },
    ]
