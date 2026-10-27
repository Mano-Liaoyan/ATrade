"""Reads one strategy version by its ID, for the capabilities that run strategy versions (backtest, forward test)."""

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
            WHERE strategy_version.id = %(strategy_version_id)s
            """,
            {"strategy_version_id": strategy_version_id},
        )
        return await cursor.fetchone()
