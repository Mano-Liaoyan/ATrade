"""SQL for the screen tables. Only the screen capability reads or writes them (docs/architecture/screen.md 24.4)."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import psycopg
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

# The count of recent screen results that a read of a screen gives (section 24.7).
RECENT_SCREEN_RESULT_COUNT = 10


@dataclass(frozen=True)
class ScreenRecord:
    id: int
    name: str
    market: str
    definition: dict[str, Any]
    kept: bool
    assistant_conversation_id: int | None
    created_at_utc: datetime
    updated_at_utc: datetime


@dataclass(frozen=True)
class ScreenResultSummaryRecord:
    id: int
    run_at_utc: datetime
    result_count: int


class NameInUseError(Exception):
    """Another screen has the name."""


async def insert_screen(
    connection: psycopg.AsyncConnection, *, name: str, market: str, definition: object, now_utc: datetime
) -> ScreenRecord:
    """A screen of the user: kept, with no conversation. Raises NameInUseError."""
    async with connection.cursor(row_factory=class_row(ScreenRecord)) as cursor:
        await cursor.execute(
            """
            INSERT INTO screen (name, market, definition, kept, created_at_utc, updated_at_utc)
            VALUES (%(name)s, %(market)s, %(definition)s, true, %(now)s, %(now)s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id, name, market, definition, kept, assistant_conversation_id, created_at_utc, updated_at_utc
            """,
            {"name": name, "market": market, "definition": Jsonb(definition), "now": now_utc},
        )
        record = await cursor.fetchone()
    if record is None:
        raise NameInUseError
    return record


async def update_screen(
    connection: psycopg.AsyncConnection, *, screen_id: int, name: str, definition: object, now_utc: datetime
) -> ScreenRecord | None:
    """Returns None when the screen does not exist. Raises NameInUseError."""
    try:
        async with connection.cursor(row_factory=class_row(ScreenRecord)) as cursor:
            await cursor.execute(
                """
                UPDATE screen SET name = %(name)s, definition = %(definition)s, updated_at_utc = %(now)s
                WHERE id = %(id)s
                RETURNING id, name, market, definition, kept, assistant_conversation_id, created_at_utc, updated_at_utc
                """,
                {"id": screen_id, "name": name, "definition": Jsonb(definition), "now": now_utc},
            )
            return await cursor.fetchone()
    except psycopg.errors.UniqueViolation as error:
        raise NameInUseError from error


async def select_screen(connection: psycopg.AsyncConnection, screen_id: int) -> ScreenRecord | None:
    async with connection.cursor(row_factory=class_row(ScreenRecord)) as cursor:
        await cursor.execute(
            """
            SELECT id, name, market, definition, kept, assistant_conversation_id, created_at_utc, updated_at_utc
            FROM screen WHERE id = %(id)s
            """,
            {"id": screen_id},
        )
        return await cursor.fetchone()


async def select_screens(connection: psycopg.AsyncConnection) -> list[ScreenRecord]:
    """The last changed screen first."""
    async with connection.cursor(row_factory=class_row(ScreenRecord)) as cursor:
        await cursor.execute(
            """
            SELECT id, name, market, definition, kept, assistant_conversation_id, created_at_utc, updated_at_utc
            FROM screen ORDER BY updated_at_utc DESC, id DESC
            """
        )
        return await cursor.fetchall()


async def select_recent_screen_results(
    connection: psycopg.AsyncConnection, screen_id: int
) -> list[ScreenResultSummaryRecord]:
    """The last run first."""
    async with connection.cursor(row_factory=class_row(ScreenResultSummaryRecord)) as cursor:
        await cursor.execute(
            """
            SELECT id, run_at_utc, result_count FROM screen_result
            WHERE screen_id = %(id)s
            ORDER BY run_at_utc DESC, id DESC
            LIMIT %(limit)s
            """,
            {"id": screen_id, "limit": RECENT_SCREEN_RESULT_COUNT},
        )
        return await cursor.fetchall()


async def delete_screen(connection: psycopg.AsyncConnection, screen_id: int) -> bool:
    """Returns False when the screen does not exist. PostgreSQL also deletes its screen results."""
    cursor = await connection.execute("DELETE FROM screen WHERE id = %(id)s", {"id": screen_id})
    return cursor.rowcount > 0


@dataclass(frozen=True)
class NewScreenResult:
    screen_id: int
    run_at_utc: datetime
    definition: object
    market: str
    daily_bars_date: date | None
    run_seconds: float
    start_count: int
    after_filters_count: int
    after_indicator_conditions_count: int
    # (symbol, exchange, currency, values JSON) in the order of the result. Position 1 is the first.
    rows: list[tuple[str, str, str, dict[str, Any]]]
    # (symbol, exchange, currency, reason).
    exclusions: list[tuple[str, str, str, str]]


@dataclass(frozen=True)
class ScreenResultRecord:
    id: int
    screen_id: int
    run_at_utc: datetime
    definition: dict[str, Any]
    market: str
    daily_bars_date: date | None
    run_seconds: float
    start_count: int
    after_filters_count: int
    after_indicator_conditions_count: int
    result_count: int
    assistant_conversation_id: int | None


@dataclass(frozen=True)
class ScreenResultRowRecord:
    position: int
    symbol: str
    exchange: str
    currency: str
    values: dict[str, Any]


@dataclass(frozen=True)
class ScreenResultExclusionRecord:
    symbol: str
    exchange: str
    currency: str
    reason: str


@dataclass(frozen=True)
class ExclusionCountRecord:
    reason: str
    count: int


async def insert_screen_result(connection: psycopg.AsyncConnection, result: NewScreenResult) -> int:
    """Saves the screen result, its rows, and its excluded list. The caller commits them in one transaction."""
    cursor = await connection.execute(
        """
        INSERT INTO screen_result (
            screen_id, run_at_utc, definition, market, daily_bars_date, run_seconds,
            start_count, after_filters_count, after_indicator_conditions_count, result_count
        )
        VALUES (
            %(screen_id)s, %(run_at_utc)s, %(definition)s, %(market)s, %(daily_bars_date)s, %(run_seconds)s,
            %(start_count)s, %(after_filters_count)s, %(after_indicator_conditions_count)s, %(result_count)s
        )
        RETURNING id
        """,
        {
            "screen_id": result.screen_id,
            "run_at_utc": result.run_at_utc,
            "definition": Jsonb(result.definition),
            "market": result.market,
            "daily_bars_date": result.daily_bars_date,
            "run_seconds": result.run_seconds,
            "start_count": result.start_count,
            "after_filters_count": result.after_filters_count,
            "after_indicator_conditions_count": result.after_indicator_conditions_count,
            "result_count": len(result.rows),
        },
    )
    row = await cursor.fetchone()
    if row is None:
        raise RuntimeError("INSERT ... RETURNING gave no row.")
    screen_result_id = int(row[0])
    async with connection.cursor() as cursor:
        await cursor.executemany(
            """
            INSERT INTO screen_result_row (screen_result_id, position, symbol, exchange, currency, values)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (screen_result_id, position, symbol, exchange, currency, Jsonb(values))
                for position, (symbol, exchange, currency, values) in enumerate(result.rows, start=1)
            ],
        )
        await cursor.executemany(
            """
            INSERT INTO screen_result_exclusion (screen_result_id, symbol, exchange, currency, reason)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [(screen_result_id, *exclusion) for exclusion in result.exclusions],
        )
    return screen_result_id


async def select_screen_result(connection: psycopg.AsyncConnection, screen_result_id: int) -> ScreenResultRecord | None:
    async with connection.cursor(row_factory=class_row(ScreenResultRecord)) as cursor:
        await cursor.execute(
            """
            SELECT id, screen_id, run_at_utc, definition, market, daily_bars_date, run_seconds, start_count,
                after_filters_count, after_indicator_conditions_count, result_count, assistant_conversation_id
            FROM screen_result WHERE id = %(id)s
            """,
            {"id": screen_result_id},
        )
        return await cursor.fetchone()


async def select_screen_result_rows(
    connection: psycopg.AsyncConnection, screen_result_id: int, *, offset: int, limit: int
) -> list[ScreenResultRowRecord]:
    async with connection.cursor(row_factory=class_row(ScreenResultRowRecord)) as cursor:
        await cursor.execute(
            """
            SELECT position, symbol, exchange, currency, values FROM screen_result_row
            WHERE screen_result_id = %(id)s
            ORDER BY position
            OFFSET %(offset)s LIMIT %(limit)s
            """,
            {"id": screen_result_id, "offset": offset, "limit": limit},
        )
        return await cursor.fetchall()


async def select_screen_result_exclusions(
    connection: psycopg.AsyncConnection, screen_result_id: int
) -> list[ScreenResultExclusionRecord]:
    """By symbol."""
    async with connection.cursor(row_factory=class_row(ScreenResultExclusionRecord)) as cursor:
        await cursor.execute(
            """
            SELECT symbol, exchange, currency, reason FROM screen_result_exclusion
            WHERE screen_result_id = %(id)s
            ORDER BY symbol COLLATE "C", exchange COLLATE "C", currency COLLATE "C"
            """,
            {"id": screen_result_id},
        )
        return await cursor.fetchall()


async def select_exclusion_counts(
    connection: psycopg.AsyncConnection, screen_result_id: int
) -> list[ExclusionCountRecord]:
    """The count of each exclusion reason, the most frequent reason first."""
    async with connection.cursor(row_factory=class_row(ExclusionCountRecord)) as cursor:
        await cursor.execute(
            """
            SELECT reason, count(*)::integer AS count FROM screen_result_exclusion
            WHERE screen_result_id = %(id)s
            GROUP BY reason
            ORDER BY count DESC, reason COLLATE "C"
            """,
            {"id": screen_result_id},
        )
        return await cursor.fetchall()
