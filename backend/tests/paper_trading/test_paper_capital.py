"""fetch_paper_capital_usd(): the paper account balance after a passed check, else the local value from settings."""

from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from atrade.foundation.settings import Settings
from atrade.ibkr import AccountValue
from atrade.paper_trading import PaperAccountMonitor, fetch_paper_capital_usd, require_paper_account
from tests.fakes.ibkr import FakeGatewayConnection, make_balance_values

ACCOUNT_ID = "DU1234567"


def make_monitor(gateway_connection: FakeGatewayConnection) -> PaperAccountMonitor:
    settings = Settings(
        database_url="postgresql://unused/atrade",
        frontend_build_dir=Path("/unused"),
        ibkr_account_id=ACCOUNT_ID,
        local_paper_capital_usd=Decimal(50000),
    )
    return PaperAccountMonitor(settings=settings, gateway_connection=gateway_connection)


def make_gateway(managed_accounts: list[str], *, connected: bool) -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=managed_accounts)
    gateway_connection.account_values = make_balance_values(
        ACCOUNT_ID, net_liquidation_usd="123456.78", cash_usd="1000"
    )
    gateway_connection.connected = connected
    return gateway_connection


@pytest.mark.anyio
async def test_paper_capital_is_the_paper_account_balance_after_a_passed_check() -> None:
    monitor = make_monitor(make_gateway([ACCOUNT_ID], connected=True))

    assert await fetch_paper_capital_usd(monitor) == Decimal("123456.78")


@pytest.mark.anyio
async def test_paper_capital_is_the_local_value_when_the_gateway_is_not_connected() -> None:
    monitor = make_monitor(make_gateway([ACCOUNT_ID], connected=False))

    assert await fetch_paper_capital_usd(monitor) == Decimal(50000)


@pytest.mark.anyio
async def test_paper_capital_is_the_local_value_when_the_check_fails() -> None:
    monitor = make_monitor(make_gateway(["DU7654321"], connected=True))

    assert await fetch_paper_capital_usd(monitor) == Decimal(50000)


@pytest.mark.anyio
async def test_paper_capital_is_the_eur_balance_in_usd() -> None:
    gateway_connection = make_gateway([ACCOUNT_ID], connected=True)
    gateway_connection.account_values = [
        AccountValue(account=ACCOUNT_ID, tag="NetLiquidation", value="1000.00", currency="EUR"),
    ]
    gateway_connection.exchange_rates = {("EUR", "USD"): Decimal("1.1139")}

    assert await fetch_paper_capital_usd(make_monitor(gateway_connection)) == Decimal("1113.90")


@pytest.mark.anyio
async def test_paper_capital_is_the_local_value_without_an_exchange_rate() -> None:
    gateway_connection = make_gateway([ACCOUNT_ID], connected=True)
    gateway_connection.account_values = [
        AccountValue(account=ACCOUNT_ID, tag="NetLiquidation", value="1000.00", currency="EUR"),
    ]

    assert await fetch_paper_capital_usd(make_monitor(gateway_connection)) == Decimal(50000)


@pytest.mark.anyio
async def test_paper_capital_route_returns_the_local_value_without_a_passed_check(
    web_client: httpx.AsyncClient,
) -> None:
    # The web_client settings have no IBKR account ID, so the paper account check does not pass.
    response = await web_client.get("/api/paper-trading/paper-capital")

    assert response.status_code == 200
    assert response.json() == {"paper_capital_usd": "100000"}


def test_require_paper_account_returns_the_checked_account() -> None:
    gateway_connection = make_gateway([ACCOUNT_ID], connected=True)
    monitor = make_monitor(gateway_connection)

    assert require_paper_account(settings=monitor.settings, gateway_connection=gateway_connection) == ACCOUNT_ID
    assert monitor.require_checked_paper_account() == ACCOUNT_ID


def test_orders_are_refused_without_a_checked_paper_account() -> None:
    monitor = make_monitor(make_gateway([ACCOUNT_ID], connected=False))

    with pytest.raises(PermissionError, match="not connected"):
        monitor.require_checked_paper_account()
