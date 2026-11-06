"""A database time is the same time in UTC for each session time zone (docs/architecture.md section 6.1)."""

from datetime import UTC, date, datetime

import psycopg
import pytest

STORED_UTC = datetime(2026, 3, 31, 23, 30, tzinfo=UTC)
READ_TIME = "SELECT %s::timestamptz"


def test_a_sync_read_gives_utc_in_a_session_with_another_time_zone(database_url: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("SET TIME ZONE 'Europe/Amsterdam'")
        row = connection.execute(READ_TIME, [STORED_UTC]).fetchone()

    assert row is not None
    assert row[0].tzinfo == UTC
    assert row[0].date() == date(2026, 3, 31)


@pytest.mark.anyio
async def test_an_async_binary_read_gives_utc_in_a_session_with_another_time_zone(database_url: str) -> None:
    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as connection:
        await connection.execute("SET TIME ZONE 'Europe/Amsterdam'")
        cursor = await connection.execute(READ_TIME, [STORED_UTC], binary=True)
        row = await cursor.fetchone()

    assert row is not None
    assert row[0].tzinfo == UTC
    assert row[0].date() == date(2026, 3, 31)
