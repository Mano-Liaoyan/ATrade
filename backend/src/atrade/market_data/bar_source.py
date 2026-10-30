"""Bar sources and the global source order (docs/architecture/market_data.md section 8.7)."""

from datetime import datetime
from enum import StrEnum

import psycopg
from psycopg import sql


class BarSource(StrEnum):
    """Each bar source has its own bar table and its own saved-range table (ADR 0002)."""

    IBKR = "ibkr"
    DATABENTO = "databento"


# The migration writes this order. The code does not rank the bar sources: the source order does.
DEFAULT_SOURCE_ORDER = [BarSource.IBKR, BarSource.DATABENTO]


def bar_table(bar_source: BarSource) -> sql.Identifier:
    return sql.Identifier(f"{bar_source.value}_bar")


def saved_range_table(bar_source: BarSource) -> sql.Identifier:
    return sql.Identifier(f"{bar_source.value}_bar_saved_range")


def check_source_order(source_order: list[BarSource]) -> str | None:
    """Returns why the source order is not valid, or None. A source order holds each bar source exactly 1 time, so the
    bars route always reads the IBKR bars that it saves (docs/architecture/market_data.md section 8.14)."""
    if len(set(source_order)) != len(source_order):
        return "The source order has a bar source 2 times."
    missing_sources = [bar_source.value for bar_source in BarSource if bar_source not in source_order]
    if missing_sources:
        return f"The source order must hold all bar sources. Missing: {', '.join(missing_sources)}."
    return None


async def select_source_order(connection: psycopg.AsyncConnection) -> list[BarSource]:
    """The global source order. Without a row (only an emptied test database), the default order."""
    async with connection.cursor() as cursor:
        await cursor.execute("SELECT bar_sources FROM source_order")
        row = await cursor.fetchone()
    if row is None:
        return list(DEFAULT_SOURCE_ORDER)
    bar_sources: list[str] = row[0]
    return [BarSource(value) for value in bar_sources]


async def update_source_order(
    connection: psycopg.AsyncConnection, source_order: list[BarSource], changed_at_utc: datetime
) -> None:
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            INSERT INTO source_order (id, bar_sources, changed_at_utc)
            VALUES (true, %(bar_sources)s, %(changed_at_utc)s)
            ON CONFLICT (id) DO UPDATE SET
                bar_sources = excluded.bar_sources, changed_at_utc = excluded.changed_at_utc
            """,
            {"bar_sources": [bar_source.value for bar_source in source_order], "changed_at_utc": changed_at_utc},
        )


async def read_source_order(*, database_url: str) -> list[BarSource]:
    """The global source order. Backtests use it unless the backtest form changes it."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await select_source_order(connection)
