"""Stock splits from IBKR evidence: evidence A of the bars route and the change of the stored bars.

Real PostgreSQL and the IBKR fake (docs/architecture/market_data.md sections 8.13.2 and 8.13.3).
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import psycopg
import pytest
from psycopg import sql

from atrade.app.web import create_web_app
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayRequestError
from atrade.market_data import (
    BarRequest,
    BarSource,
    StockSplitCandidate,
    StockSplitChange,
    StockSplitConfirmedError,
    apply_stock_split,
    read_daily_bar_summaries,
    read_saved_bars,
    read_stock_split_candidates,
    read_unsaved_ranges,
    save_received_bars,
)
from tests.backtest.real_runner import (
    TEST_STRATEGY_FILE,
    run_backtest_runner,
    save_test_bars,
    start_backtest,
    wait_for_final_status,
)
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection

BARS_PATH = "/api/market-data/bars"
BTEST = Instrument(symbol="BTEST", exchange="ARCA", currency="USD")
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
# The fixed clock is 2026-01-02 03:04:05 UTC.
STORED_DAY_UTC = datetime(2025, 12, 29, tzinfo=UTC)
ONE_DAY = timedelta(days=1)
RECORDED_AT_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
# Bars from Monday 22 December to Friday 26 December 2025. The ex-date is Wednesday 24 December.
BAR_DAYS_UTC = [datetime(2025, 12, 22, tzinfo=UTC) + ONE_DAY * offset for offset in range(5)]
EX_DATE_UTC = datetime(2025, 12, 24, tzinfo=UTC)
STORED_RANGE = TimeRange(BAR_DAYS_UTC[0], BAR_DAYS_UTC[-1] + ONE_DAY)


def create_bar(start_utc: datetime, close: str, volume: str = "1000") -> Bar:
    price = Decimal(close)
    return Bar(start_utc=start_utc, open=price, high=price, low=price, close=price, volume=Decimal(volume))


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


async def save_daily_bar(database_url: str, bar: Bar) -> None:
    bar_request = BarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(bar.start_utc, bar.start_utc + ONE_DAY))
    await save_received_bars(database_url=database_url, bar_request=bar_request, bars=[bar])


async def read_daily_closes(client: httpx.AsyncClient, time_range: TimeRange) -> list[float]:
    response = await client.get(
        BARS_PATH,
        params={
            "symbol": APPLE.symbol,
            "exchange": APPLE.exchange,
            "currency": APPLE.currency,
            "bar_period": "1-DAY",
            "start_utc": time_range.start_utc.isoformat(),
            "end_utc": time_range.end_utc.isoformat(),
        },
    )
    assert response.status_code == 200
    return [bar["close"] for bar in response.json()["bars"]]


async def read_missing_daily_bars(client: httpx.AsyncClient) -> None:
    """The days after the stored day are missing, so the bars route reads them from IBKR."""
    await read_daily_closes(client, TimeRange(STORED_DAY_UTC + ONE_DAY, datetime(2026, 1, 2, tzinfo=UTC)))


@pytest.mark.anyio
async def test_a_bar_read_from_ibkr_reads_the_stored_day_again_and_finds_a_split_ratio_of_2(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    await save_daily_bar(database_url, create_bar(STORED_DAY_UTC, "100"))
    gateway_connection.historical_bars[APPLE] = [
        create_bar(STORED_DAY_UTC + ONE_DAY * offset, close) for offset, close in enumerate(["50", "51", "52"])
    ]

    await read_missing_daily_bars(client)

    stored_day_request = TimeRange(STORED_DAY_UTC, STORED_DAY_UTC + ONE_DAY)
    assert stored_day_request in [request.time_range for request in gateway_connection.historical_bar_requests]
    candidates = await read_stock_split_candidates(database_url=database_url)
    assert candidates == [
        StockSplitCandidate(
            id=candidates[0].id, instrument=APPLE, ex_date_utc=STORED_DAY_UTC + ONE_DAY, split_ratio=Decimal(2)
        )
    ]


@pytest.mark.anyio
async def test_a_ratio_of_1_gives_no_candidate(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    await save_daily_bar(database_url, create_bar(STORED_DAY_UTC, "100"))
    gateway_connection.historical_bars[APPLE] = [
        create_bar(STORED_DAY_UTC + ONE_DAY * offset, close) for offset, close in enumerate(["100.4", "101", "102"])
    ]

    await read_missing_daily_bars(client)

    assert await read_stock_split_candidates(database_url=database_url) == []


def store_bars(database_url: str, bar_source: BarSource, bar_period: BarPeriod, close: str) -> None:
    """Saves 1 bar for each day of `BAR_DAYS_UTC` and the saved range in the tables of the bar source, like its writer
    does. The volume is 1000."""
    key = {"symbol": APPLE.symbol, "exchange": APPLE.exchange, "currency": APPLE.currency, "bar_period": bar_period}
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            sql.SQL("""
                INSERT INTO {} (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
                VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, %(start_utc)s, %(close)s,
                    %(close)s, %(close)s, %(close)s, 1000)
            """).format(sql.Identifier(f"{bar_source}_bar")),
            [{**key, "start_utc": start_utc, "close": Decimal(close)} for start_utc in BAR_DAYS_UTC],
        )
        cursor.execute(
            sql.SQL("""
                INSERT INTO {} (symbol, exchange, currency, bar_period, start_utc, end_utc)
                VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, %(start_utc)s, %(end_utc)s)
            """).format(sql.Identifier(f"{bar_source}_bar_saved_range")),
            {**key, "start_utc": STORED_RANGE.start_utc, "end_utc": STORED_RANGE.end_utc},
        )


def store_bars_of_all_sources(database_url: str) -> None:
    store_bars(database_url, BarSource.IBKR, BarPeriod.ONE_DAY, "100")
    store_bars(database_url, BarSource.IBKR, BarPeriod.ONE_HOUR, "100")
    store_bars(database_url, BarSource.DATABENTO, BarPeriod.ONE_DAY, "100")


async def read_prices_and_volumes(database_url: str, bar_source: BarSource, bar_period: BarPeriod) -> list[str]:
    saved = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(APPLE, bar_period, STORED_RANGE),
        source_order=[bar_source],
    )
    return [
        " ".join(f"{value.normalize():f}" for value in (bar.open, bar.high, bar.low, bar.close, bar.volume))
        for bar in saved.bars
    ]


def read_stock_split_rows(database_url: str) -> list[tuple[object, ...]]:
    with psycopg.connect(database_url) as connection:
        return connection.execute(
            "SELECT symbol, ex_date_utc, split_ratio, source, confirmation FROM stock_split"
        ).fetchall()


SPLIT_OF_2 = StockSplitChange(instrument=APPLE, ex_date_utc=EX_DATE_UTC, split_ratio=Decimal(2))


BEFORE_AND_AFTER_THE_EX_DATE = [
    "50 50 50 50 2000",
    "50 50 50 50 2000",
    "100 100 100 100 1000",
    "100 100 100 100 1000",
    "100 100 100 100 1000",
]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("bar_source", "bar_period"),
    [
        (BarSource.IBKR, BarPeriod.ONE_DAY),
        (BarSource.IBKR, BarPeriod.ONE_HOUR),
        (BarSource.DATABENTO, BarPeriod.ONE_DAY),
    ],
)
async def test_the_change_divides_the_prices_and_multiplies_the_volume_of_each_bar_before_the_ex_date(
    database_url: str, bar_source: BarSource, bar_period: BarPeriod
) -> None:
    store_bars_of_all_sources(database_url)

    await apply_stock_split(
        database_url=database_url, change=SPLIT_OF_2, confirmation="bar_evidence", recorded_at_utc=RECORDED_AT_UTC
    )

    assert await read_prices_and_volumes(database_url, bar_source, bar_period) == BEFORE_AND_AFTER_THE_EX_DATE


@pytest.mark.anyio
async def test_the_change_writes_the_stock_split_row(database_url: str) -> None:
    store_bars_of_all_sources(database_url)

    await apply_stock_split(
        database_url=database_url, change=SPLIT_OF_2, confirmation="bar_evidence", recorded_at_utc=RECORDED_AT_UTC
    )

    assert read_stock_split_rows(database_url) == [("AAPL", EX_DATE_UTC, Decimal(2), "ibkr_evidence", "bar_evidence")]


@pytest.mark.anyio
async def test_the_change_updates_the_daily_bar_summary(database_url: str) -> None:
    # Evidence A gives the day after the last stored day as the ex-date, so the last stored close changes.
    store_bars(database_url, BarSource.IBKR, BarPeriod.ONE_DAY, "100")
    await save_daily_bar(database_url, create_bar(BAR_DAYS_UTC[-1], "100"))
    change = StockSplitChange(instrument=APPLE, ex_date_utc=STORED_RANGE.end_utc, split_ratio=Decimal(4))

    await apply_stock_split(
        database_url=database_url, change=change, confirmation="both_evidences", recorded_at_utc=RECORDED_AT_UTC
    )

    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE])
    assert [(summary.last_day_start_utc, summary.last_close) for summary in summaries] == [
        (BAR_DAYS_UTC[-1], Decimal(25))
    ]


@pytest.mark.anyio
async def test_the_change_sends_no_ibkr_request_and_keeps_all_bars_and_saved_ranges(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    assert client is not None
    store_bars_of_all_sources(database_url)

    await apply_stock_split(
        database_url=database_url, change=SPLIT_OF_2, confirmation="user_apply", recorded_at_utc=RECORDED_AT_UTC
    )

    assert gateway_connection.historical_bar_requests == []
    for bar_period in (BarPeriod.ONE_DAY, BarPeriod.ONE_HOUR):
        bar_request = BarRequest(APPLE, bar_period, STORED_RANGE)
        assert await read_unsaved_ranges(database_url=database_url, bar_request=bar_request) == []
    assert len(await read_prices_and_volumes(database_url, BarSource.IBKR, BarPeriod.ONE_HOUR)) == len(BAR_DAYS_UTC)
    assert len(await read_prices_and_volumes(database_url, BarSource.DATABENTO, BarPeriod.ONE_DAY)) == len(BAR_DAYS_UTC)


@pytest.mark.anyio
async def test_a_confirmed_stock_split_does_not_change_the_bars_again(database_url: str) -> None:
    store_bars_of_all_sources(database_url)
    await apply_stock_split(
        database_url=database_url, change=SPLIT_OF_2, confirmation="bar_evidence", recorded_at_utc=RECORDED_AT_UTC
    )

    with pytest.raises(StockSplitConfirmedError):
        await apply_stock_split(
            database_url=database_url, change=SPLIT_OF_2, confirmation="user_apply", recorded_at_utc=RECORDED_AT_UTC
        )

    assert (
        await read_prices_and_volumes(database_url, BarSource.IBKR, BarPeriod.ONE_DAY) == BEFORE_AND_AFTER_THE_EX_DATE
    )


@pytest.mark.anyio
async def test_a_failed_step_changes_neither_the_bars_nor_the_stock_split_table(database_url: str) -> None:
    store_bars_of_all_sources(database_url)
    with psycopg.connect(database_url, autocommit=True) as connection:
        # The last step, the update of the daily bar summary, fails.
        connection.execute("""
            CREATE FUNCTION fail_summary_write() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'summary write failed'; END $$;
            CREATE TRIGGER fail_summary_write BEFORE INSERT OR UPDATE ON daily_bar_summary
                FOR EACH ROW EXECUTE FUNCTION fail_summary_write();
        """)
    try:
        with pytest.raises(psycopg.errors.RaiseException):
            await apply_stock_split(
                database_url=database_url,
                change=SPLIT_OF_2,
                confirmation="bar_evidence",
                recorded_at_utc=RECORDED_AT_UTC,
            )
    finally:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute("DROP TRIGGER fail_summary_write ON daily_bar_summary")
            connection.execute("DROP FUNCTION fail_summary_write()")

    unchanged = ["100 100 100 100 1000"] * len(BAR_DAYS_UTC)
    assert await read_prices_and_volumes(database_url, BarSource.IBKR, BarPeriod.ONE_DAY) == unchanged
    assert read_stock_split_rows(database_url) == []


@pytest.mark.anyio
async def test_older_ibkr_bars_get_the_stored_form_until_the_change_divides_them(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    # Stored: 29 December at the old price 100. IBKR gives all days at the new price 50 after a split of 2.
    await save_daily_bar(database_url, create_bar(STORED_DAY_UTC, "100"))
    older_range = TimeRange(STORED_DAY_UTC - ONE_DAY * 3, STORED_DAY_UTC)
    gateway_connection.historical_bars[APPLE] = [
        create_bar(older_range.start_utc + ONE_DAY * offset, "50") for offset in range(4)
    ]

    closes_before_the_change = await read_daily_closes(client, older_range)
    [candidate] = await read_stock_split_candidates(database_url=database_url)
    change = StockSplitChange(candidate.instrument, candidate.ex_date_utc, candidate.split_ratio)
    await apply_stock_split(
        database_url=database_url, change=change, confirmation="bar_evidence", recorded_at_utc=RECORDED_AT_UTC
    )

    assert closes_before_the_change == [100.0, 100.0, 100.0]
    assert await read_daily_closes(client, TimeRange(older_range.start_utc, STORED_DAY_UTC + ONE_DAY)) == [50.0] * 4


@pytest.mark.anyio
async def test_the_saved_results_of_a_finished_backtest_do_not_change(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    backtest_id = await start_backtest(web_client, TEST_STRATEGY_FILE.read_text())
    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        finished = await wait_for_final_status(web_client, backtest_id)
    assert finished["status"] == "finished"
    change = StockSplitChange(instrument=BTEST, ex_date_utc=datetime(2026, 3, 16, tzinfo=UTC), split_ratio=Decimal(2))

    await apply_stock_split(
        database_url=database_url, change=change, confirmation="bar_evidence", recorded_at_utc=RECORDED_AT_UTC
    )

    assert (await web_client.get(f"/api/backtests/{backtest_id}")).json() == finished


def write_waiting_import_split(database_url: str, ex_date_utc: datetime) -> None:
    """A Databento import split of 2 for APPLE that waits for the import check."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO stock_split (
                symbol, exchange, currency, ex_date_utc, split_ratio, source, confirmation, recorded_at_utc
            )
            VALUES ('AAPL', 'NASDAQ', 'USD', %(ex_date_utc)s, 2, 'databento_import', NULL, now())
            """,
            {"ex_date_utc": ex_date_utc},
        )


@pytest.mark.anyio
async def test_a_waiting_import_split_gives_no_second_candidate_and_new_ibkr_bars_get_the_stored_form(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    # The real ex-date is 2 days after the stored day. The import check confirms the split later.
    await save_daily_bar(database_url, create_bar(STORED_DAY_UTC, "100"))
    write_waiting_import_split(database_url, STORED_DAY_UTC + ONE_DAY * 2)
    gateway_connection.historical_bars[APPLE] = [
        create_bar(STORED_DAY_UTC + ONE_DAY * offset, "50") for offset in range(4)
    ]

    closes = await read_daily_closes(client, TimeRange(STORED_DAY_UTC, datetime(2026, 1, 2, tzinfo=UTC)))

    assert await read_stock_split_candidates(database_url=database_url) == []
    assert closes == [100.0, 100.0, 50.0, 50.0]


@pytest.mark.anyio
async def test_an_ibkr_confirmation_does_not_take_a_waiting_import_split(database_url: str) -> None:
    store_bars_of_all_sources(database_url)
    write_waiting_import_split(database_url, EX_DATE_UTC)

    with pytest.raises(StockSplitConfirmedError):
        await apply_stock_split(
            database_url=database_url, change=SPLIT_OF_2, confirmation="bar_evidence", recorded_at_utc=RECORDED_AT_UTC
        )

    assert [row[3:] for row in read_stock_split_rows(database_url)] == [("databento_import", None)]
    unchanged = ["100 100 100 100 1000"] * len(BAR_DAYS_UTC)
    assert await read_prices_and_volumes(database_url, BarSource.IBKR, BarPeriod.ONE_DAY) == unchanged


@pytest.mark.anyio
async def test_received_bars_before_the_ex_date_of_a_candidate_get_the_stored_form(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    await save_daily_bar(database_url, create_bar(STORED_DAY_UTC, "100"))
    gateway_connection.historical_bars[APPLE] = [
        create_bar(STORED_DAY_UTC + ONE_DAY * offset, "50") for offset in range(4)
    ]
    await read_missing_daily_bars(client)

    # A forward test saves warm-up bars that it received from IBKR in the new form.
    await save_daily_bar(database_url, create_bar(STORED_DAY_UTC - ONE_DAY, "50", volume="2000"))

    saved = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(STORED_DAY_UTC - ONE_DAY, STORED_DAY_UTC)),
        source_order=[BarSource.IBKR],
    )
    assert [(bar.close, bar.volume) for bar in saved.bars] == [(Decimal(100), Decimal(1000))]


class StoredDayFailingGateway(FakeGatewayConnection):
    """The read of the stored day again fails. Other reads work."""

    async def read_historical_bars(
        self, instrument: Instrument, bar_period: BarPeriod, time_range: TimeRange
    ) -> list[Bar]:
        if time_range == TimeRange(STORED_DAY_UTC, STORED_DAY_UTC + ONE_DAY):
            message = "Historical data request pacing violation"
            raise GatewayRequestError(message)
        return await super().read_historical_bars(instrument, bar_period, time_range)


@pytest.mark.anyio
async def test_a_failed_read_of_the_stored_day_does_not_stop_the_read_of_the_missing_bars(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    gateway_connection = StoredDayFailingGateway(managed_accounts=["DU1234567"])
    gateway_connection.connected = True
    gateway_connection.historical_bars[APPLE] = [
        create_bar(STORED_DAY_UTC + ONE_DAY * offset, "50") for offset in range(1, 4)
    ]
    await save_daily_bar(database_url, create_bar(STORED_DAY_UTC, "100"))
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http_client:
        missing_range = TimeRange(STORED_DAY_UTC + ONE_DAY, datetime(2026, 1, 2, tzinfo=UTC))
        closes = await read_daily_closes(http_client, missing_range)

    assert closes == [50.0, 50.0, 50.0]
    assert await read_stock_split_candidates(database_url=database_url) == []
