"""The forward-test worker: every 2 seconds it compares the desired state with the actual state of each forward test,
starts and stops child processes, and writes the actual state (docs/architecture.md sections 12.3-12.6).

The function that starts a child comes in as an argument, so that tests and the e2e server pass a fake.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, Protocol

import psycopg

from atrade.forward_test import forward_test_store
from atrade.forward_test.forward_test_store import ForwardTestRow
from atrade.foundation.clock import Clock

COMPARE_INTERVAL_SECONDS = 2.0
# The child exits with this code when the paper account check fails. It sent no order, so there is no retry.
PAPER_CHECK_FAILED_EXIT_CODE = 3
PAPER_CHECK_FAILED_MESSAGE = "The paper account check failed."

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
        if row.desired_state == "stopped" and running_child.mode == "run" and not running_child.is_stop_requested:
            running_child.child.request_stop()
            running_child.is_stop_requested = True
            await forward_test_store.write_status(connection, forward_test_id=row.id, status="stopping")

    async def start_child_when_needed(self, connection: psycopg.AsyncConnection, row: ForwardTestRow) -> None:
        # A row with status "running" and no child is a forward test of an earlier worker: start it again.
        if row.desired_state == "running" and row.status in {"starting", "running"}:
            await self.start_running_child(row.id, "run")
            await forward_test_store.write_status(connection, forward_test_id=row.id, status="running")
            return
        # A stop without a running child, after a crash or a failed cancel: cancel the orders of the client ID.
        if row.desired_state == "stopped" and row.client_id is not None:
            await self.start_running_child(row.id, "cancel_orders")
            await forward_test_store.write_status(connection, forward_test_id=row.id, status="stopping")

    async def start_running_child(self, forward_test_id: int, mode: ChildMode) -> None:
        child = await self.start_child(forward_test_id, mode)
        self.running_children[forward_test_id] = RunningChild(child=child, mode=mode)

    async def record_child_end(
        self, connection: psycopg.AsyncConnection, row: ForwardTestRow, running_child: RunningChild, exit_code: int
    ) -> None:
        is_stop = running_child.mode == "cancel_orders" or running_child.is_stop_requested
        if is_stop and exit_code == 0:
            await forward_test_store.write_end(
                connection,
                forward_test_id=row.id,
                status="stopped",
                stopped_at_utc=self.clock.read_now_utc(),
                error_message=None,
            )
            return
        if is_stop:
            await forward_test_store.write_failure_with_client_id(
                connection, forward_test_id=row.id, status="stop_failed", error_message=describe_crash(exit_code)
            )
            return
        if exit_code == PAPER_CHECK_FAILED_EXIT_CODE:
            await forward_test_store.write_end(
                connection,
                forward_test_id=row.id,
                status="failed",
                stopped_at_utc=self.clock.read_now_utc(),
                error_message=PAPER_CHECK_FAILED_MESSAGE,
            )
            return
        # Issue #77 adds the automatic restarts. Until then a crash fails the forward test. Its orders can still be
        # open, so the client ID stays taken until a stop cancels them.
        await forward_test_store.write_failure_with_client_id(
            connection, forward_test_id=row.id, status="failed", error_message=describe_crash(exit_code)
        )
