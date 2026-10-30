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
from atrade.paper_trading import write_capital_allocation

type DesiredState = Literal["running", "stopped"]
type ForwardTestStatus = Literal[
    "starting", "running", "waiting_for_gateway", "stopping", "stopped", "stop_failed", "failed"
]
# Why the forward test did not run for a time (section 12.7).
type InterruptionReason = Literal["crash", "gateway", "worker_restart"]

NO_FREE_CLIENT_ID_MESSAGE = "limit of running forward tests reached"


@dataclass(frozen=True)
class ForwardTestRequest:
    strategy_version_id: int
    instrument: Instrument
    bar_period: BarPeriod
    # The capital of the forward test in USD (section 12.18).
    allocated_capital_usd: Decimal
    end_time_utc: datetime | None = None


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
    end_time_utc: datetime | None
    crash_count: int
    # None for a forward test of the time before the allocated capital. It then uses start_balance_usd.
    allocated_capital_usd: Decimal | None

    @property
    def start_capital_usd(self) -> Decimal | None:
        """The start of the equity curve and of the Net profit: the allocated capital, or the old start balance."""
        return self.allocated_capital_usd if self.allocated_capital_usd is not None else self.start_balance_usd

    def is_stop_wanted(self, now_utc: datetime) -> bool:
        """The user stopped the forward test, or its end time came (section 12.1)."""
        return self.desired_state == "stopped" or (self.end_time_utc is not None and now_utc >= self.end_time_utc)


@dataclass(frozen=True)
class ForwardTestInterruption:
    reason: InterruptionReason
    started_at_utc: datetime
    # None while the interruption lasts.
    ended_at_utc: datetime | None


@dataclass(frozen=True)
class StartRefusal:
    """Why the start was refused. `unallocated_usd` is set when the allocated capital is too large (section 12.18)."""

    reason: Literal["no_free_client_id", "capital_too_large"]
    unallocated_usd: Decimal | None = None


FORWARD_TEST_COLUMNS: Final = """
    id, strategy_version_id, symbol, exchange, currency, bar_period, desired_state, status, client_id,
    start_balance_usd, error_message, created_at_utc, stopped_at_utc, end_time_utc, crash_count, allocated_capital_usd
"""


def read_instrument(row: ForwardTestRow) -> Instrument:
    return Instrument(symbol=row.symbol, exchange=row.exchange, currency=row.currency)


async def select_allocated_usd(connection: psycopg.AsyncConnection) -> Decimal:
    """The sum of the allocated capital of the running forward tests: the forward tests that hold a client ID."""
    cursor = await connection.execute(
        "SELECT COALESCE(sum(allocated_capital_usd), 0) FROM forward_test WHERE client_id IS NOT NULL"
    )
    row = await cursor.fetchone()
    return Decimal(0) if row is None else Decimal(row[0])


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
                created_at_utc, end_time_utc, allocated_capital_usd
            ) VALUES (
                %(strategy_version_id)s, %(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, 'running',
                'starting', %(client_id)s, %(created_at_utc)s, %(end_time_utc)s, %(allocated_capital_usd)s
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
                "end_time_utc": request.end_time_utc,
                "allocated_capital_usd": request.allocated_capital_usd,
            },
        )
        row = await cursor.fetchone()
    if row is None:
        message = "INSERT ... RETURNING returned no row."
        raise RuntimeError(message)
    return row


async def start_forward_test(  # noqa: PLR0913 readability-exception: one keyword argument per input of the start.
    connection: psycopg.AsyncConnection,
    *,
    request: ForwardTestRequest,
    client_ids: range,
    created_at_utc: datetime,
    net_liquidation_usd: Decimal,
    account: str,
) -> ForwardTestRow | StartRefusal:
    """Checks the allocated capital and takes the lowest free client ID in one transaction (sections 12.4, 12.18).

    The connection must not be in autocommit. The table lock makes parallel starts wait for each other. The unique
    constraints are a second guard. The same transaction moves the allocated capital from "By hand" to the forward
    test in the owner ledger.
    """
    async with connection.transaction():
        await connection.execute("LOCK TABLE forward_test IN SHARE ROW EXCLUSIVE MODE")
        unallocated_usd = net_liquidation_usd - await select_allocated_usd(connection)
        if request.allocated_capital_usd > unallocated_usd:
            return StartRefusal(reason="capital_too_large", unallocated_usd=unallocated_usd)
        client_id = find_lowest_free_client_id(client_ids, await select_taken_client_ids(connection))
        if client_id is None:
            return StartRefusal(reason="no_free_client_id")
        row = await insert_forward_test(connection, request=request, client_id=client_id, created_at_utc=created_at_utc)
        await write_capital_allocation(
            connection,
            account=account,
            forward_test_id=row.id,
            allocated_capital_usd=request.allocated_capital_usd,
            time_utc=created_at_utc,
        )
        return row


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
    """The process ended and its orders are cancelled, or it never sent orders: the client ID becomes free.

    An open interruption ends at the same time. The status "stopped" clears the message of an earlier crash: it is
    not the current state. The crash interruptions keep the history (section 12.7).
    """
    await connection.execute(
        """
        UPDATE forward_test
        SET status = %(status)s, client_id = NULL, stopped_at_utc = %(stopped_at_utc)s,
            error_message = CASE WHEN %(status)s = 'stopped' THEN NULL
                                 ELSE COALESCE(error_message, %(error_message)s) END
        WHERE id = %(id)s
        """,
        {"status": status, "stopped_at_utc": stopped_at_utc, "error_message": error_message, "id": forward_test_id},
    )
    await end_interruption(connection, forward_test_id=forward_test_id, ended_at_utc=stopped_at_utc)


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


