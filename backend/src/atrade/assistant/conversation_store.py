"""SQL for the assistant_conversation table. Only the assistant capability reads or writes it."""

from dataclasses import dataclass
from datetime import datetime
from typing import Final, Literal

import psycopg
from psycopg.rows import class_row

type TitleState = Literal["new", "generating", "generated", "not_generated", "renamed"]

CONVERSATION_COLUMNS: Final = (
    "id, strategy_id, title, title_state, created_at_utc, last_provider, last_model, last_credential_name"
)


@dataclass(frozen=True)
class ConversationRecord:
    id: int
    strategy_id: int
    title: str
    title_state: TitleState
    created_at_utc: datetime
    last_provider: str | None
    last_model: str | None
    last_credential_name: str | None


async def insert_conversation(
    connection: psycopg.AsyncConnection, *, strategy_id: int, title: str, created_at_utc: datetime
) -> ConversationRecord | None:
    """Returns None when the strategy does not exist."""
    try:
        async with connection.transaction(), connection.cursor(row_factory=class_row(ConversationRecord)) as cursor:
            await cursor.execute(
                f"""
                INSERT INTO assistant_conversation (strategy_id, title, created_at_utc)
                VALUES (%(strategy_id)s, %(title)s, %(created_at_utc)s)
                RETURNING {CONVERSATION_COLUMNS}
                """,
                {"strategy_id": strategy_id, "title": title, "created_at_utc": created_at_utc},
            )
            return await cursor.fetchone()
    except psycopg.errors.ForeignKeyViolation:
        # readability-exception: PostgreSQL reports a missing strategy only as an error.
        return None


async def select_conversations(connection: psycopg.AsyncConnection, strategy_id: int) -> list[ConversationRecord]:
    """The conversations of one strategy, the newest first."""
    async with connection.cursor(row_factory=class_row(ConversationRecord)) as cursor:
        await cursor.execute(
            f"SELECT {CONVERSATION_COLUMNS} FROM assistant_conversation WHERE strategy_id = %(strategy_id)s "
            "ORDER BY created_at_utc DESC, id DESC",
            {"strategy_id": strategy_id},
        )
        return await cursor.fetchall()


async def select_conversation(connection: psycopg.AsyncConnection, conversation_id: int) -> ConversationRecord | None:
    async with connection.cursor(row_factory=class_row(ConversationRecord)) as cursor:
        await cursor.execute(
            f"SELECT {CONVERSATION_COLUMNS} FROM assistant_conversation WHERE id = %(id)s",
            {"id": conversation_id},
        )
        return await cursor.fetchone()


async def rename_conversation(
    connection: psycopg.AsyncConnection, conversation_id: int, title: str
) -> ConversationRecord | None:
    """Sets the title of the user. ATrade never changes it again. Returns None when the conversation does not exist."""
    async with connection.cursor(row_factory=class_row(ConversationRecord)) as cursor:
        await cursor.execute(
            f"""
            UPDATE assistant_conversation SET title = %(title)s, title_state = 'renamed' WHERE id = %(id)s
            RETURNING {CONVERSATION_COLUMNS}
            """,
            {"id": conversation_id, "title": title},
        )
        return await cursor.fetchone()


async def delete_conversation(connection: psycopg.AsyncConnection, conversation_id: int) -> bool:
    """Returns False when no conversation has this ID."""
    cursor = await connection.execute("DELETE FROM assistant_conversation WHERE id = %(id)s", {"id": conversation_id})
    return cursor.rowcount > 0


async def save_last_model(
    connection: psycopg.AsyncConnection, conversation_id: int, *, provider: str, model: str, credential_name: str
) -> None:
    await connection.execute(
        """
        UPDATE assistant_conversation
        SET last_provider = %(provider)s, last_model = %(model)s, last_credential_name = %(credential_name)s
        WHERE id = %(id)s
        """,
        {"id": conversation_id, "provider": provider, "model": model, "credential_name": credential_name},
    )


async def claim_title_generation(connection: psycopg.AsyncConnection, conversation_id: int) -> bool:
    """Moves the title state from new to generating. False when the title was generated, tried, or renamed before."""
    cursor = await connection.execute(
        "UPDATE assistant_conversation SET title_state = 'generating' WHERE id = %(id)s AND title_state = 'new'",
        {"id": conversation_id},
    )
    return cursor.rowcount > 0


async def end_title_generation(connection: psycopg.AsyncConnection, conversation_id: int, title: str | None) -> None:
    """Saves the generated title, or marks the generation as failed (title None).

    A rename during the generation wins: the update changes only a conversation in the state generating.
    """
    await connection.execute(
        """
        UPDATE assistant_conversation
        SET title = COALESCE(%(title)s, title),
            title_state = CASE WHEN %(title)s::text IS NULL THEN 'not_generated' ELSE 'generated' END
        WHERE id = %(id)s AND title_state = 'generating'
        """,
        {"id": conversation_id, "title": title},
    )
