"""Reads one strategy version by its ID, for the capabilities that run strategy versions (backtest, forward test)."""

from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

from atrade.strategy.rules_code import find_warm_up_bar_count
from atrade.strategy.strategy_rules import StrategyRules


@dataclass(frozen=True)
class StrategyVersion:
    """A saved strategy version with the name of its strategy, for labels like "strategy name v3"."""

    id: int
    strategy_id: int
    strategy_name: str
    version_number: int
    code: str
    # The bars that the longest indicator of the rules needs (#164). None for a version without rules or without
    # an indicator: the backtest and the forward test then use the default look-back length.
    warm_up_bar_count: int | None = None


def to_strategy_version(row: dict[str, Any]) -> StrategyVersion:
    rules = row["rules"]
    return StrategyVersion(
        id=row["id"],
        strategy_id=row["strategy_id"],
        strategy_name=row["strategy_name"],
        version_number=row["version_number"],
        code=row["code"],
        warm_up_bar_count=None if rules is None else find_warm_up_bar_count(StrategyRules.model_validate(rules)),
    )


async def read_strategy_version(*, database_url: str, strategy_version_id: int) -> StrategyVersion | None:
    versions = await read_strategy_versions(database_url=database_url, strategy_version_ids=[strategy_version_id])
    return versions.get(strategy_version_id)


async def read_strategy_versions(*, database_url: str, strategy_version_ids: list[int]) -> dict[int, StrategyVersion]:
    """The strategy versions by ID, with one connection and one query. A missing ID is not in the result."""
    async with (
        await psycopg.AsyncConnection.connect(database_url) as connection,
        connection.cursor(row_factory=dict_row) as cursor,
    ):
        await cursor.execute(
            """
            SELECT strategy_version.id, strategy_version.strategy_id, strategy.name AS strategy_name,
                strategy_version.version_number, strategy_version.code, strategy_version.rules
            FROM strategy_version
            JOIN strategy ON strategy.id = strategy_version.strategy_id
            WHERE strategy_version.id = ANY(%(strategy_version_ids)s)
            """,
            {"strategy_version_ids": strategy_version_ids},
        )
        return {version.id: version for version in map(to_strategy_version, await cursor.fetchall())}
