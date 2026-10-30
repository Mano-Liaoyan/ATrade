"""Contract test of a forward test on the real IBKR paper account (docs/architecture.md section 17.4). Run by hand.

The IB execution client of a real LiveNode sends a limit order far from the market price. The Web connection sees it
with reqAllOpenOrders and reads the forward test ID from orderRef. The stop cancels the order. After `kill -9` of the
child process, the worker restarts it with the same client ID, and the restart cancels the old order (section 12.7).
The last test runs the IB data client and the ATrade execution client with one client ID (section 12.24).
Run: `uv run pytest -m ibkr_paper tests/forward_test`. It needs ATRADE_TEST_DATABASE_URL, the repository `.env`,
and IB Gateway at ATRADE_IBKR_HOST:ATRADE_IBKR_PAPER_PORT (an SSH tunnel, see tests/ibkr). Without them it skips.
"""

import asyncio
import hashlib
import socket
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path

import anyio
import psycopg
import pytest
from nautilus_trader.adapters.interactive_brokers import (
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersDataClientFactory,
    InteractiveBrokersInstrumentProviderConfig,
)
from nautilus_trader.common import Environment
from nautilus_trader.config import StrategyConfig
from nautilus_trader.live import LiveExecutionEngineConfig, LiveNode, LiveNodeBuilder, LiveNodeConfig
from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType, InstrumentId, OrderSide, Price, Quantity, TraderId
from nautilus_trader.trading import Strategy
from pydantic_settings import BaseSettings, SettingsConfigDict

from atrade.app.forward_test_worker import ForwardTestProcess, start_forward_test_process
from atrade.forward_test import (
    ChildMode,
    ForwardTestWorker,
    IbkrAccess,
    OwnerLedgerExecutionClientFactory,
    OwnerLedgerInput,
    add_atrade_clients,
    run_forward_test_child,
    run_live_node,
)
from atrade.foundation.clock import SystemClock
from atrade.foundation.instrument import Instrument
from atrade.foundation.order_ref import format_forward_test_order_tag, read_order_source
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, IbAsyncGatewayConnection, OpenOrder
from tests.fakes.owner_ledger import FakeOwnerLedger

REPOSITORY_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
# Not the Web client ID (1), not a forward test client ID (10-13), and not a multiple of 1000.
WEB_SIDE_CLIENT_ID = 98
GATEWAY_PROBE_TIMEOUT_SECONDS = 3
ORDER_WAIT_SECONDS = 90
CHILD_STOP_WAIT_SECONDS = 60

# Sends 1 limit order to buy 1 share at 1.00 USD at the start: far from the market price, so it does not fill.
FAR_LIMIT_ORDER_STRATEGY = '''"""Contract test strategy: 1 far limit order at the start."""

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import BarType, InstrumentId, OrderSide, Price, Quantity
from nautilus_trader.trading import Strategy


class FarLimitOrderConfig(StrategyConfig):
    def __init__(self, *, instrument_id: InstrumentId, bar_type: BarType, **kwargs) -> None:
        super().__init__(**kwargs)
        self.instrument_id = instrument_id
        self.bar_type = bar_type


class FarLimitOrderStrategy(Strategy):
    def __init__(self, config: FarLimitOrderConfig) -> None:
        super().__init__(config)
        self.settings = config

    def on_start(self) -> None:
        order = self.order_factory.limit(
            self.settings.instrument_id, OrderSide.BUY, Quantity.from_int(1), Price.from_str("1.00")
        )
        self.submit_order(order)
'''


class PaperAccountTestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATRADE_", env_file=REPOSITORY_ENV_FILE, extra="ignore")

    ibkr_account_id: str | None = None
    ibkr_host: str = "127.0.0.1"
    ibkr_paper_port: int = 4004


