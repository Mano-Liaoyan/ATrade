"""The backtest timeout and concurrency. PostgreSQL stores them in the backtest_limits table. The UI changes them.

The table has at most one row. Without a row, the defaults apply (docs/architecture/backtest.md section 10.1).
"""

from dataclasses import dataclass

import psycopg
from psycopg.rows import class_row

DEFAULT_TIMEOUT_SECONDS = 120 * 60
DEFAULT_CONCURRENCY = 1
MAX_TIMEOUT_SECONDS = 7 * 24 * 60 * 60
MAX_CONCURRENCY = 16


@dataclass(frozen=True)
class BacktestLimits:
    timeout_seconds: int
    concurrency: int


DEFAULT_BACKTEST_LIMITS = BacktestLimits(timeout_seconds=DEFAULT_TIMEOUT_SECONDS, concurrency=DEFAULT_CONCURRENCY)


async def read_backtest_limits(connection: psycopg.AsyncConnection) -> BacktestLimits:
    async with connection.cursor(row_factory=class_row(BacktestLimits)) as cursor:
        await cursor.execute("SELECT timeout_seconds, concurrency FROM backtest_limits")
        saved_limits = await cursor.fetchone()
    if saved_limits is None:
        return DEFAULT_BACKTEST_LIMITS
    return saved_limits


async def save_backtest_limits(connection: psycopg.AsyncConnection, limits: BacktestLimits) -> None:
    await connection.execute(
        """
        INSERT INTO backtest_limits (timeout_seconds, concurrency) VALUES (%(timeout_seconds)s, %(concurrency)s)
        ON CONFLICT (single_row) DO UPDATE
        SET timeout_seconds = EXCLUDED.timeout_seconds, concurrency = EXCLUDED.concurrency
        """,
        {"timeout_seconds": limits.timeout_seconds, "concurrency": limits.concurrency},
    )
