"""Quarterly US universe update: at 06:00 ET on the first trading day of the quarter, download the EQUS.SUMMARY bars,
import them, and save the members (docs/architecture/market_data.md section 8.9).

Real PostgreSQL, a fixed clock, and the Databento fake.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from atrade.market_data import UsUniverseUpdate, read_us_universe_members
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
async def test_the_update_runs_only_on_the_first_trading_day_of_the_quarter_and_only_one_time(
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
