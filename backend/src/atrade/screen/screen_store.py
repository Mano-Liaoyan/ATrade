"""SQL for the screen tables. Only the screen capability reads or writes them (docs/architecture/screen.md 24.4)."""

from dataclasses import dataclass
from datetime import datetime
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