def can_open_tcp_connection(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=GATEWAY_PROBE_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False


@pytest.fixture
def paper_settings(database_url: str) -> Settings:
    if not REPOSITORY_ENV_FILE.exists():
        pytest.skip(f"{REPOSITORY_ENV_FILE} does not exist.")
    paper_account = PaperAccountTestSettings()
    if paper_account.ibkr_account_id is None:
        pytest.skip("ATRADE_IBKR_ACCOUNT_ID is not set.")
    if not can_open_tcp_connection(paper_account.ibkr_host, paper_account.ibkr_paper_port):
        pytest.skip(f"IB Gateway is not reachable at {paper_account.ibkr_host}:{paper_account.ibkr_paper_port}.")
    return Settings(
        database_url=database_url,
        ibkr_account_id=paper_account.ibkr_account_id,
        ibkr_host=paper_account.ibkr_host,
        ibkr_paper_port=paper_account.ibkr_paper_port,
    )


@pytest.fixture
async def web_connection(paper_settings: Settings) -> AsyncIterator[GatewayConnection]:
    """The connection of the Web side, which reads the open orders of all client IDs."""
    connection = IbAsyncGatewayConnection(
        host=paper_settings.ibkr_host, port=paper_settings.ibkr_paper_port, client_id=WEB_SIDE_CLIENT_ID
    )
    await connection.connect()
    yield connection
    # A failed test leaves its connection open. IB Gateway then refuses the client ID in the next test (error 326).
    connection.disconnect()


def insert_forward_test(database_url: str, account: str) -> int:
    """The rows that the start route writes, with client ID 10, the far limit order strategy, and 10000 USD allocated
    capital that "By hand" gives to the forward test in the owner ledger (forward_test.md section 12.18)."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        strategy_row = connection.execute(
            "INSERT INTO strategy (name, created_at_utc) VALUES ('Far limit order', now()) RETURNING id"
        ).fetchone()
        assert strategy_row is not None
        version_row = connection.execute(
            """
            INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc)
            VALUES (%(strategy_id)s, 1, %(code)s, %(code_sha256)s, now()) RETURNING id
            """,
            {
                "strategy_id": strategy_row[0],
                "code": FAR_LIMIT_ORDER_STRATEGY,
                "code_sha256": hashlib.sha256(FAR_LIMIT_ORDER_STRATEGY.encode()).hexdigest(),
            },
        ).fetchone()
        assert version_row is not None
        forward_test_row = connection.execute(
            """
            INSERT INTO forward_test (
                strategy_version_id, symbol, exchange, currency, bar_period, desired_state, status, client_id,
                created_at_utc, allocated_capital_usd
            ) VALUES (
                %(strategy_version_id)s, 'AAPL', 'NASDAQ', 'USD', '1-MINUTE', 'running', 'running', 10, now(), 10000
            )
            RETURNING id
            """,
            {"strategy_version_id": version_row[0]},
        ).fetchone()
        assert forward_test_row is not None
        connection.execute(
            """
            INSERT INTO owner_ledger_entry (owner_kind, forward_test_id, entry_kind, time_utc, account, currency,
                quantity_change, cash_change)
            VALUES ('by_hand', NULL, 'transfer', now(), %(account)s, 'USD', 0, -10000),
                ('forward_test', %(id)s, 'transfer', now(), %(account)s, 'USD', 0, 10000)
            """,
            {"account": account, "id": forward_test_row[0]},
        )
    return int(forward_test_row[0])


async def wait_for_forward_test_orders(
    web_connection: GatewayConnection, forward_test_id: int, *, is_open: bool
) -> list[OpenOrder]:
    with anyio.fail_after(ORDER_WAIT_SECONDS):
        while True:
            orders = [
                order
                for order in await web_connection.read_open_orders()
                if read_order_source(order.order_ref).forward_test_id == forward_test_id
            ]
            if bool(orders) == is_open:
                return orders
            await anyio.sleep(1)


@pytest.mark.anyio
@pytest.mark.ibkr_paper
async def test_the_forward_test_order_shows_its_forward_test_id_and_the_stop_cancels_it(
    paper_settings: Settings, web_connection: GatewayConnection
) -> None:
    forward_test_id = insert_forward_test(paper_settings.database_url, paper_settings.ibkr_account_id or "")
    stop_requested = asyncio.Event()

    def open_gateway_connection(client_id: int) -> GatewayConnection:
        return IbAsyncGatewayConnection(
            host=paper_settings.ibkr_host, port=paper_settings.ibkr_paper_port, client_id=client_id
        )

    child_task = asyncio.create_task(
        run_forward_test_child(
            settings=paper_settings,
            forward_test_id=forward_test_id,
            mode="run",
            ibkr_access=IbkrAccess(open_gateway_connection=open_gateway_connection, run_live_node=run_live_node),
            stop_requested=stop_requested,
        )
    )
    try:
        open_orders = await wait_for_forward_test_orders(web_connection, forward_test_id, is_open=True)
    finally:
        stop_requested.set()
    exit_code = await asyncio.wait_for(child_task, CHILD_STOP_WAIT_SECONDS)
    orders_after_stop = await wait_for_forward_test_orders(web_connection, forward_test_id, is_open=False)

    assert exit_code == 0
    assert [(order.client_id, order.instrument.symbol, order.limit_price) for order in open_orders] == [(10, "AAPL", 1)]
    assert orders_after_stop == []


def read_status_and_client_id(database_url: str, forward_test_id: int) -> tuple[str, int | None]:
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            "SELECT status, client_id FROM forward_test WHERE id = %(id)s", {"id": forward_test_id}
        ).fetchone()
    assert row is not None
    return str(row[0]), row[1]


async def compare_until(worker: ForwardTestWorker, database_url: str, forward_test_id: int, status: str) -> None:
    with anyio.fail_after(ORDER_WAIT_SECONDS):
        while read_status_and_client_id(database_url, forward_test_id)[0] != status:
            await worker.compare_states()
            await anyio.sleep(1)


@pytest.mark.anyio
@pytest.mark.ibkr_paper
async def test_after_kill_9_the_worker_restarts_with_the_same_client_id_and_cancels_the_old_order(
    paper_settings: Settings, web_connection: GatewayConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The child processes read the settings from the environment, like in the forward-test service.
    monkeypatch.setenv("DATABASE_URL", paper_settings.database_url)
    monkeypatch.setenv("ATRADE_IBKR_ACCOUNT_ID", paper_settings.ibkr_account_id or "")
    monkeypatch.setenv("ATRADE_IBKR_HOST", paper_settings.ibkr_host)
    monkeypatch.setenv("ATRADE_IBKR_PAPER_PORT", str(paper_settings.ibkr_paper_port))
    forward_test_id = insert_forward_test(paper_settings.database_url, paper_settings.ibkr_account_id or "")
    processes: list[ForwardTestProcess] = []

    async def start_child(forward_test_id: int, mode: ChildMode) -> ForwardTestProcess:
        process = await start_forward_test_process(forward_test_id, mode)
        processes.append(process)
        return process

    worker = ForwardTestWorker(database_url=paper_settings.database_url, clock=SystemClock(), start_child=start_child)
    try:
        await worker.compare_states()
        [first_order] = await wait_for_forward_test_orders(web_connection, forward_test_id, is_open=True)

        processes[0].process.kill()
        await processes[0].process.wait()
        # The worker sees the crash and starts a new run child. Its strategy sends a new order at the start.
        await worker.compare_states()
        await compare_until(worker, paper_settings.database_url, forward_test_id, "running")
        with anyio.fail_after(ORDER_WAIT_SECONDS):
            while True:
                orders = await wait_for_forward_test_orders(web_connection, forward_test_id, is_open=True)
                if first_order.order_id not in [order.order_id for order in orders]:
                    break
                await anyio.sleep(1)
        assert [order.client_id for order in orders] == [10]
        assert read_status_and_client_id(paper_settings.database_url, forward_test_id) == ("running", 10)
    finally:
        with psycopg.connect(paper_settings.database_url, autocommit=True) as connection:
            connection.execute(
                "UPDATE forward_test SET desired_state = 'stopped' WHERE id = %(id)s", {"id": forward_test_id}
            )
        await compare_until(worker, paper_settings.database_url, forward_test_id, "stopped")
    orders_after_stop = await wait_for_forward_test_orders(web_connection, forward_test_id, is_open=False)

    assert len(processes) == 2
    assert orders_after_stop == []
    assert read_status_and_client_id(paper_settings.database_url, forward_test_id) == ("stopped", None)


SHARED_CLIENT_ID = 13
SHARED_CLIENT_FORWARD_TEST_ID = 913
SHARED_CLIENT_BAR_TYPE = "AAPL.NASDAQ-1-MINUTE-LAST-EXTERNAL"
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")


class SharedClientIdConfig(StrategyConfig):
    pass


class SharedClientIdStrategy(Strategy):
    """Subscribes to 1-minute bars (IB data client) and sends 1 far limit order (ATrade execution client)."""

    def __init__(self, config: SharedClientIdConfig) -> None:
        super().__init__(config)
        self.bar_count = 0

    def on_start(self) -> None:
        bar_type = BarType.from_str(SHARED_CLIENT_BAR_TYPE)
        self.subscribe_bars(bar_type)  # pyright: ignore[reportUnknownMemberType]
        order = self.order_factory.limit(  # pyright: ignore[reportUnknownMemberType]
            bar_type.instrument_id, OrderSide.BUY, Quantity.from_int(1), Price.from_str("1.00")
        )
        self.submit_order(order)  # pyright: ignore[reportUnknownMemberType]

    def on_bar(self, bar: NautilusBar) -> None:
        self.bar_count += 1


def build_shared_client_id_node(paper_settings: Settings, ledger: FakeOwnerLedger) -> LiveNode:
    """The IB data client and the ATrade execution client with the same client ID (section 12.24)."""
    instrument_id = InstrumentId.from_str("AAPL.NASDAQ")
    config = LiveNodeConfig(
        environment=Environment.LIVE,
        trader_id=TraderId(f"ATRADE-{SHARED_CLIENT_FORWARD_TEST_ID}"),
        exec_engine=LiveExecutionEngineConfig(reconciliation=True),
    )
    builder = LiveNodeBuilder.from_config("shared-client-id", config)  # pyright: ignore[reportUnknownMemberType]
    builder = builder.add_data_client(
        "IB",
        InteractiveBrokersDataClientFactory(),
        InteractiveBrokersDataClientConfig(
            host=paper_settings.ibkr_host,
            port=paper_settings.ibkr_paper_port,
            client_id=SHARED_CLIENT_ID,
            instrument_provider=InteractiveBrokersInstrumentProviderConfig(load_ids={instrument_id}),
        ),
    )
    gateway = IbAsyncGatewayConnection(
        host=paper_settings.ibkr_host, port=paper_settings.ibkr_paper_port, client_id=SHARED_CLIENT_ID
    )
    execution_factory = OwnerLedgerExecutionClientFactory(
        OwnerLedgerInput(
            forward_test_id=SHARED_CLIENT_FORWARD_TEST_ID,
            client_id=SHARED_CLIENT_ID,
            account_id=paper_settings.ibkr_account_id or "",
            instruments=(APPLE,),
        ),
        ledger,
        gateway,
    )
    return add_atrade_clients(builder, None, execution_factory).build()


async def cancel_own_orders(paper_settings: Settings, client_id: int) -> None:
    """Restart step 1 (section 12.7): only the client ID of an order can cancel it."""
    connection = IbAsyncGatewayConnection(
        host=paper_settings.ibkr_host, port=paper_settings.ibkr_paper_port, client_id=client_id
    )
    await connection.connect()
    try:
        for order in await connection.read_own_open_orders():
            await connection.cancel_order_and_wait(order.order_id)
    finally:
        connection.disconnect()


@pytest.mark.anyio
@pytest.mark.ibkr_paper
async def test_the_ib_data_client_and_the_atrade_execution_client_can_share_the_client_id(
    paper_settings: Settings, web_connection: GatewayConnection
) -> None:
    """Section 12.24: one client ID cannot have 2 connections. The IB data client and the `ib_async` connection of
    the ATrade execution client both use it. The node must get bars and send the order."""
    live_node = build_shared_client_id_node(paper_settings, FakeOwnerLedger(cash_usd=Decimal(100000)))
    strategy = SharedClientIdStrategy(
        SharedClientIdConfig(order_id_tag=format_forward_test_order_tag(SHARED_CLIENT_FORWARD_TEST_ID))  # pyright: ignore[reportCallIssue]
    )
    live_node.add_strategy(strategy)
    run_task = asyncio.create_task(live_node.run_async())
    try:
        open_orders = await wait_for_forward_test_orders(web_connection, SHARED_CLIENT_FORWARD_TEST_ID, is_open=True)
        with anyio.fail_after(ORDER_WAIT_SECONDS):
            while strategy.bar_count == 0:
                await anyio.sleep(1)
    finally:
        live_node.handle().stop()
        await asyncio.wait_for(run_task, CHILD_STOP_WAIT_SECONDS)
        live_node.dispose()
        await cancel_own_orders(paper_settings, SHARED_CLIENT_ID)

    assert [order.client_id for order in open_orders] == [SHARED_CLIENT_ID]
    assert strategy.bar_count > 0
