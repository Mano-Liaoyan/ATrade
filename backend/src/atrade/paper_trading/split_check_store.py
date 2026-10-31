"""SQL for the split_check table and the `split_adjustment` rows of the owner ledger
(docs/architecture/paper_trading.md section 11.11). Only paper_trading reads or writes them."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

import psycopg
from psycopg.rows import class_row

from atrade.foundation.instrument import Instrument
from atrade.paper_trading.stock_split_rules import SplitAdjustment, SplitCheckEvidence

type SplitCheckStatus = Literal["needed", "applied", "kept"]


@dataclass(frozen=True)
class SplitCheck:
    id: int
    # None for a `position_only` check until "Apply split" writes the stock split.
    stock_split_id: int | None
    account: str
    symbol: str
    exchange: str
    currency: str
    ex_date_utc: datetime
    detected_ratio: Decimal
    evidence: SplitCheckEvidence
    account_quantity_before: Decimal
    account_quantity_after: Decimal
    status: SplitCheckStatus
    restarted_at_utc: datetime | None

    @property
    def instrument(self) -> Instrument:
        return Instrument(symbol=self.symbol, exchange=self.exchange, currency=self.currency)


@dataclass(frozen=True)
class NewSplitCheck:
    account: str
    instrument: Instrument
    stock_split_id: int | None
    ex_date_utc: datetime
    detected_ratio: Decimal
    evidence: SplitCheckEvidence
    account_quantity_before: Decimal
    account_quantity_after: Decimal


SPLIT_CHECK_COLUMNS = """
    id, stock_split_id, account, symbol, exchange, currency, ex_date_utc, detected_ratio, evidence,
    account_quantity_before, account_quantity_after, status, restarted_at_utc
