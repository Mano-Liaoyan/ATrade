"""Contract test: the same assertions run against the IBKR fake and against the real IBKR paper account.

CI runs only the fake. The real case has the mark `ibkr_paper` and the default pytest options leave it out.
Run it by hand: `uv run pytest -m ibkr_paper`. It reads the repository `.env` file and the environment.
The Gateway API port is not published outside the Compose network, so set ATRADE_IBKR_HOST and
ATRADE_IBKR_PAPER_PORT to an address that this machine can reach, for example an SSH tunnel.
The case skips when `.env`, the account ID, or the Gateway is not available.
"""

import socket
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import anyio
import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict

from atrade.foundation.bar import BarPeriod, TimeRange, floor_to_bar_start
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection, GatewayRequestError, IbAsyncGatewayConnection
from tests.fakes.ibkr import FakeGatewayConnection, make_balance_values, make_stock_position

REPOSITORY_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
FAKE_ACCOUNT_ID = "DU1234567"
# Not the Web client ID (1), not in the forward test range (10-13), and not a multiple of 1000.
CONTRACT_TEST_CLIENT_ID = 99
CONNECT_WAIT_SECONDS = 30
GATEWAY_PROBE_TIMEOUT_SECONDS = 3


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


@pytest.fixture(params=["fake", pytest.param("ibkr_paper", marks=pytest.mark.ibkr_paper)])
def connection_and_account(request: pytest.FixtureRequest) -> tuple[GatewayConnection, str]:
    if request.param == "fake":
        fake = FakeGatewayConnection(managed_accounts=[FAKE_ACCOUNT_ID])
        fake.account_values = make_balance_values(FAKE_ACCOUNT_ID, net_liquidation_usd="100000.00", cash_usd="99000")
        fake.portfolio = [make_stock_position(FAKE_ACCOUNT_ID, symbol="AAPL", quantity="10", market_price="100")]
        return fake, FAKE_ACCOUNT_ID
    if not REPOSITORY_ENV_FILE.exists():
        pytest.skip(f"{REPOSITORY_ENV_FILE} does not exist.")
    settings = PaperAccountTestSettings()
    if settings.ibkr_account_id is None:
        pytest.skip("ATRADE_IBKR_ACCOUNT_ID is not set.")
    if not can_open_tcp_connection(settings.ibkr_host, settings.ibkr_paper_port):
        pytest.skip(f"IB Gateway is not reachable at {settings.ibkr_host}:{settings.ibkr_paper_port}.")
    connection = IbAsyncGatewayConnection(
        host=settings.ibkr_host, port=settings.ibkr_paper_port, client_id=CONTRACT_TEST_CLIENT_ID
    )
    return connection, settings.ibkr_account_id


async def wait_until_connected(connection: GatewayConnection) -> None:
    with anyio.fail_after(CONNECT_WAIT_SECONDS):
        while not connection.is_connected():
            await anyio.sleep(0.05)


@pytest.mark.anyio
async def test_connects_and_reads_the_paper_account(connection_and_account: tuple[GatewayConnection, str]) -> None:
    connection, account_id = connection_and_account

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(connection.keep_connected)
        await wait_until_connected(connection)
        assert account_id in connection.read_managed_accounts()
        assert account_id.startswith("DU")
        task_group.cancel_scope.cancel()
    connection.disconnect()


@pytest.mark.anyio
async def test_reports_not_connected_after_disconnect(connection_and_account: tuple[GatewayConnection, str]) -> None:
    connection, _account_id = connection_and_account

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(connection.keep_connected)
        await wait_until_connected(connection)
        task_group.cancel_scope.cancel()
    connection.disconnect()

    assert not connection.is_connected()
    assert connection.read_managed_accounts() == []