async def write_crash(
    connection: psycopg.AsyncConnection,
    *,
    forward_test_id: int,
    status: ForwardTestStatus,
    crash_count: int,
    error_message: str,
) -> None:
    """A run child ended without a stop request. The client ID stays taken: its orders can still be open."""
    await connection.execute(
        """
        UPDATE forward_test
        SET status = %(status)s, crash_count = %(crash_count)s,
            error_message = COALESCE(error_message, %(error_message)s)
        WHERE id = %(id)s
        """,
        {"status": status, "crash_count": crash_count, "error_message": error_message, "id": forward_test_id},
    )


async def start_interruption(
    connection: psycopg.AsyncConnection, *, forward_test_id: int, reason: InterruptionReason, started_at_utc: datetime
) -> None:
    """Records the start of an interruption. When one is already open, it stays and this call does nothing."""
    await connection.execute(
        """
        INSERT INTO forward_test_interruption (forward_test_id, reason, started_at_utc)
        VALUES (%(id)s, %(reason)s, %(started_at_utc)s)
        ON CONFLICT (forward_test_id) WHERE ended_at_utc IS NULL DO NOTHING
        """,
        {"id": forward_test_id, "reason": reason, "started_at_utc": started_at_utc},
    )


async def end_interruption(
    connection: psycopg.AsyncConnection, *, forward_test_id: int, ended_at_utc: datetime
) -> None:
    await connection.execute(
        """
        UPDATE forward_test_interruption SET ended_at_utc = %(ended_at_utc)s
        WHERE forward_test_id = %(id)s AND ended_at_utc IS NULL
        """,
        {"id": forward_test_id, "ended_at_utc": ended_at_utc},
    )


async def select_interruptions(
    connection: psycopg.AsyncConnection, forward_test_id: int
) -> list[ForwardTestInterruption]:
    async with connection.cursor(row_factory=class_row(ForwardTestInterruption)) as cursor:
        await cursor.execute(
            """
            SELECT reason, started_at_utc, ended_at_utc FROM forward_test_interruption
            WHERE forward_test_id = %(id)s ORDER BY started_at_utc, id
            """,
            {"id": forward_test_id},
        )
        return await cursor.fetchall()


async def select_interruptions_of_forward_tests(
    connection: psycopg.AsyncConnection, forward_test_ids: list[int]
) -> dict[int, list[ForwardTestInterruption]]:
    """The interruptions of each forward test in one query. A forward test without interruptions has an empty list."""
    interruptions: dict[int, list[ForwardTestInterruption]] = {
        forward_test_id: [] for forward_test_id in forward_test_ids
    }
    cursor = await connection.execute(
        """
        SELECT forward_test_id, reason, started_at_utc, ended_at_utc FROM forward_test_interruption
        WHERE forward_test_id = ANY(%(ids)s) ORDER BY forward_test_id, started_at_utc, id
        """,
        {"ids": forward_test_ids},
    )
    for forward_test_id, reason, started_at_utc, ended_at_utc in await cursor.fetchall():
        interruptions[forward_test_id].append(
            ForwardTestInterruption(reason=reason, started_at_utc=started_at_utc, ended_at_utc=ended_at_utc)
        )
    return interruptions


async def write_waiting_for_gateway(
    connection: psycopg.AsyncConnection, *, forward_test_id: int, started_at_utc: datetime
) -> None:
    """IB Gateway is not reachable (section 12.5). The child writes it. A stop that came first stays."""
    await connection.execute(
        """
        UPDATE forward_test SET status = 'waiting_for_gateway'
        WHERE id = %(id)s AND status IN ('starting', 'running', 'waiting_for_gateway')
        """,
        {"id": forward_test_id},
    )
    await start_interruption(
        connection, forward_test_id=forward_test_id, reason="gateway", started_at_utc=started_at_utc
    )


async def write_live_node_start(
    connection: psycopg.AsyncConnection, *, forward_test_id: int, started_at_utc: datetime
) -> None:
    """The child starts the LiveNode: the forward test runs again, and an open interruption ends.

    The message of an earlier crash is not the current state anymore. The crash interruption keeps the history.
    """
    await connection.execute(
        """
        UPDATE forward_test SET status = 'running', error_message = NULL
        WHERE id = %(id)s AND status IN ('starting', 'running', 'waiting_for_gateway')
        """,
        {"id": forward_test_id},
    )
    await end_interruption(connection, forward_test_id=forward_test_id, ended_at_utc=started_at_utc)


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
