"""Databento import program: downloads the bought batch jobs with the Databento fake and imports their DBN files.

Real PostgreSQL. No real Databento call (docs/architecture.md section 17.3).
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from atrade.app.databento_import import calculate_us_universe_quarters, log_hourly_costs, main, run_databento_import
from atrade.foundation.instrument import Instrument
from atrade.market_data import read_us_universe_members
from tests.fakes.databento import (
    CLOSE_PRICE,
    DAILY_SCHEMA,
    OPENING_PRICE,
    STATISTICS_SCHEMA,
    DailyRecord,
    DbnFile,
    FakeDatabentoClient,
    StatisticRecord,
    write_dbn_files,
)
from tests.fakes.ibkr import FakeGatewayConnection
from tests.us_universe_bars import insert_daily_bars, nasdaq, weekdays

TRADING_DAY = date(2020, 1, 2)
START = date(2018, 5, 1)
END = date(2024, 7, 1)


def create_daily_files(dataset: str, volume: int) -> list[DbnFile]:
    daily_record = DailyRecord(
        symbol="AAPL",
        trading_day=TRADING_DAY,
        open=Decimal("74.06"),
        high=Decimal("75.15"),
        low=Decimal("73.80"),
        close=Decimal("75.20"),
        volume=volume,
    )
    return [DbnFile(dataset, DAILY_SCHEMA, START, END, daily_records=[daily_record])]


def create_statistics_files(dataset: str, listed: bool) -> list[DbnFile]:
    statistic_records = [
        StatisticRecord("AAPL", TRADING_DAY, OPENING_PRICE, Decimal("74.06")),
        StatisticRecord("AAPL", TRADING_DAY, CLOSE_PRICE, Decimal("75.09")),
    ]
    return [DbnFile(dataset, STATISTICS_SCHEMA, START, END, statistic_records=statistic_records if listed else [])]


def count_bars(database_url: str) -> int:
    with psycopg.connect(database_url) as connection:
        row = connection.execute("SELECT count(*) FROM databento_bar").fetchone()
    return 0 if row is None else int(row[0])


@pytest.fixture
async def gateway() -> FakeGatewayConnection:
    connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    await connection.connect()
    return connection


@pytest.mark.anyio
async def test_the_program_downloads_each_batch_job_and_imports_all_its_files(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    client = FakeDatabentoClient(
        {
            "XNAS-20261029-AAAA": [*create_daily_files("XNAS.ITCH", 1000), *create_statistics_files("XNAS.ITCH", True)],
            "XNYS-20261029-BBBB": [
                *create_daily_files("XNYS.PILLAR", 300),
                *create_statistics_files("XNYS.PILLAR", False),
            ],
        }
    )

    report = await run_databento_import(
        database_url=database_url,
        directory=tmp_path,
        job_ids=["XNAS-20261029-AAAA", "XNYS-20261029-BBBB"],
        client=client,
        gateway=gateway,
    )

    assert client.downloaded_job_ids == ["XNAS-20261029-AAAA", "XNYS-20261029-BBBB"]
    assert report.saved_bar_count == 1
    assert count_bars(database_url) == 1


@pytest.mark.anyio
async def test_the_program_imports_the_files_that_are_already_in_the_directory(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    write_dbn_files(tmp_path / "XNAS-20261029-AAAA", [*create_daily_files("XNAS.ITCH", 1000)])
    write_dbn_files(tmp_path / "XNAS-20261029-AAAA", [*create_statistics_files("XNAS.ITCH", True)])
    write_dbn_files(tmp_path / "XNYS-20261029-BBBB", [*create_daily_files("XNYS.PILLAR", 300)])
    write_dbn_files(tmp_path / "XNYS-20261029-BBBB", [*create_statistics_files("XNYS.PILLAR", False)])

    report = await run_databento_import(
        database_url=database_url, directory=tmp_path, job_ids=[], client=None, gateway=gateway
    )

    assert report.saved_bar_count == 1


def test_the_program_does_not_download_without_a_databento_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/atrade")
    monkeypatch.setenv("DATABENTO_API_KEY", "")

    with pytest.raises(SystemExit) as stop:
        main([str(tmp_path), "--job-id", "XNAS-20261029-AAAA"])

    assert stop.value.code == 1
    assert "DATABENTO_API_KEY is empty" in caplog.text


@pytest.mark.anyio
async def test_the_program_calculates_the_us_universe_of_the_quarters_after_the_import(
    database_url: str, caplog: pytest.LogCaptureFixture
) -> None:
    insert_daily_bars(database_url, nasdaq("AAPL"), weekdays(START, date(2018, 9, 28)), "10", 100)
    caplog.set_level("INFO")

    calculate_us_universe_quarters(database_url)

    members = await read_us_universe_members(
        database_url=database_url, quarter_start_utc=datetime(2018, 10, 1, tzinfo=UTC), top_n=500
    )
    assert [member.instrument.symbol for member in members] == ["AAPL"]
    assert "Calculated the US universe of 1 quarters." in caplog.text


def insert_member(database_url: str, quarter_start: date, rank: int, instrument: Instrument) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO us_universe_member (
                quarter_start_utc, rank, symbol, exchange, currency, average_trading_value, last_ranking_day_utc
            )
            VALUES (%(quarter_start_utc)s, %(rank)s, %(symbol)s, %(exchange)s, 'USD', 1000000, %(quarter_start_utc)s)
            """,
            {
                "quarter_start_utc": datetime(quarter_start.year, quarter_start.month, quarter_start.day, tzinfo=UTC),
                "rank": rank,
                "symbol": instrument.symbol,
                "exchange": instrument.exchange,
            },
        )


def test_the_program_prints_the_cost_of_the_hourly_bars_of_each_universe_quarter_before_the_purchase(
    database_url: str, caplog: pytest.LogCaptureFixture
) -> None:
    """META was FB until 2020-03-02, so the first quarter also buys FB. The last quarter ends on the end day."""
    insert_member(database_url, date(2020, 1, 2), 1, nasdaq("META"))
    insert_member(database_url, date(2020, 1, 2), 2, nasdaq("AAPL"))
    insert_member(database_url, date(2020, 4, 1), 1, nasdaq("AAPL"))
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO databento_symbol_link (old_symbol, new_symbol, exchange, change_day)
            VALUES ('FB', 'META', 'NASDAQ', '2020-03-02')
            """
        )
    client = FakeDatabentoClient()
    caplog.set_level("INFO")

    total = log_hourly_costs(database_url=database_url, client=client, end_day=date(2020, 5, 15))

    assert client.hourly_cost_requests == [
        (["AAPL", "FB", "META"], date(2020, 1, 2), date(2020, 4, 1)),
        (["AAPL"], date(2020, 4, 1), date(2020, 5, 15)),
    ]
    assert total == Decimal("0.04")
    assert "XNAS.ITCH ohlcv-1h 2020-01-02 to 2020-04-01: 3 symbols, 0.03 USD: AAPL FB META" in caplog.text
    assert "The hourly bars of 2 quarters cost 0.04 USD." in caplog.text
