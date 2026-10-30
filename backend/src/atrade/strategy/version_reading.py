"""Reads strategy versions for the capabilities that run them (backtest, forward test), and the outline of a
strategy for the start context of an AI assistant conversation (app/)."""

from dataclasses import dataclass

import psycopg
from psycopg.rows import class_row


@dataclass(frozen=True)
class StrategyVersion:
    """A saved strategy version with the name of its strategy, for labels like "strategy name v3"."""

    id: int
    strategy_id: int
    strategy_name: str
    version_number: int
    code: str


async def read_strategy_version(*, database_url: str, strategy_version_id: int) -> StrategyVersion | None:
    versions = await read_strategy_versions(database_url=database_url, strategy_version_ids=[strategy_version_id])
    return versions.get(strategy_version_id)


async def read_strategy_versions(*, database_url: str, strategy_version_ids: list[int]) -> dict[int, StrategyVersion]:
    """The strategy versions by ID, with one connection and one query. A missing ID is not in the result."""
    async with (
        await psycopg.AsyncConnection.connect(database_url) as connection,
        connection.cursor(row_factory=class_row(StrategyVersion)) as cursor,
    ):
        await cursor.execute(
            """
            SELECT strategy_version.id, strategy_version.strategy_id, strategy.name AS strategy_name,
                strategy_version.version_number, strategy_version.code
            FROM strategy_version
            JOIN strategy ON strategy.id = strategy_version.strategy_id
            WHERE strategy_version.id = ANY(%(strategy_version_ids)s)
            """,
            {"strategy_version_ids": strategy_version_ids},
        )
        return {version.id: version for version in await cursor.fetchall()}


@dataclass(frozen=True)
class StrategyOutline:
    """The name of a strategy and the IDs of its versions."""

    id: int
    name: str
    version_ids: list[int]


async def read_strategy_outline(*, database_url: str, strategy_id: int) -> StrategyOutline | None:
    """Returns None when the strategy does not exist."""
    async with (
        await psycopg.AsyncConnection.connect(database_url) as connection,
        connection.cursor(row_factory=class_row(StrategyOutline)) as cursor,
    ):
        await cursor.execute(
            """
            SELECT strategy.id, strategy.name,
                ARRAY(SELECT strategy_version.id FROM strategy_version WHERE strategy_version.strategy_id = strategy.id)
                    AS version_ids
            FROM strategy
            WHERE strategy.id = %(strategy_id)s
            """,
            {"strategy_id": strategy_id},
        )
        return await cursor.fetchone()
