"""PaperAccountMonitor.read_balance(): the balance in USD for a paper account with any base currency (section 11.9).

ATrade keeps money in USD. A paper account with the base currency EUR has NetLiquidation and TotalCashValue only in
EUR, so ATrade converts them with an exchange rate from IBKR.
"""

import time
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import pytest

from atrade.foundation.settings import Settings
from atrade.ibkr import AccountValue
from atrade.paper_trading import PaperAccountMonitor
from tests.fakes.ibkr import FakeGatewayConnection, make_balance_values

ACCOUNT_ID = "DU1234567"


def make_monitor(
    gateway_connection: FakeGatewayConnection, read_monotonic_seconds: Callable[[], float] = time.monotonic
) -> PaperAccountMonitor:
    settings = Settings(
        database_url="postgresql://unused/atrade",
        frontend_build_dir=Path("/unused"),
        ibkr_account_id=ACCOUNT_ID,
    )
    return PaperAccountMonitor(
        settings=settings, gateway_connection=gateway_connection, read_monotonic_seconds=read_monotonic_seconds
    )


def make_eur_gateway() -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID])
    # The values of the real EUR paper account: NetLiquidation only in EUR, the ledger rows in BASE and EUR.
    gateway_connection.account_values = [
        AccountValue(account=ACCOUNT_ID, tag="NetLiquidation", value="100000.00", currency="EUR"),
        AccountValue(account=ACCOUNT_ID, tag="TotalCashValue", value="80000.00", currency="EUR"),
        AccountValue(account=ACCOUNT_ID, tag="$LEDGER-ExchangeRate", value="1.00", currency="BASE"),
        AccountValue(account=ACCOUNT_ID, tag="$LEDGER-ExchangeRate", value="1.00", currency="EUR"),
        AccountValue(account=ACCOUNT_ID, tag="AccountType", value="INDIVIDUAL", currency=""),
    ]
    gateway_connection.connected = True
    return gateway_connection


@pytest.mark.anyio
async def test_usd_account_balance_needs_no_exchange_rate() -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=[ACCOUNT_ID])
    gateway_connection.account_values = make_balance_values(ACCOUNT_ID, net_liquidation_usd="5000.5", cash_usd="10")
    gateway_connection.connected = True

    balance = await make_monitor(gateway_connection).read_balance()

    assert balance is not None
    assert balance.net_liquidation_usd == Decimal("5000.5")
    assert balance.cash_usd == Decimal(10)
    assert balance.base_currency == "USD"
    assert balance.usd_per_base_unit == Decimal(1)
    assert balance.exchange_rate_source == "base_currency_is_usd"
    assert balance.message is None
    assert gateway_connection.exchange_rate_requests == []


@pytest.mark.anyio
async def test_eur_account_balance_is_converted_with_the_ibkr_forex_rate() -> None:
    gateway_connection = make_eur_gateway()
    gateway_connection.exchange_rates = {("EUR", "USD"): Decimal("1.1139")}

    balance = await make_monitor(gateway_connection).read_balance()

    assert balance is not None
    assert balance.net_liquidation_usd == Decimal("111390.00")
    assert balance.cash_usd == Decimal("89112.00")
    assert balance.base_currency == "EUR"
    assert balance.net_liquidation_base == Decimal("100000.00")
    assert balance.usd_per_base_unit == Decimal("1.1139")
    assert balance.exchange_rate_source == "ibkr_forex"
    assert balance.message is None


@pytest.mark.anyio
async def test_eur_account_balance_uses_the_account_exchange_rate_for_usd_first() -> None:
    gateway_connection = make_eur_gateway()
    # IBKR sends ExchangeRate per ledger currency: the base currency units for 1 unit of that currency.
    gateway_connection.account_values.append(
        AccountValue(account=ACCOUNT_ID, tag="$LEDGER-ExchangeRate", value="0.8", currency="USD")
    )
    gateway_connection.exchange_rates = {("EUR", "USD"): Decimal("1.1139")}

    balance = await make_monitor(gateway_connection).read_balance()

    assert balance is not None
    assert balance.net_liquidation_usd == Decimal("125000.00")
    assert balance.usd_per_base_unit == Decimal("1.25")
    assert balance.exchange_rate_source == "account"
    assert gateway_connection.exchange_rate_requests == []


@pytest.mark.anyio
async def test_eur_account_balance_has_no_usd_values_without_an_exchange_rate() -> None:
    gateway_connection = make_eur_gateway()
    gateway_connection.exchange_rate_error_message = "No market data permissions for IDEALPRO CASH."

    balance = await make_monitor(gateway_connection).read_balance()

    assert balance is not None
    assert balance.net_liquidation_usd is None
    assert balance.cash_usd is None
    assert balance.base_currency == "EUR"
    assert balance.net_liquidation_base == Decimal("100000.00")
    assert balance.usd_per_base_unit is None
    assert balance.exchange_rate_source is None
    assert balance.message == (
        "The paper account has the base currency EUR and IBKR sent no EUR to USD exchange rate: "
        "No market data permissions for IDEALPRO CASH."
    )


@pytest.mark.anyio
async def test_exchange_rate_is_read_again_only_after_its_maximum_age() -> None:
    gateway_connection = make_eur_gateway()
    gateway_connection.exchange_rates = {("EUR", "USD"): Decimal("1.1139")}
    now = [1000.0]
    monitor = make_monitor(gateway_connection, lambda: now[0])

    await monitor.read_balance()
    now[0] += 59
    await monitor.read_balance()
    first_request_count = len(gateway_connection.exchange_rate_requests)
    now[0] += 2
    gateway_connection.exchange_rates = {("EUR", "USD"): Decimal("1.2")}
    balance = await monitor.read_balance()

    assert first_request_count == 1
    assert len(gateway_connection.exchange_rate_requests) == 2
    assert balance is not None
    assert balance.usd_per_base_unit == Decimal("1.2")


@pytest.mark.anyio
async def test_a_new_connection_reads_the_exchange_rate_again() -> None:
    gateway_connection = make_eur_gateway()
    gateway_connection.exchange_rates = {("EUR", "USD"): Decimal("1.1139")}
    monitor = make_monitor(gateway_connection)

    await monitor.read_balance()
    gateway_connection.connected = False
    gateway_connection.connected = True
    await monitor.read_balance()

    assert len(gateway_connection.exchange_rate_requests) == 2
