"""SQL for the strategy and strategy_version tables. Only the strategy capability reads or writes them."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Final, Literal

import psycopg
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

# The version source (docs/architecture/strategy.md section 9.1.1). A CHECK constraint holds the same values.
VersionSource = Literal["user", "rule_builder"]
VERSION_COLUMNS: Final = "id, strategy_id, version_number, code, code_sha256, created_at_utc, source, rules"


@dataclass(frozen=True)
class StrategyRecord:
    id: int
    name: str
    created_at_utc: datetime


@dataclass(frozen=True)
class StrategyListRow:
    id: int
    name: str
    latest_version_number: int


@dataclass(frozen=True)
class StrategyVersionRecord:
    id: int
    strategy_id: int
    version_number: int
    code: str
    code_sha256: str
    created_at_utc: datetime
    source: VersionSource
    rules: dict[str, Any] | None


@dataclass(frozen=True)
class VersionContent:
    """What a save stores in a new version. Only versions with the source rule_builder have rules."""

    code: str
    source: VersionSource
    rules: dict[str, Any] | None


class DeleteResult(Enum):
    DELETED = "deleted"
    NOT_FOUND = "not_found"
    IN_USE = "in_use"


@dataclass(frozen=True)
class SavedVersion:
    version: StrategyVersionRecord
    is_new_version: bool


def calculate_code_sha256(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


async def insert_strategy(
    connection: psycopg.AsyncConnection, *, name: str, created_at_utc: datetime
) -> StrategyRecord | None:
    """Returns None when a strategy with this name exists."""
    async with connection.cursor(row_factory=class_row(StrategyRecord)) as cursor:
        await cursor.execute(
            """
            INSERT INTO strategy (name, created_at_utc) VALUES (%(name)s, %(created_at_utc)s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id, name, created_at_utc
            """,
            {"name": name, "created_at_utc": created_at_utc},
        )
        return await cursor.fetchone()


async def select_strategies(connection: psycopg.AsyncConnection) -> list[StrategyListRow]:
    async with connection.cursor(row_factory=class_row(StrategyListRow)) as cursor:
        await cursor.execute(
            """
            SELECT strategy.id, strategy.name, max(strategy_version.version_number) AS latest_version_number
            FROM strategy
            JOIN strategy_version ON strategy_version.strategy_id = strategy.id
            GROUP BY strategy.id, strategy.name
            ORDER BY strategy.name
            """
        )
        return await cursor.fetchall()


async def select_strategy(connection: psycopg.AsyncConnection, strategy_id: int) -> StrategyRecord | None:
    async with connection.cursor(row_factory=class_row(StrategyRecord)) as cursor:
        await cursor.execute(
            "SELECT id, name, created_at_utc FROM strategy WHERE id = %(strategy_id)s",
            {"strategy_id": strategy_id},
        )
        return await cursor.fetchone()


async def select_versions(connection: psycopg.AsyncConnection, strategy_id: int) -> list[StrategyVersionRecord]:
    async with connection.cursor(row_factory=class_row(StrategyVersionRecord)) as cursor:
        await cursor.execute(
            f"""
            SELECT {VERSION_COLUMNS}
            FROM strategy_version
            WHERE strategy_id = %(strategy_id)s
            ORDER BY version_number
            """,
            {"strategy_id": strategy_id},
        )
        return await cursor.fetchall()


async def select_version(
    connection: psycopg.AsyncConnection, *, strategy_id: int, version_number: int
) -> StrategyVersionRecord | None:
    async with connection.cursor(row_factory=class_row(StrategyVersionRecord)) as cursor:
        await cursor.execute(
            f"""
            SELECT {VERSION_COLUMNS}
            FROM strategy_version
            WHERE strategy_id = %(strategy_id)s AND version_number = %(version_number)s
            """,
            {"strategy_id": strategy_id, "version_number": version_number},
        )
        return await cursor.fetchone()


async def save_version(
    connection: psycopg.AsyncConnection, *, strategy_id: int, code: str, created_at_utc: datetime
) -> SavedVersion | None:
    """Appends a version when the code differs from the latest version. Returns None when the strategy is missing.

    The caller runs this in a transaction. FOR UPDATE on the strategy row makes two saves of the same
    strategy wait for each other, so they cannot get the same version number.
    """
    locked_cursor = await connection.execute(
        "SELECT id FROM strategy WHERE id = %(strategy_id)s FOR UPDATE", {"strategy_id": strategy_id}
    )
    if await locked_cursor.fetchone() is None:
        return None
    async with connection.cursor(row_factory=class_row(StrategyVersionRecord)) as cursor:
        await cursor.execute(
            f"""
            SELECT {VERSION_COLUMNS}
            FROM strategy_version
            WHERE strategy_id = %(strategy_id)s
            ORDER BY version_number DESC
            LIMIT 1
            """,
            {"strategy_id": strategy_id},
        )
        latest_version = await cursor.fetchone()
    code_sha256 = calculate_code_sha256(code)
    if latest_version is not None and latest_version.code_sha256 == code_sha256:
        return SavedVersion(version=latest_version, is_new_version=False)
    next_version_number = 1 if latest_version is None else latest_version.version_number + 1
    new_version = await insert_version(
        connection,
        strategy_id=strategy_id,
        version_number=next_version_number,
        content=VersionContent(code=code, source="user", rules=None),
        created_at_utc=created_at_utc,
    )
    return SavedVersion(version=new_version, is_new_version=True)


async def insert_version(
    connection: psycopg.AsyncConnection,
    *,
    strategy_id: int,
    version_number: int,
    content: VersionContent,
    created_at_utc: datetime,
) -> StrategyVersionRecord:
    async with connection.cursor(row_factory=class_row(StrategyVersionRecord)) as cursor:
        await cursor.execute(
            f"""
            INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc, source, rules)
            VALUES (
                %(strategy_id)s, %(version_number)s, %(code)s, %(code_sha256)s, %(created_at_utc)s, %(source)s, %(rules)s
            )
            RETURNING {VERSION_COLUMNS}
            """,
            {
                "strategy_id": strategy_id,
                "version_number": version_number,
                "code": content.code,
                "code_sha256": calculate_code_sha256(content.code),
                "created_at_utc": created_at_utc,
                "source": content.source,
                "rules": None if content.rules is None else Jsonb(content.rules),
            },
        )
        inserted_version = await cursor.fetchone()
    if inserted_version is None:
        message = "INSERT ... RETURNING returned no row."
        raise RuntimeError(message)
    return inserted_version


async def delete_strategy(connection: psycopg.AsyncConnection, strategy_id: int) -> DeleteResult:
    """Deletes the strategy and its versions, unless a backtest or forward test uses one of the versions.

    The tables of backtests and forward tests reference strategy_version with a foreign key. PostgreSQL
    refuses the delete when a reference exists. This way the strategy capability does not read the tables
    of other capabilities (docs/architecture.md section 6.3).
    """
    try:
        async with connection.transaction():
            cursor = await connection.execute(
                "DELETE FROM strategy WHERE id = %(strategy_id)s", {"strategy_id": strategy_id}
            )
    except psycopg.errors.ForeignKeyViolation:
        # readability-exception: PostgreSQL reports a foreign key reference only as an error.
        return DeleteResult.IN_USE
    if cursor.rowcount == 0:
        return DeleteResult.NOT_FOUND
    return DeleteResult.DELETED
