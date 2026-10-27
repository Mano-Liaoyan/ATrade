"""SQL for the forward_test table. Only the forward_test capability reads or writes it (docs/architecture.md section 12).

The Web process inserts a row and writes only desired_state. The worker writes status and client_id.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final, Literal

import psycopg
from psycopg.rows import class_row

from atrade.foundation.bar import BarPeriod
from atrade.foundation.instrument import Instrument

type DesiredState = Literal["running", "stopped"]
type ForwardTestStatus = Literal["starting", "running", "stopping", "stopped", "stop_failed", "failed"]

NO_FREE_CLIENT_ID_MESSAGE = "limit of running forward tests reached"


@dataclass(frozen=True)
class ForwardTestRequest:
    strategy_version_id: int
    instrument: Instrument
    bar_period: BarPeriod


@dataclass(frozen=True)
class ForwardTestRow:
    id: int
    strategy_version_id: int
    symbol: str
    exchange: str
    currency: str
    bar_period: str
    desired_state: DesiredState
    status: ForwardTestStatus
    client_id: int | None
    start_balance_usd: Decimal | None
    error_message: str | None
    created_at_utc: datetime
    stopped_at_utc: datetime | None


@dataclass(frozen=True)
class StartRefusal:
    """Why the start was refused. `forward_test_id` is the forward test that already runs on the instrument."""

    reason: Literal["no_free_client_id", "instrument_taken"]
    forward_test_id: int | None


FORWARD_TEST_COLUMNS: Final = """
    id, strategy_version_id, symbol, exchange, currency, bar_period, desired_state, status, client_id,
    start_balance_usd, error_message, created_at_utc, stopped_at_utc
