"""The forward-test worker: every 2 seconds it compares the desired state with the actual state of each forward test,
starts, stops, and restarts child processes, and writes the actual state (docs/architecture.md sections 12.3-12.7).

The function that starts a child comes in as an argument, so that tests and the e2e server pass a fake.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Protocol

import psycopg

from atrade.forward_test import forward_test_store
from atrade.forward_test.forward_test_store import ForwardTestRow
from atrade.foundation.clock import Clock
from atrade.paper_trading import transfer_to_by_hand

COMPARE_INTERVAL_SECONDS = 2.0
# The child exits with this code when the paper account check fails. It sent no order, so there is no retry.
PAPER_CHECK_FAILED_EXIT_CODE = 3
PAPER_CHECK_FAILED_MESSAGE = "The paper account check failed."
# The child exits with this code when IB Gateway is not reachable for a long time (section 12.7). It is not a crash:
# the worker writes "waiting_for_gateway" and starts the child again, which waits for IB Gateway.
GATEWAY_UNREACHABLE_EXIT_CODE = 4
# After this number of crashes in a row, the worker stops the restarts (section 12.7).
CRASH_LIMIT = 3
# A run child that ran this long before its crash starts a new count: the crashes are not "in a row".
CRASH_COUNT_RESET_AFTER = timedelta(minutes=10)

# "run": check the paper account, run the LiveNode until the stop request, then cancel the open orders.
# "cancel_orders": only cancel the open orders of the client ID, for a stop without a running child.
type ChildMode = Literal["run", "cancel_orders"]


class ForwardTestChild(Protocol):
    def read_exit_code(self) -> int | None:
        """None while the child runs."""
        ...

    def request_stop(self) -> None:
        """Asks the child to stop the LiveNode, cancel its orders, and exit (section 12.6)."""
        ...


type StartForwardTestChild = Callable[[int, ChildMode], Awaitable[ForwardTestChild]]


@dataclass
class RunningChild:
    child: ForwardTestChild
    mode: ChildMode
    started_at_utc: datetime
    is_stop_requested: bool = False


def describe_crash(exit_code: int) -> str:
    return f"The forward test process ended with exit code {exit_code}. The forward-test log has the reason."


class ForwardTestWorker:
    def __init__(self, *, database_url: str, clock: Clock, start_child: StartForwardTestChild) -> None:
        self.database_url = database_url
        self.clock = clock
        self.start_child = start_child
        self.running_children: dict[int, RunningChild] = {}

    async def keep_comparing(self) -> None:
        """Runs until the caller cancels it."""
        while True:
            await self.compare_states()
            await asyncio.sleep(COMPARE_INTERVAL_SECONDS)

    async def compare_states(self) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            for row in await forward_test_store.select_rows_to_compare(connection):
                await self.compare_row(connection, row)

    async def compare_row(self, connection: psycopg.AsyncConnection, row: ForwardTestRow) -> None:
        running_child = self.running_children.get(row.id)
        if running_child is None:
            await self.start_child_when_needed(connection, row)
            return
        exit_code = running_child.child.read_exit_code()
        if exit_code is not None:
            del self.running_children[row.id]
            await self.record_child_end(connection, row, running_child, exit_code)
            return
        is_stop_wanted = row.is_stop_wanted(self.clock.read_now_utc())
        if is_stop_wanted and running_child.mode == "run" and not running_child.is_stop_requested:
            running_child.child.request_stop()
            running_child.is_stop_requested = True
            await forward_test_store.write_status(connection, forward_test_id=row.id, status="stopping")

    async def start_child_when_needed(self, connection: psycopg.AsyncConnection, row: ForwardTestRow) -> None:
        now_utc = self.clock.read_now_utc()
        # A stop without a running child, after a crash, a failed cancel, a worker restart, or the end time:
        # cancel the orders of the client ID.
        if row.is_stop_wanted(now_utc):
            if row.client_id is not None:
                await self.start_running_child(row.id, "cancel_orders")
                await forward_test_store.write_status(connection, forward_test_id=row.id, status="stopping")
            return
        if row.status not in {"starting", "running", "waiting_for_gateway"}:
            return
        # A row with status "running" and no child is a forward test of an earlier worker: start it again.
        if row.status == "running":
            await forward_test_store.start_interruption(
                connection, forward_test_id=row.id, reason="worker_restart", started_at_utc=now_utc
            )
        await self.start_running_child(row.id, "run")
        # While the child waits for IB Gateway, the status stays. The child writes "running" at the LiveNode start.
        if row.status != "waiting_for_gateway":
            await forward_test_store.write_status(connection, forward_test_id=row.id, status="running")

    async def start_running_child(self, forward_test_id: int, mode: ChildMode) -> None:
        child = await self.start_child(forward_test_id, mode)
        self.running_children[forward_test_id] = RunningChild(
            child=child, mode=mode, started_at_utc=self.clock.read_now_utc()
        )

    async def record_child_end(
        self, connection: psycopg.AsyncConnection, row: ForwardTestRow, running_child: RunningChild, exit_code: int
    ) -> None:
        now_utc = self.clock.read_now_utc()
        is_stop = running_child.mode == "cancel_orders" or running_child.is_stop_requested
        if is_stop and exit_code == 0:
            async with connection.transaction():
                await forward_test_store.write_end(
                    connection, forward_test_id=row.id, status="stopped", stopped_at_utc=now_utc, error_message=None
                )
                # The positions and the remaining cash go to "By hand". The records do not change (section 12.6).
                await transfer_to_by_hand(connection, forward_test_id=row.id, time_utc=now_utc)
            return
        if is_stop:
            await forward_test_store.write_failure_with_client_id(
                connection, forward_test_id=row.id, status="stop_failed", error_message=describe_crash(exit_code)
            )
            return
        if exit_code == PAPER_CHECK_FAILED_EXIT_CODE:
            async with connection.transaction():
                await forward_test_store.write_end(
                    connection,
                    forward_test_id=row.id,
                    status="failed",
                    stopped_at_utc=now_utc,
                    error_message=PAPER_CHECK_FAILED_MESSAGE,
                )
                # The capital is not allocated any more, so it goes back to "By hand" (section 12.18).
                await transfer_to_by_hand(connection, forward_test_id=row.id, time_utc=now_utc)
            return
        if exit_code == GATEWAY_UNREACHABLE_EXIT_CODE:
            await forward_test_store.write_waiting_for_gateway(
                connection, forward_test_id=row.id, started_at_utc=now_utc
            )
            return
        await self.record_crash(connection, row, running_child, now_utc, exit_code)

    async def record_crash(
        self,
        connection: psycopg.AsyncConnection,
        row: ForwardTestRow,
        running_child: RunningChild,
        now_utc: datetime,
        exit_code: int,
    ) -> None:
        """A run child ended without a stop request. Its orders can still be open, so the client ID stays taken.

        The next comparison restarts it (the restart child cancels the old orders first), until CRASH_LIMIT.
        """
        is_new_count = now_utc - running_child.started_at_utc >= CRASH_COUNT_RESET_AFTER
        crash_count = 1 if is_new_count else row.crash_count + 1
        await forward_test_store.start_interruption(
            connection, forward_test_id=row.id, reason="crash", started_at_utc=now_utc
        )
        await forward_test_store.write_crash(
            connection,
            forward_test_id=row.id,
            status="failed" if crash_count >= CRASH_LIMIT else "starting",
            crash_count=crash_count,
            error_message=describe_crash(exit_code),
        )
