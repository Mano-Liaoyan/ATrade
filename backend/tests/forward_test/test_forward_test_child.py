"""The forward test child process body: the paper account check before the LiveNode start, and the stop steps
(docs/architecture.md sections 12.5 and 12.6).

The IBKR connection is the fake. The function that runs the LiveNode is a fake: the real LiveNode needs IB Gateway
(test_forward_test_paper_contract.py).
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from atrade.forward_test import (
    GATEWAY_UNREACHABLE_EXIT_CODE,
    PAPER_CHECK_FAILED_EXIT_CODE,
    ChildMode,
    IbkrAccess,
    LiveNodeEnd,
    LiveNodeInput,
    run_forward_test_child,
)
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, make_balance_values, make_forward_test_order
from tests.forward_test.test_forward_test_routes import (
    FORWARD_TESTS_PATH,
    make_start_request,
    save_test_strategy_version,
)

ACCOUNT_ID = "DU1234567"
TEST_GATEWAY_RETRY_SECONDS = 0.01
FORWARD_TEST_CLIENT_ID = 10
WEB_CLIENT_ID = 1

type JsonObject = dict[str, Any]


class FakeLiveNode:
    """Records the input and sends one order with the forward test client ID, like a strategy on a LiveNode."""

    def __init__(self, gateway_connection: FakeGatewayConnection, *, end: LiveNodeEnd | None = None) -> None:
        self.gateway_connection = gateway_connection
        # When it is set, the LiveNode ends at once with it, without the stop request.
        self.end: LiveNodeEnd | None = end
        self.inputs: list[LiveNodeInput] = []
        self.was_check_connection_open_at_start = False
        self.open_order_ids_at_start: list[int] = []

    async def run_live_node(self, live_node_input: LiveNodeInput, stop_requested: asyncio.Event) -> LiveNodeEnd:
        self.inputs.append(live_node_input)
        self.was_check_connection_open_at_start = self.gateway_connection.connected
        self.open_order_ids_at_start = [order.order_id for order in self.gateway_connection.open_orders]
        if self.end is not None:
            return self.end
        self.gateway_connection.open_orders.append(
            make_forward_test_order(
                ACCOUNT_ID,
                forward_test_id=live_node_input.forward_test_id,
                order_id=7,
                client_id=live_node_input.client_id,
            )
        )
        await stop_requested.wait()
        return "ended"


def make_settings(database_url: str, frontend_build_dir: Path, *, ibkr_account_id: str = ACCOUNT_ID) -> Settings:
    return Settings(database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=ibkr_account_id)


def make_forward_test_gateway() -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID], client_id=FORWARD_TEST_CLIENT_ID)
    gateway_connection.account_values = make_balance_values(ACCOUNT_ID, net_liquidation_usd="98765.40", cash_usd="1")
    # An order by hand of the Web process. The forward test must not cancel it.
    gateway_connection.open_orders = [
        make_forward_test_order(ACCOUNT_ID, forward_test_id=99, order_id=3, client_id=WEB_CLIENT_ID)
    ]
    return gateway_connection


async def start_forward_test(web_client: httpx.AsyncClient) -> JsonObject:
    strategy_version_id = await save_test_strategy_version(web_client)
    return (await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))).json()


@dataclass(frozen=True)
class ChildRunOptions:
    # IB Gateway is not reachable for this number of connections.
    reachable_after_connections: int = 0
    # When it is True, the stop request is there before the child starts.
    is_stop_requested_at_start: bool = True


DEFAULT_CHILD_RUN_OPTIONS = ChildRunOptions()


async def run_child(
    settings: Settings,
    forward_test_id: int,
    mode: ChildMode,
    live_node: FakeLiveNode,
    options: ChildRunOptions = DEFAULT_CHILD_RUN_OPTIONS,
) -> tuple[int, list[int]]:
    """Runs the child with the gateway of `live_node`. Returns the exit code and the opened client IDs."""
    gateway_connection = live_node.gateway_connection
    reachable_after_connections = options.reachable_after_connections
    opened_client_ids: list[int] = []

    def open_gateway_connection(client_id: int) -> FakeGatewayConnection:
        opened_client_ids.append(client_id)
        gateway_connection.is_gateway_reachable = len(opened_client_ids) > reachable_after_connections
        return gateway_connection

    stop_requested = asyncio.Event()
    if options.is_stop_requested_at_start:
        stop_requested.set()
    exit_code = await run_forward_test_child(
        settings=settings,
        forward_test_id=forward_test_id,
        mode=mode,
        ibkr_access=IbkrAccess(
            open_gateway_connection=open_gateway_connection,
            run_live_node=live_node.run_live_node,
            clock=FixedClock(datetime(2026, 1, 2, 3, 10, tzinfo=UTC)),
            gateway_retry_seconds=TEST_GATEWAY_RETRY_SECONDS,
        ),
        stop_requested=stop_requested,
    )
    return exit_code, opened_client_ids


@pytest.mark.anyio
async def test_checks_the_paper_account_then_runs_the_live_node_with_the_same_client_id(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()
    live_node = FakeLiveNode(gateway_connection)

    exit_code, opened_client_ids = await run_child(
        make_settings(database_url, frontend_build_dir), forward_test["id"], "run", live_node
    )

    assert exit_code == 0
    [live_node_input] = live_node.inputs
    assert live_node_input.client_id == 10
    assert live_node_input.account_id == ACCOUNT_ID
    assert live_node_input.order_id_tag == f"FT{forward_test['id']}"
    assert live_node_input.instrument.symbol == "AAPL"
    assert "class BarCountStrategy" in live_node_input.strategy_code
    # The check connection closes before the LiveNode connects with the same client ID.
    assert not live_node.was_check_connection_open_at_start
    assert opened_client_ids == [10, 10]
    listed = (await web_client.get(FORWARD_TESTS_PATH)).json()[0]
    assert listed["start_balance_usd"] == "98765.40"


@pytest.mark.anyio
async def test_stop_cancels_only_the_open_orders_of_the_forward_test_client_id(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()

    await run_child(
        make_settings(database_url, frontend_build_dir),
        forward_test["id"],
        "run",
        FakeLiveNode(gateway_connection),
    )

    assert [order.client_id for order in gateway_connection.open_orders] == [WEB_CLIENT_ID]
    assert not gateway_connection.connected


@pytest.mark.anyio
async def test_a_failed_paper_account_check_starts_no_live_node(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()
    live_node = FakeLiveNode(gateway_connection)
    settings = make_settings(database_url, frontend_build_dir, ibkr_account_id="DU7654321")

    exit_code, _ = await run_child(settings, forward_test["id"], "run", live_node)

    assert exit_code == PAPER_CHECK_FAILED_EXIT_CODE
    assert live_node.inputs == []
    listed = (await web_client.get(FORWARD_TESTS_PATH)).json()[0]
    assert listed["error_message"] == (
        "The paper account check failed: The account DU1234567 from IB Gateway is not the expected account DU7654321."
    )


@pytest.mark.anyio
async def test_cancel_mode_cancels_the_orders_without_a_live_node(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()
    gateway_connection.open_orders.append(
        make_forward_test_order(ACCOUNT_ID, forward_test_id=forward_test["id"], order_id=8, client_id=10)
    )
    live_node = FakeLiveNode(gateway_connection)

    exit_code, _ = await run_child(
        make_settings(database_url, frontend_build_dir),
        forward_test["id"],
        "cancel_orders",
        live_node,
    )

    assert exit_code == 0
    assert live_node.inputs == []
    assert [order.client_id for order in gateway_connection.open_orders] == [WEB_CLIENT_ID]


@pytest.mark.anyio
async def test_a_cancel_without_confirmation_ends_with_an_error(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()
    gateway_connection.open_orders.append(
        make_forward_test_order(ACCOUNT_ID, forward_test_id=forward_test["id"], order_id=8, client_id=10)
    )
    gateway_connection.cancel_error_message = "IB Gateway did not confirm the cancel of order 8 in time."

    exit_code, _ = await run_child(
        make_settings(database_url, frontend_build_dir),
        forward_test["id"],
        "cancel_orders",
        FakeLiveNode(gateway_connection),
    )

    assert exit_code == 1
    listed = (await web_client.get(FORWARD_TESTS_PATH)).json()[0]
    assert listed["error_message"] == (
        "The open orders were not cancelled: IB Gateway did not confirm the cancel of order 8 in time."
    )


@pytest.mark.anyio
async def test_a_restart_cancels_the_old_orders_before_the_live_node_starts(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()
    # An order of the earlier child of this forward test, before its crash.
    gateway_connection.open_orders.append(
        make_forward_test_order(ACCOUNT_ID, forward_test_id=forward_test["id"], order_id=8, client_id=10)
    )
    live_node = FakeLiveNode(gateway_connection)

    exit_code, opened_client_ids = await run_child(
        make_settings(database_url, frontend_build_dir), forward_test["id"], "run", live_node
    )

    assert exit_code == 0
    assert live_node.open_order_ids_at_start == [3]
    assert opened_client_ids == [10, 10]


@pytest.mark.anyio
async def test_the_child_waits_for_the_gateway_and_retries(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()
    statuses_at_start: list[str] = []
    live_node = FakeLiveNode(gateway_connection)
    run_fake_live_node = live_node.run_live_node

    async def run_live_node(live_node_input: LiveNodeInput, stop_requested: asyncio.Event) -> LiveNodeEnd:
        statuses_at_start.append((await web_client.get(FORWARD_TESTS_PATH)).json()[0]["status"])
        stop_requested.set()
        return await run_fake_live_node(live_node_input, stop_requested)

    live_node.run_live_node = run_live_node  # pyright: ignore[reportAttributeAccessIssue]

    exit_code, opened_client_ids = await run_child(
        make_settings(database_url, frontend_build_dir),
        forward_test["id"],
        "run",
        live_node,
        ChildRunOptions(reachable_after_connections=2, is_stop_requested_at_start=False),
    )

    assert exit_code == 0
    assert opened_client_ids == [10, 10, 10, 10]
    assert statuses_at_start == ["running"]
    listed = (await web_client.get(FORWARD_TESTS_PATH)).json()[0]
    assert listed["interruptions"] == [
        {"reason": "gateway", "started_at_utc": "2026-01-02T03:10:00Z", "ended_at_utc": "2026-01-02T03:10:00Z"}
    ]
    assert listed["error_message"] is None


@pytest.mark.anyio
async def test_a_lost_gateway_ends_the_child_without_a_cancel(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()

    exit_code, opened_client_ids = await run_child(
        make_settings(database_url, frontend_build_dir),
        forward_test["id"],
        "run",
        FakeLiveNode(gateway_connection, end="gateway_lost"),
        ChildRunOptions(is_stop_requested_at_start=False),
    )

    assert exit_code == GATEWAY_UNREACHABLE_EXIT_CODE
    assert opened_client_ids == [10]


@pytest.mark.anyio
async def test_a_stop_while_the_child_waits_for_the_gateway_tries_the_cancel(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()
    live_node = FakeLiveNode(gateway_connection)

    exit_code, opened_client_ids = await run_child(
        make_settings(database_url, frontend_build_dir),
        forward_test["id"],
        "run",
        live_node,
        ChildRunOptions(reachable_after_connections=10),
    )

    # The orders of an earlier child can still be open, so the stop fails until IB Gateway is back.
    assert exit_code == 1
    assert live_node.inputs == []
    assert opened_client_ids == [10, 10]
    listed = (await web_client.get(FORWARD_TESTS_PATH)).json()[0]
    assert listed["status"] == "waiting_for_gateway"
