"""SQL for the assistant_prompt_version table. Only the assistant capability reads or writes it.

A prompt version does not change after it is saved: a trigger refuses each UPDATE. The version numbers are 1, 2, 3, …
An exclusive lock of the table in the transaction keeps 2 saves at the same time from taking the same number.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Final

import psycopg
from psycopg.rows import class_row

PROMPT_VERSION_COLUMNS: Final = "id, version_number, text, created_at_utc"


@dataclass(frozen=True)
class PromptVersionRecord:
    id: int
    version_number: int
    text: str
    created_at_utc: datetime


async def lock_prompt_versions(connection: psycopg.AsyncConnection) -> None:
    """Call in a transaction. Other saves wait until the transaction ends. Reads do not wait."""
    await connection.execute("LOCK TABLE assistant_prompt_version IN EXCLUSIVE MODE")


async def insert_prompt_version(
    connection: psycopg.AsyncConnection, *, text: str, created_at_utc: datetime
) -> PromptVersionRecord:
    """Saves the text as the next version number. Call after lock_prompt_versions in the same transaction."""
    async with connection.cursor(row_factory=class_row(PromptVersionRecord)) as cursor:
        await cursor.execute(
            f"""
            INSERT INTO assistant_prompt_version (version_number, text, created_at_utc)
            SELECT COALESCE(MAX(version_number), 0) + 1, %(text)s, %(created_at_utc)s FROM assistant_prompt_version
            RETURNING {PROMPT_VERSION_COLUMNS}
            """,
            {"text": text, "created_at_utc": created_at_utc},
        )
        record = await cursor.fetchone()
    if record is None:
        message = "The INSERT of a prompt version returned no row."
        raise RuntimeError(message)
    return record


async def select_prompt_versions(connection: psycopg.AsyncConnection) -> list[PromptVersionRecord]:
    """All prompt versions, the newest first."""
    async with connection.cursor(row_factory=class_row(PromptVersionRecord)) as cursor:
        await cursor.execute(
            f"SELECT {PROMPT_VERSION_COLUMNS} FROM assistant_prompt_version ORDER BY version_number DESC"
        )
        return await cursor.fetchall()


async def select_or_insert_latest_version(
    connection: psycopg.AsyncConnection, *, default_text: str, created_at_utc: datetime
) -> PromptVersionRecord:
    """The latest prompt version. When no version exists, saves the default text as version 1 first.

    Call in a transaction.
    """
    await lock_prompt_versions(connection)
    async with connection.cursor(row_factory=class_row(PromptVersionRecord)) as cursor:
        await cursor.execute(
            f"SELECT {PROMPT_VERSION_COLUMNS} FROM assistant_prompt_version ORDER BY version_number DESC LIMIT 1"
        )
        latest = await cursor.fetchone()
    if latest is not None:
        return latest
    return await insert_prompt_version(connection, text=default_text, created_at_utc=created_at_utc)
