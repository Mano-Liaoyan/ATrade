"""The forward test child process body: the paper account check before the LiveNode start, and the stop steps
(docs/architecture.md sections 12.5 and 12.6).

The IBKR connection is the fake. The function that runs the LiveNode is a fake: the real LiveNode needs IB Gateway
(test_forward_test_paper_contract.py).
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg
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
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.settings import Settings
from atrade.ibkr import AccountValue
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import (
    FakeGatewayConnection,
    HistoricalBarRequest,
    make_balance_values,
    make_forward_test_order,
)
from tests.forward_test.test_forward_test_routes import (
    FORWARD_TESTS_PATH,
    make_start_request,
    save_test_strategy_version,
)

ACCOUNT_ID = "DU1234567"
CHILD_NOW_UTC = datetime(2026, 1, 2, 3, 10, 30, tzinfo=UTC)
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


async def start_old_forward_test(web_client: httpx.AsyncClient, database_url: str) -> JsonObject:
    """A forward test from the time before the allocated capital: its equity starts at the start balance."""
    forward_test = await start_forward_test(web_client)
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            "UPDATE forward_test SET allocated_capital_usd = NULL WHERE id = %(id)s", {"id": forward_test["id"]}
        )
    return forward_test


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
            clock=FixedClock(CHILD_NOW_UTC),
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
    # The recorder DataActor of the LiveNode starts the equity at the allocated capital (section 12.8).
    assert live_node_input.database_url == database_url
    assert live_node_input.start_balance_usd == Decimal(10000)
    # The check connection closes before the LiveNode connects with the same client ID.
    assert not live_node.was_check_connection_open_at_start
    assert opened_client_ids == [10, 10]
    listed = (await web_client.get(FORWARD_TESTS_PATH)).json()[0]
    assert listed["start_balance_usd"] is None


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
async def test_the_live_node_gets_the_warm_up_bars_of_7_days_before_the_start(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()
    live_node = FakeLiveNode(gateway_connection)

    await run_child(make_settings(database_url, frontend_build_dir), forward_test["id"], "run", live_node)

    # The range ends at the start of the current 1-minute bar: the current bar is not complete.
    warm_up_end_utc = datetime(2026, 1, 2, 3, 10, tzinfo=UTC)
    [request] = gateway_connection.historical_bar_requests
    assert request == HistoricalBarRequest(
        live_node.inputs[0].instrument,
        BarPeriod.ONE_MINUTE,
        TimeRange(start_utc=warm_up_end_utc - timedelta(days=7), end_utc=warm_up_end_utc),
    )
    warm_up_bars = live_node.inputs[0].warm_up_bars
    assert len(warm_up_bars) == 7 * 24 * 60
    assert warm_up_bars[-1].start_utc == warm_up_end_utc - timedelta(minutes=1)
    # The child saves the warm-up bars in the bar store, so a same-period backtest can use them.
    with psycopg.connect(database_url) as connection:
        assert connection.execute("SELECT count(*) FROM bar").fetchall() == [(7 * 24 * 60,)]
        assert connection.execute("SELECT start_utc, end_utc FROM bar_saved_range").fetchall() == [
            (warm_up_end_utc - timedelta(days=7), warm_up_end_utc)
        ]


@pytest.mark.anyio
async def test_a_failed_warm_up_read_starts_the_live_node_without_warm_up_bars(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    gateway_connection = make_forward_test_gateway()
    gateway_connection.historical_bars_error_message = "Error 162: no market data permissions"
    live_node = FakeLiveNode(gateway_connection)

    exit_code, _ = await run_child(
        make_settings(database_url, frontend_build_dir), forward_test["id"], "run", live_node
    )

    assert exit_code == 0
    assert live_node.inputs[0].warm_up_bars == ()


@pytest.mark.anyio
async def test_a_restart_that_runs_again_clears_the_crash_message(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_forward_test(web_client)
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            "UPDATE forward_test SET error_message = 'The forward test process ended with exit code 1.' WHERE id = %s",
            [forward_test["id"]],
        )
    live_node = FakeLiveNode(make_forward_test_gateway())
    run_fake_live_node = live_node.run_live_node
    states_at_start: list[tuple[str, str | None]] = []

    async def run_live_node(live_node_input: LiveNodeInput, stop_requested: asyncio.Event) -> LiveNodeEnd:
        listed = (await web_client.get(FORWARD_TESTS_PATH)).json()[0]
        states_at_start.append((listed["status"], listed["error_message"]))
        return await run_fake_live_node(live_node_input, stop_requested)

    live_node.run_live_node = run_live_node  # pyright: ignore[reportAttributeAccessIssue]

    await run_child(make_settings(database_url, frontend_build_dir), forward_test["id"], "run", live_node)

    assert states_at_start == [("running", None)]


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
async def test_a_paper_account_without_a_usd_balance_starts_no_live_node(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_old_forward_test(web_client, database_url)
    gateway_connection = make_forward_test_gateway()
    gateway_connection.account_values = []
    live_node = FakeLiveNode(gateway_connection)

    exit_code, _ = await run_child(
        make_settings(database_url, frontend_build_dir), forward_test["id"], "run", live_node
    )

    # The equity of the records starts at the balance, so a forward test without it cannot record (section 12.8).
    assert exit_code == PAPER_CHECK_FAILED_EXIT_CODE
    assert live_node.inputs == []
    listed = (await web_client.get(FORWARD_TESTS_PATH)).json()[0]
    assert listed["error_message"] == (
        "The paper account has no NetLiquidation value in USD. IBKR sent no NetLiquidation value for the paper account."
    )


def make_eur_account_values() -> list[AccountValue]:
    return [
        AccountValue(account=ACCOUNT_ID, tag="NetLiquidation", value="1000.00", currency="EUR"),
        AccountValue(account=ACCOUNT_ID, tag="TotalCashValue", value="1000.00", currency="EUR"),
    ]


@pytest.mark.anyio
async def test_a_eur_paper_account_starts_with_the_balance_converted_to_usd(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_old_forward_test(web_client, database_url)
    gateway_connection = make_forward_test_gateway()
    gateway_connection.account_values = make_eur_account_values()
    gateway_connection.exchange_rates = {("EUR", "USD"): Decimal("1.1139")}
    live_node = FakeLiveNode(gateway_connection)

    exit_code, _ = await run_child(
        make_settings(database_url, frontend_build_dir), forward_test["id"], "run", live_node
    )

    assert exit_code == 0
    [live_node_input] = live_node.inputs
    assert live_node_input.start_balance_usd == Decimal("1113.90")
    listed = (await web_client.get(FORWARD_TESTS_PATH)).json()[0]
    assert listed["start_balance_usd"] == "1113.90"


@pytest.mark.anyio
async def test_a_eur_paper_account_without_an_exchange_rate_starts_no_live_node(
    web_client: httpx.AsyncClient, database_url: str, frontend_build_dir: Path
) -> None:
    forward_test = await start_old_forward_test(web_client, database_url)
    gateway_connection = make_forward_test_gateway()
    gateway_connection.account_values = make_eur_account_values()
    gateway_connection.exchange_rate_error_message = "No market data permissions."
    live_node = FakeLiveNode(gateway_connection)

    exit_code, _ = await run_child(
        make_settings(database_url, frontend_build_dir), forward_test["id"], "run", live_node
    )

    assert exit_code == PAPER_CHECK_FAILED_EXIT_CODE
    assert live_node.inputs == []
    listed = (await web_client.get(FORWARD_TESTS_PATH)).json()[0]
    assert listed["error_message"] == (
        "The paper account has no NetLiquidation value in USD. The paper account has the base currency EUR and IBKR "
        "sent no EUR to USD exchange rate: No market data permissions."
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
        {"reason": "gateway", "started_at_utc": "2026-01-02T03:10:30Z", "ended_at_utc": "2026-01-02T03:10:30Z"}
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