"""


def read_instrument(row: ForwardTestRow) -> Instrument:
    return Instrument(symbol=row.symbol, exchange=row.exchange, currency=row.currency)


async def select_forward_test_on_instrument(
    connection: psycopg.AsyncConnection, instrument: Instrument
) -> ForwardTestRow | None:
    """The forward test that holds a client ID on the instrument. It can have open orders and a position there."""
    async with connection.cursor(row_factory=class_row(ForwardTestRow)) as cursor:
        await cursor.execute(
            f"""
            SELECT {FORWARD_TEST_COLUMNS} FROM forward_test
            WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND client_id IS NOT NULL
            """,
            {"symbol": instrument.symbol, "exchange": instrument.exchange},
        )
        return await cursor.fetchone()


async def select_taken_client_ids(connection: psycopg.AsyncConnection) -> set[int]:
    cursor = await connection.execute("SELECT client_id FROM forward_test WHERE client_id IS NOT NULL")
    return {int(row[0]) for row in await cursor.fetchall()}


def find_lowest_free_client_id(client_ids: range, taken_client_ids: set[int]) -> int | None:
    for client_id in client_ids:
        if client_id not in taken_client_ids:
            return client_id
    return None


async def insert_forward_test(
    connection: psycopg.AsyncConnection, *, request: ForwardTestRequest, client_id: int, created_at_utc: datetime
) -> ForwardTestRow:
    async with connection.cursor(row_factory=class_row(ForwardTestRow)) as cursor:
        await cursor.execute(
            f"""
            INSERT INTO forward_test (
                strategy_version_id, symbol, exchange, currency, bar_period, desired_state, status, client_id,
                created_at_utc
            ) VALUES (
                %(strategy_version_id)s, %(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, 'running',
                'starting', %(client_id)s, %(created_at_utc)s
            )
            RETURNING {FORWARD_TEST_COLUMNS}
            """,
            {
                "strategy_version_id": request.strategy_version_id,
                "symbol": request.instrument.symbol,
                "exchange": request.instrument.exchange,
                "currency": request.instrument.currency,
                "bar_period": request.bar_period.value,
                "client_id": client_id,
                "created_at_utc": created_at_utc,
            },
        )
        row = await cursor.fetchone()
    if row is None:
        message = "INSERT ... RETURNING returned no row."
        raise RuntimeError(message)
    return row


async def start_forward_test(
    connection: psycopg.AsyncConnection, *, request: ForwardTestRequest, client_ids: range, created_at_utc: datetime
) -> ForwardTestRow | StartRefusal:
    """Takes the lowest free client ID in one transaction (section 12.4). The connection must not be in autocommit.

    The table lock makes parallel starts wait for each other. The unique constraints are a second guard.
    """
    async with connection.transaction():
        await connection.execute("LOCK TABLE forward_test IN SHARE ROW EXCLUSIVE MODE")
        running_forward_test = await select_forward_test_on_instrument(connection, request.instrument)
        if running_forward_test is not None:
            return StartRefusal(reason="instrument_taken", forward_test_id=running_forward_test.id)
        client_id = find_lowest_free_client_id(client_ids, await select_taken_client_ids(connection))
        if client_id is None:
            return StartRefusal(reason="no_free_client_id", forward_test_id=None)
        return await insert_forward_test(
            connection, request=request, client_id=client_id, created_at_utc=created_at_utc
        )


async def select_forward_tests(connection: psycopg.AsyncConnection) -> list[ForwardTestRow]:
    async with connection.cursor(row_factory=class_row(ForwardTestRow)) as cursor:
        await cursor.execute(f"SELECT {FORWARD_TEST_COLUMNS} FROM forward_test ORDER BY id DESC")
        return await cursor.fetchall()


async def select_forward_test(connection: psycopg.AsyncConnection, forward_test_id: int) -> ForwardTestRow | None:
    async with connection.cursor(row_factory=class_row(ForwardTestRow)) as cursor:
        await cursor.execute(
            f"SELECT {FORWARD_TEST_COLUMNS} FROM forward_test WHERE id = %(id)s", {"id": forward_test_id}
        )
        return await cursor.fetchone()


async def write_desired_state(
    connection: psycopg.AsyncConnection, *, forward_test_id: int, desired_state: DesiredState
) -> bool:
    """The only write of the Web process after the insert (section 12.3). Returns False when the row is missing."""
    cursor = await connection.execute(
        "UPDATE forward_test SET desired_state = %(desired_state)s WHERE id = %(id)s",
        {"desired_state": desired_state, "id": forward_test_id},
    )
    return cursor.rowcount == 1


async def select_rows_to_compare(connection: psycopg.AsyncConnection) -> list[ForwardTestRow]:
    """The rows that the worker can still act on: a row is done when it is stopped, or failed without a client ID."""
    async with connection.cursor(row_factory=class_row(ForwardTestRow)) as cursor:
        await cursor.execute(
            f"""
            SELECT {FORWARD_TEST_COLUMNS} FROM forward_test
            WHERE status <> 'stopped' AND NOT (status = 'failed' AND client_id IS NULL)
            ORDER BY id
            """
        )
        return await cursor.fetchall()


async def write_status(connection: psycopg.AsyncConnection, *, forward_test_id: int, status: ForwardTestStatus) -> None:
    await connection.execute(
        "UPDATE forward_test SET status = %(status)s WHERE id = %(id)s", {"status": status, "id": forward_test_id}
    )


async def write_end(
    connection: psycopg.AsyncConnection,
    *,
    forward_test_id: int,
    status: ForwardTestStatus,
    stopped_at_utc: datetime,
    error_message: str | None,
) -> None:
    """The process ended and its orders are cancelled, or it never sent orders: the client ID becomes free."""
    await connection.execute(
        """
        UPDATE forward_test
        SET status = %(status)s, client_id = NULL, stopped_at_utc = %(stopped_at_utc)s,
            error_message = COALESCE(error_message, %(error_message)s)
        WHERE id = %(id)s
        """,
        {"status": status, "stopped_at_utc": stopped_at_utc, "error_message": error_message, "id": forward_test_id},
    )


async def write_failure_with_client_id(
    connection: psycopg.AsyncConnection, *, forward_test_id: int, status: ForwardTestStatus, error_message: str
) -> None:
    """The process ended, but its orders can still be open: the client ID stays taken (section 12.4)."""
    await connection.execute(
        """
        UPDATE forward_test SET status = %(status)s, error_message = COALESCE(error_message, %(error_message)s)
        WHERE id = %(id)s
        """,
        {"status": status, "error_message": error_message, "id": forward_test_id},
    )


async def write_error_message(connection: psycopg.AsyncConnection, *, forward_test_id: int, error_message: str) -> None:
    """The child process writes why it failed, for example the reason of the paper account check."""
    await connection.execute(
        "UPDATE forward_test SET error_message = %(error_message)s WHERE id = %(id)s",
        {"error_message": error_message, "id": forward_test_id},
    )


async def write_start_balance(
    connection: psycopg.AsyncConnection, *, forward_test_id: int, start_balance_usd: Decimal
) -> None:
    """The balance at the first start. A restart keeps the first value (section 12.1)."""
    await connection.execute(
        """
        UPDATE forward_test SET start_balance_usd = %(start_balance_usd)s
        WHERE id = %(id)s AND start_balance_usd IS NULL
        """,
        {"start_balance_usd": start_balance_usd, "id": forward_test_id},
    )
