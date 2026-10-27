"""Contract test of a forward test on the real IBKR paper account (docs/architecture.md section 17.4). Run by hand.

The IB execution client of a real LiveNode sends a limit order far from the market price. The Web connection sees it
with reqAllOpenOrders and reads the forward test ID from orderRef. The stop cancels the order.
Run: `uv run pytest -m ibkr_paper tests/forward_test`. It needs ATRADE_TEST_DATABASE_URL, the repository `.env`,
and IB Gateway at ATRADE_IBKR_HOST:ATRADE_IBKR_PAPER_PORT (an SSH tunnel, see tests/ibkr). Without them it skips.
"""

import asyncio
import hashlib
import socket
from pathlib import Path

import anyio
import psycopg
import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict

from atrade.forward_test import IbkrAccess, run_forward_test_child, run_live_node
from atrade.foundation.order_ref import read_order_source
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, IbAsyncGatewayConnection, OpenOrder

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


def insert_forward_test(database_url: str) -> int:
    """The rows that the start route writes, with client ID 10 and the far limit order strategy."""
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
                created_at_utc
            ) VALUES (%(strategy_version_id)s, 'AAPL', 'NASDAQ', 'USD', '1-MINUTE', 'running', 'running', 10, now())
            RETURNING id
            """,
            {"strategy_version_id": version_row[0]},
        ).fetchone()
    assert forward_test_row is not None
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
    paper_settings: Settings,
) -> None:
    forward_test_id = insert_forward_test(paper_settings.database_url)
    web_connection = IbAsyncGatewayConnection(
        host=paper_settings.ibkr_host, port=paper_settings.ibkr_paper_port, client_id=WEB_SIDE_CLIENT_ID
    )
    await web_connection.connect()
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
    web_connection.disconnect()

    assert exit_code == 0
    assert [(order.client_id, order.instrument.symbol, order.limit_price) for order in open_orders] == [(10, "AAPL", 1)]
    assert orders_after_stop == []
