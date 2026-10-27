"""fetch_paper_capital_usd(): the paper account balance after a passed check, else the local value from settings."""

from decimal import Decimal
from pathlib import Path

import pytest

from atrade.foundation.settings import Settings
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


def test_paper_capital_is_the_paper_account_balance_after_a_passed_check() -> None:
    monitor = make_monitor(make_gateway([ACCOUNT_ID], connected=True))

    assert fetch_paper_capital_usd(monitor) == Decimal("123456.78")


def test_paper_capital_is_the_local_value_when_the_gateway_is_not_connected() -> None:
    monitor = make_monitor(make_gateway([ACCOUNT_ID], connected=False))

    assert fetch_paper_capital_usd(monitor) == Decimal(50000)


def test_paper_capital_is_the_local_value_when_the_check_fails() -> None:
    monitor = make_monitor(make_gateway(["DU7654321"], connected=True))

    assert fetch_paper_capital_usd(monitor) == Decimal(50000)


def test_require_paper_account_returns_the_checked_account() -> None:
    gateway_connection = make_gateway([ACCOUNT_ID], connected=True)
    monitor = make_monitor(gateway_connection)

    assert require_paper_account(settings=monitor.settings, gateway_connection=gateway_connection) == ACCOUNT_ID
    assert monitor.require_checked_paper_account() == ACCOUNT_ID


def test_orders_are_refused_without_a_checked_paper_account() -> None:
    monitor = make_monitor(make_gateway([ACCOUNT_ID], connected=False))

    with pytest.raises(PermissionError, match="not connected"):
        monitor.require_checked_paper_account()
