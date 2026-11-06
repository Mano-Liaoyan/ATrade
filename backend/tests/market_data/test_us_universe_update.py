"""Quarterly US universe update: from 06:00 ET on the first trading day of the quarter until the quarter has members,
download the EQUS.SUMMARY bars, import them, and save the members (docs/architecture/market_data.md section 8.9).

Real PostgreSQL, a fixed clock, and the Databento fake.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from atrade.market_data import (
    UsUniverseCalculationError,
    UsUniverseUpdate,
    read_us_universe_members,
    us_universe_update,
)
from atrade.market_data.databento_client import DatabentoDownloadNotStartedError
from tests.fakes.clock import FixedClock
from tests.fakes.databento import DailyRecord, FakeDatabentoClient
from tests.us_universe_bars import insert_daily_bars, nasdaq, nyse, weekdays

NEW_YORK = ZoneInfo("America/New_York")
QUARTER_START_UTC = datetime(2025, 1, 2, tzinfo=UTC)
PREVIOUS_QUARTER_DAYS = weekdays(date(2024, 10, 1), date(2024, 12, 31))


def at_new_york_time(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=NEW_YORK).astimezone(UTC)


def summary_records(symbol: str, days: list[date], close: str, volume: int) -> list[DailyRecord]:
    price = Decimal(close)
    return [DailyRecord(symbol, day, price, price, price, price, volume) for day in days]


@pytest.fixture
def client(database_url: str) -> FakeDatabentoClient:
    """The history has 1 bar of each symbol before the download: the import takes the listing exchange from it."""
    insert_daily_bars(database_url, nasdaq("AAPL"), [date(2024, 9, 13)], "1", 1)
    insert_daily_bars(database_url, nyse("IBM"), [date(2024, 9, 13)], "1", 1)
    # IBM has the higher value on the last day of the quarter only: it decides the rank in the full window.
    records = summary_records("AAPL", PREVIOUS_QUARTER_DAYS, "100", 1000)
    records += summary_records("IBM", PREVIOUS_QUARTER_DAYS[:-1], "100", 990)
    records += summary_records("IBM", PREVIOUS_QUARTER_DAYS[-1:], "100", 10**6)
    return FakeDatabentoClient(summary_records=records, summary_end=date(2025, 1, 1))


def create_update(
    database_url: str, clock: FixedClock, client: FakeDatabentoClient, tmp_path: Path
) -> UsUniverseUpdate:
    return UsUniverseUpdate(database_url=database_url, clock=clock, client=client, download_dir=tmp_path)


async def read_ranked_symbols(database_url: str) -> list[tuple[int, str, datetime]]:
    members = await read_us_universe_members(database_url=database_url, quarter_start_utc=QUARTER_START_UTC, top_n=500)
    return [(member.rank, member.instrument.symbol, member.last_ranking_day_utc) for member in members]


@pytest.mark.anyio
async def test_the_update_at_06_00_et_downloads_the_100_days_to_the_last_ranking_day_and_saves_the_members(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path
) -> None:
    clock = FixedClock(at_new_york_time(date(2025, 1, 2), 5, 59))
    update = create_update(database_url, clock, client, tmp_path)

    update.update_if_due()
    assert client.summary_downloads == []

    clock.now_utc = at_new_york_time(date(2025, 1, 2), 6)
    update.update_if_due()

    assert client.summary_downloads == [(date(2024, 9, 22), date(2025, 1, 1))]
    last_day = datetime(2024, 12, 31, tzinfo=UTC)
    assert await read_ranked_symbols(database_url) == [(1, "IBM", last_day), (2, "AAPL", last_day)]


@pytest.mark.anyio
async def test_a_symbol_renamed_in_the_window_is_a_member_under_the_new_symbol_and_the_update_logs_the_link(
    database_url: str, clock: FixedClock, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    insert_daily_bars(database_url, nasdaq("SQ"), [date(2024, 9, 13)], "1", 1)
    middle = len(PREVIOUS_QUARTER_DAYS) // 2
    records = summary_records("SQ", PREVIOUS_QUARTER_DAYS[:middle], "100", 1000)
    records += summary_records("XYZ", PREVIOUS_QUARTER_DAYS[middle:], "100", 1000)
    client = FakeDatabentoClient(summary_records=records, summary_end=date(2025, 1, 1))
    clock.now_utc = at_new_york_time(date(2025, 1, 2), 6)

    with caplog.at_level(logging.INFO):
        create_update(database_url, clock, client, tmp_path).update_if_due()

    assert [symbol for _, symbol, _ in await read_ranked_symbols(database_url)] == ["XYZ"]
    assert "SQ to XYZ" in caplog.text


@pytest.mark.anyio
async def test_the_update_does_not_run_before_the_first_trading_day_of_the_quarter_and_runs_only_one_time(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path
) -> None:
    # 2025-01-01 is New Year's Day.
    clock = FixedClock(at_new_york_time(date(2025, 1, 1), 7))
    update = create_update(database_url, clock, client, tmp_path)
    update.update_if_due()
    clock.now_utc = at_new_york_time(date(2025, 1, 2), 7)
    update.update_if_due()
    clock.now_utc = at_new_york_time(date(2025, 1, 2), 8)
    update.update_if_due()
    clock.now_utc = at_new_york_time(date(2025, 1, 3), 7)
    update.update_if_due()

    assert len(client.summary_downloads) == 1


@pytest.mark.anyio
async def test_the_update_tries_again_each_15_minutes_and_uses_1_day_earlier_at_09_00_et(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path
) -> None:
    client.summary_end = date(2024, 12, 31)
    clock = FixedClock(at_new_york_time(date(2025, 1, 2), 6))
    update = create_update(database_url, clock, client, tmp_path)

    update.update_if_due()
    clock.now_utc = at_new_york_time(date(2025, 1, 2), 6, 14)
    update.update_if_due()
    assert client.summary_end_reads == 1
    for minute in range(6 * 60 + 15, 9 * 60, 15):
        clock.now_utc = at_new_york_time(date(2025, 1, 2), minute // 60, minute % 60)
        update.update_if_due()
    assert client.summary_end_reads == 12
    assert client.summary_downloads == []

    clock.now_utc = at_new_york_time(date(2025, 1, 2), 9)
    update.update_if_due()

    assert client.summary_downloads == [(date(2024, 9, 21), date(2024, 12, 31))]
    # Without the IBM bar of 2024-12-31, AAPL is first.
    last_day = datetime(2024, 12, 30, tzinfo=UTC)
    assert await read_ranked_symbols(database_url) == [(1, "AAPL", last_day), (2, "IBM", last_day)]


@pytest.mark.anyio
async def test_a_bar_that_becomes_available_before_09_00_et_gives_the_full_window(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path
) -> None:
    client.summary_end = date(2024, 12, 31)
    clock = FixedClock(at_new_york_time(date(2025, 1, 2), 6))
    update = create_update(database_url, clock, client, tmp_path)
    update.update_if_due()

    client.summary_end = date(2025, 1, 1)
    clock.now_utc = at_new_york_time(date(2025, 1, 2), 6, 15)
    update.update_if_due()

    assert client.summary_downloads == [(date(2024, 9, 22), date(2025, 1, 1))]
    last_day = datetime(2024, 12, 31, tzinfo=UTC)
    assert await read_ranked_symbols(database_url) == [(1, "IBM", last_day), (2, "AAPL", last_day)]


@pytest.mark.anyio
async def test_the_update_runs_on_a_later_day_when_the_quarter_has_no_members(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path
) -> None:
    update = create_update(database_url, FixedClock(at_new_york_time(date(2025, 1, 6), 7)), client, tmp_path)

    update.update_if_due()

    assert client.summary_downloads == [(date(2024, 9, 22), date(2025, 1, 1))]
    last_day = datetime(2024, 12, 31, tzinfo=UTC)
    assert await read_ranked_symbols(database_url) == [(1, "IBM", last_day), (2, "AAPL", last_day)]


def test_a_saved_quarter_stops_the_database_reads_of_the_update(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path
) -> None:
    clock = FixedClock(at_new_york_time(date(2025, 1, 2), 6))
    update = create_update(database_url, clock, client, tmp_path)
    update.update_if_due()
    clock.now_utc = at_new_york_time(date(2025, 1, 2), 6, 1)
    update.update_if_due()

    # A database read raises an error now.
    update.database_url = "postgresql://localhost:1/none"
    clock.now_utc = at_new_york_time(date(2025, 1, 2), 6, 2)
    update.update_if_due()

    assert len(client.summary_downloads) == 1


def test_a_failed_save_uses_the_downloaded_file_again(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path
) -> None:
    client.summary_records = client.summary_records[:10]
    clock = FixedClock(at_new_york_time(date(2025, 1, 2), 6))
    update = create_update(database_url, clock, client, tmp_path)

    for _ in range(3):
        with pytest.raises(UsUniverseCalculationError):
            update.update_if_due()
        clock.now_utc += timedelta(minutes=15)

    assert len(client.summary_downloads) == 1


@pytest.mark.anyio
async def test_a_failed_import_uses_the_downloaded_file_again(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_import(**_: object) -> None:
        raise OSError

    update = create_update(database_url, FixedClock(at_new_york_time(date(2025, 1, 2), 6)), client, tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(us_universe_update, "import_databento_files", fail_import)
        with pytest.raises(OSError):
            update.update_if_due()

    update.update_if_due()

    assert len(client.summary_downloads) == 1
    assert len(await read_ranked_symbols(database_url)) == 2


@pytest.mark.anyio
async def test_a_failed_download_is_not_used_again(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path
) -> None:
    client.summary_download_failures = 1
    update = create_update(database_url, FixedClock(at_new_york_time(date(2025, 1, 2), 6)), client, tmp_path)
    with pytest.raises(OSError):
        update.update_if_due()

    update.update_if_due()

    assert len(client.summary_downloads) == 2
    assert len(await read_ranked_symbols(database_url)) == 2


def test_a_process_stops_after_3_downloads_that_can_bill_and_logs_the_stop_1_time(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    client.summary_download_failures = 10
    clock = FixedClock(at_new_york_time(date(2025, 1, 2), 6))
    update = create_update(database_url, clock, client, tmp_path)
    for _ in range(3):
        with pytest.raises(OSError):
            update.update_if_due()

    update.update_if_due()
    update.update_if_due()

    assert len(client.summary_downloads) == 3
    assert [record.message for record in caplog.records if "stops" in record.message] == [
        "The US universe update of 2025-01-02 stops after 3 downloads that can bill. A restart clears the limit."
    ]


@pytest.mark.anyio
async def test_a_databento_outage_does_not_use_the_download_limit(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path
) -> None:
    client.summary_download_outages = 5
    update = create_update(database_url, FixedClock(at_new_york_time(date(2025, 1, 2), 6)), client, tmp_path)
    for _ in range(5):
        with pytest.raises(DatabentoDownloadNotStartedError):
            update.update_if_due()

    update.update_if_due()

    assert len(await read_ranked_symbols(database_url)) == 2


@pytest.mark.anyio
async def test_a_restart_after_the_import_does_not_buy_the_window_again(
    database_url: str, client: FakeDatabentoClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_save(**_: object) -> None:
        raise OSError

    clock = FixedClock(at_new_york_time(date(2025, 1, 2), 6))
    with monkeypatch.context() as patch:
        patch.setattr(us_universe_update, "save_us_universe", fail_save)
        with pytest.raises(OSError):
            create_update(database_url, clock, client, tmp_path).update_if_due()

    create_update(database_url, clock, client, tmp_path).update_if_due()

    assert len(client.summary_downloads) == 1
    assert len(await read_ranked_symbols(database_url)) == 2