"""


async def select_split_checks(
    connection: psycopg.AsyncConnection, *, account: str | None, status: SplitCheckStatus | None
) -> list[SplitCheck]:
    """The split checks of the account (all accounts for None) with the status (all for None), oldest first."""
    async with connection.cursor(row_factory=class_row(SplitCheck)) as cursor:
        await cursor.execute(
            f"""
            SELECT {SPLIT_CHECK_COLUMNS} FROM split_check
            WHERE (%(account)s::text IS NULL OR account = %(account)s)
                AND (%(status)s::text IS NULL OR status = %(status)s)
            ORDER BY id
            """,
            {"account": account, "status": status},
        )
        return await cursor.fetchall()


async def select_split_check(connection: psycopg.AsyncConnection, split_check_id: int) -> SplitCheck | None:
    """Locks the row until the end of the transaction, so 2 clicks resolve the check once."""
    async with connection.cursor(row_factory=class_row(SplitCheck)) as cursor:
        await cursor.execute(
            f"SELECT {SPLIT_CHECK_COLUMNS} FROM split_check WHERE id = %(id)s FOR UPDATE", {"id": split_check_id}
        )
        return await cursor.fetchone()


async def insert_split_check(
    connection: psycopg.AsyncConnection, check: NewSplitCheck, created_at_utc: datetime
) -> None:
    """An instrument that is in the state already keeps its first check (ON CONFLICT DO NOTHING)."""
    await connection.execute(
        """
        INSERT INTO split_check (
            stock_split_id, account, symbol, exchange, currency, ex_date_utc, detected_ratio, evidence,
            account_quantity_before, account_quantity_after, status, created_at_utc
        ) VALUES (
            %(stock_split_id)s, %(account)s, %(symbol)s, %(exchange)s, %(currency)s, %(ex_date_utc)s,
            %(detected_ratio)s, %(evidence)s, %(before)s, %(after)s, 'needed', %(created_at_utc)s
        )
        ON CONFLICT (account, symbol, exchange, currency) WHERE status = 'needed' DO NOTHING
        """,
        {
            "stock_split_id": check.stock_split_id,
            "account": check.account,
            "symbol": check.instrument.symbol,
            "exchange": check.instrument.exchange,
            "currency": check.instrument.currency,
            "ex_date_utc": check.ex_date_utc,
            "detected_ratio": check.detected_ratio,
            "evidence": check.evidence,
            "before": check.account_quantity_before,
            "after": check.account_quantity_after,
            "created_at_utc": created_at_utc,
        },
    )


async def write_resolution(
    connection: psycopg.AsyncConnection,
    *,
    split_check_id: int,
    status: Literal["applied", "kept"],
    stock_split_id: int | None,
    resolved_at_utc: datetime,
) -> None:
    await connection.execute(
        """
        UPDATE split_check SET status = %(status)s, resolved_at_utc = %(resolved_at_utc)s,
            stock_split_id = COALESCE(%(stock_split_id)s, stock_split_id)
        WHERE id = %(id)s
        """,
        {
            "id": split_check_id,
            "status": status,
            "stock_split_id": stock_split_id,
            "resolved_at_utc": resolved_at_utc,
        },
    )


async def write_restarted(
    connection: psycopg.AsyncConnection, *, split_check_id: int, restarted_at_utc: datetime
) -> None:
    await connection.execute(
        "UPDATE split_check SET restarted_at_utc = %(restarted_at_utc)s WHERE id = %(id)s",
        {"id": split_check_id, "restarted_at_utc": restarted_at_utc},
    )


async def has_stock_split_check(connection: psycopg.AsyncConnection, stock_split_id: int) -> bool:
    cursor = await connection.execute(
        "SELECT 1 FROM split_check WHERE stock_split_id = %(id)s LIMIT 1", {"id": stock_split_id}
    )
    return await cursor.fetchone() is not None


async def insert_split_adjustments(  # noqa: PLR0913 readability-exception: one keyword argument per part of the rows.
    connection: psycopg.AsyncConnection,
    *,
    account: str,
    instrument: Instrument,
    stock_split_id: int,
    adjustments: list[tuple[SplitAdjustment, Decimal]],
    time_utc: datetime,
) -> None:
    """One `split_adjustment` row for each adjustment, with its cash in lieu in USD. The caller commits."""
    async with connection.cursor() as cursor:
        await cursor.executemany(
            """
            INSERT INTO owner_ledger_entry (
                owner_kind, forward_test_id, entry_kind, time_utc, account, symbol, exchange, currency,
                quantity_change, price, cash_change, stock_split_id
            ) VALUES (%s, %s, 'split_adjustment', %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    adjustment.owner.kind,
                    adjustment.owner.forward_test_id,
                    time_utc,
                    account,
                    instrument.symbol,
                    instrument.exchange,
                    instrument.currency,
                    adjustment.quantity_change,
                    adjustment.price,
                    cash_in_lieu_usd,
                    stock_split_id,
                )
                for adjustment, cash_in_lieu_usd in adjustments
            ],
        )


async def select_split_forward_test_ids(connection: psycopg.AsyncConnection, stock_split_id: int) -> list[int]:
    """The forward tests with a split adjustment of the stock split."""
    cursor = await connection.execute(
        """
        SELECT DISTINCT forward_test_id FROM owner_ledger_entry
        WHERE stock_split_id = %(id)s AND forward_test_id IS NOT NULL ORDER BY forward_test_id
        """,
        {"id": stock_split_id},
    )
    return [int(row[0]) for row in await cursor.fetchall()]


async def select_holding_forward_test_ids(connection: psycopg.AsyncConnection, split_check: SplitCheck) -> list[int]:
    """The forward tests with an owner position on the instrument of the split check."""
    cursor = await connection.execute(
        """
        SELECT forward_test_id FROM owner_ledger_entry
        WHERE account = %(account)s AND symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
            AND forward_test_id IS NOT NULL
        GROUP BY forward_test_id HAVING sum(quantity_change) > 0
        ORDER BY forward_test_id
        """,
        {
            "account": split_check.account,
            "symbol": split_check.symbol,
            "exchange": split_check.exchange,
            "currency": split_check.currency,
        },
    )
    return [int(row[0]) for row in await cursor.fetchall()]