@pytest.mark.anyio
async def test_returns_exactly_the_paper_account_from_managed_accounts(
    connection_and_account: tuple[GatewayConnection, str],
) -> None:
    connection, account_id = connection_and_account

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(connection.keep_connected)
        await wait_until_connected(connection)
        assert connection.read_managed_accounts() == [account_id]
        assert connection.read_connection_number() >= 1
        task_group.cancel_scope.cancel()
    connection.disconnect()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("query", "expected_instrument"),
    [
        ("AAPL", Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")),
        ("700", Instrument(symbol="700", exchange="SEHK", currency="HKD")),
    ],
)
async def test_finds_stocks_by_symbol_with_exchange_and_currency(
    connection_and_account: tuple[GatewayConnection, str], query: str, expected_instrument: Instrument
) -> None:
    connection, _account_id = connection_and_account

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(connection.keep_connected)
        await wait_until_connected(connection)
        instruments = await connection.search_instruments(query)
        assert expected_instrument in instruments
        task_group.cancel_scope.cancel()
    connection.disconnect()


@pytest.mark.anyio
async def test_reads_the_balance_and_the_positions_of_the_paper_account(
    connection_and_account: tuple[GatewayConnection, str],
) -> None:
    connection, account_id = connection_and_account

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(connection.keep_connected)
        await wait_until_connected(connection)
        # ib_async reports "connected" before the first account update arrives.
        with anyio.fail_after(CONNECT_WAIT_SECONDS):
            while not connection.read_account_values():
                await anyio.sleep(0.05)
        net_liquidation_values = [
            Decimal(value.value)
            for value in connection.read_account_values()
            if value.account == account_id and value.tag == "NetLiquidation" and value.currency == "USD"
        ]
        positions = connection.read_portfolio()
        assert len(net_liquidation_values) == 1
        assert net_liquidation_values[0] > 0
        assert all(position.account == account_id for position in positions)
        assert all(position.quantity != 0 for position in positions)
        task_group.cancel_scope.cancel()
    connection.disconnect()

    assert connection.read_account_values() == []
    assert connection.read_portfolio() == []


@pytest.mark.anyio
async def test_refuses_a_search_without_a_connection(connection_and_account: tuple[GatewayConnection, str]) -> None:
    connection, _account_id = connection_and_account

    with pytest.raises(GatewayRequestError):
        await connection.search_instruments("AAPL")


# A past week with trading days on NASDAQ. The range covers more than one IBKR step of 1 minute bars (1 day).
HISTORICAL_RANGE = TimeRange(datetime(2026, 3, 2, tzinfo=UTC), datetime(2026, 3, 5, tzinfo=UTC))
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")


@pytest.mark.anyio
@pytest.mark.parametrize("bar_period", [BarPeriod.ONE_MINUTE, BarPeriod.ONE_DAY])
async def test_reads_historical_bars_in_the_range_oldest_first(
    connection_and_account: tuple[GatewayConnection, str], bar_period: BarPeriod
) -> None:
    connection, _account_id = connection_and_account

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(connection.keep_connected)
        await wait_until_connected(connection)
        bars = await connection.read_historical_bars(APPLE, bar_period, HISTORICAL_RANGE)
        bar_starts = [bar.start_utc for bar in bars]
        assert bar_starts == sorted(set(bar_starts))
        assert all(HISTORICAL_RANGE.start_utc <= start_utc < HISTORICAL_RANGE.end_utc for start_utc in bar_starts)
        assert all(start_utc == floor_to_bar_start(start_utc, bar_period) for start_utc in bar_starts)
        assert all(bar.low <= min(bar.open, bar.close) and bar.high >= max(bar.open, bar.close) for bar in bars)
        assert {start_utc.date() for start_utc in bar_starts} == {date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 4)}
        task_group.cancel_scope.cancel()
    connection.disconnect()


@pytest.mark.anyio
async def test_refuses_historical_bars_without_a_connection(
    connection_and_account: tuple[GatewayConnection, str],
) -> None:
    connection, _account_id = connection_and_account

    with pytest.raises(GatewayRequestError):
        await connection.read_historical_bars(APPLE, BarPeriod.ONE_HOUR, HISTORICAL_RANGE)
