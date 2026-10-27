"""The paper account state of the Web process: the check result in memory, the balance, and the positions.

The check runs once after each connection and reconnection. A lost connection clears the result (section 11.2).
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

import anyio

from atrade.foundation.settings import Settings
from atrade.ibkr import AccountValue, GatewayConnection, GatewayRequestError, PortfolioPosition
from atrade.paper_trading.paper_account_check import PaperAccountCheck, PaperAccountCheckError, check_paper_account

REFRESH_INTERVAL_SECONDS = 0.5
NET_LIQUIDATION_TAG = "NetLiquidation"
CASH_TAG = "TotalCashValue"
BALANCE_CURRENCY = "USD"
# IBKR sends one ExchangeRate row per currency of the account ledger: the base currency units for 1 unit of that
# currency. reqAccountUpdates sends it with the "$LEDGER-" prefix.
EXCHANGE_RATE_TAGS = ("ExchangeRate", "$LEDGER-ExchangeRate")
# Currency names of account values that are not a real currency: "BASE" is the sum in the base currency.
NOT_A_CURRENCY = ("", "BASE")
# The IBKR forex rate is read again after this time, and after each new connection (section 11.9).
EXCHANGE_RATE_MAX_AGE_SECONDS = 60.0
USD_CENT = Decimal("0.01")

type ExchangeRateSource = Literal["base_currency_is_usd", "account", "ibkr_forex"]

logger = logging.getLogger("atrade.paper_trading")


@dataclass(frozen=True)
class PaperAccountBalance:
    """The balance in USD, and the values in the base currency of the account that ATrade converted (section 11.9).

    The USD values are None when no exchange rate is available. `message` then tells why.
    """

    net_liquidation_usd: Decimal | None
    cash_usd: Decimal | None
    base_currency: str | None
    net_liquidation_base: Decimal | None
    cash_base: Decimal | None
    usd_per_base_unit: Decimal | None
    exchange_rate_source: ExchangeRateSource | None
    message: str | None


@dataclass(frozen=True)
class ForexRateReading:
    connection_number: int
    base_currency: str
    read_at_seconds: float
    usd_per_base_unit: Decimal | None
    error_message: str | None


class PaperAccountMonitor:
    def __init__(
        self,
        *,
        settings: Settings,
        gateway_connection: GatewayConnection,
        read_monotonic_seconds: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self.gateway_connection = gateway_connection
        self.read_monotonic_seconds = read_monotonic_seconds
        self.forex_rate_reading: ForexRateReading | None = None
        self.checked_connection_number: int | None = None
        self.check = PaperAccountCheck(
            status="disconnected", message=None, actual_accounts=(), expected_account=settings.ibkr_account_id
        )

    async def keep_checking(self) -> None:
        """Runs until the caller cancels it, so that a failed check reaches the log without an open browser."""
        while True:
            self.refresh()
            await anyio.sleep(REFRESH_INTERVAL_SECONDS)

    def refresh(self) -> None:
        if not self.gateway_connection.is_connected():
            self.checked_connection_number = None
            self.check = check_paper_account(settings=self.settings, gateway_connection=self.gateway_connection)
            return
        connection_number = self.gateway_connection.read_connection_number()
        if connection_number == self.checked_connection_number:
            return
        self.checked_connection_number = connection_number
        self.check = check_paper_account(settings=self.settings, gateway_connection=self.gateway_connection)
        if self.check.status == "failed":
            # One line per connection. ATrade does not retry until the next connection.
            logger.error(
                "Paper account check failed: %s Actual accounts: %s. Expected account: %s. ATrade sends no orders.",
                self.check.message,
                list(self.check.actual_accounts),
                self.check.expected_account,
            )

    def read_check(self) -> PaperAccountCheck:
        self.refresh()
        return self.check

    def require_checked_paper_account(self) -> str:
        """Returns the paper account number for an order. Raises PaperAccountCheckError without a passed check."""
        check = self.read_check()
        if check.status == "disconnected":
            not_connected = PaperAccountCheck(
                status="disconnected",
                message="ATrade is not connected to IB Gateway.",
                actual_accounts=(),
                expected_account=check.expected_account,
            )
            raise PaperAccountCheckError(not_connected)
        if check.status == "failed":
            raise PaperAccountCheckError(check)
        return check.actual_accounts[0]

    def read_checked_account_id(self) -> str | None:
        check = self.read_check()
        if check.status != "passed":
            return None
        return check.actual_accounts[0]

    async def read_balance(self) -> PaperAccountBalance | None:
        account_id = self.read_checked_account_id()
        if account_id is None:
            return None
        account_values = [
            account_value
            for account_value in self.gateway_connection.read_account_values()
            if account_value.account == account_id
        ]
        base_currency = find_base_currency(account_values)
        if base_currency is None:
            return PaperAccountBalance(
                net_liquidation_usd=None,
                cash_usd=None,
                base_currency=None,
                net_liquidation_base=None,
                cash_base=None,
                usd_per_base_unit=None,
                exchange_rate_source=None,
                message="IBKR sent no NetLiquidation value for the paper account.",
            )
        base_values = [account_value for account_value in account_values if account_value.currency == base_currency]
        net_liquidation_base = find_amount(base_values, NET_LIQUIDATION_TAG)
        cash_base = find_amount(base_values, CASH_TAG)
        usd_per_base_unit, source, message = await self.find_usd_per_base_unit(account_values, base_currency)
        return PaperAccountBalance(
            net_liquidation_usd=convert_to_usd(net_liquidation_base, usd_per_base_unit),
            cash_usd=convert_to_usd(cash_base, usd_per_base_unit),
            base_currency=base_currency,
            net_liquidation_base=net_liquidation_base,
            cash_base=cash_base,
            usd_per_base_unit=usd_per_base_unit,
            exchange_rate_source=source,
            message=message,
        )

    async def find_usd_per_base_unit(
        self, account_values: list[AccountValue], base_currency: str
    ) -> tuple[Decimal | None, ExchangeRateSource | None, str | None]:
        """The rate of the account first, then the IBKR forex rate. Without a rate, the reason (section 11.9)."""
        if base_currency == BALANCE_CURRENCY:
            return Decimal(1), "base_currency_is_usd", None
        base_units_per_usd = find_account_exchange_rate(account_values, BALANCE_CURRENCY)
        if base_units_per_usd is not None:
            return Decimal(1) / base_units_per_usd, "account", None
        reading = await self.read_forex_rate(base_currency)
        if reading.usd_per_base_unit is not None:
            return reading.usd_per_base_unit, "ibkr_forex", None
        message = (
            f"The paper account has the base currency {base_currency} and IBKR sent no {base_currency} to "
            f"{BALANCE_CURRENCY} exchange rate: {reading.error_message}"
        )
        return None, None, message

    async def read_forex_rate(self, base_currency: str) -> ForexRateReading:
        """The cached IBKR forex rate. A new connection, a new base currency, or the maximum age reads it again."""
        now_seconds = self.read_monotonic_seconds()
        connection_number = self.gateway_connection.read_connection_number()
        reading = self.forex_rate_reading
        if (
            reading is not None
            and reading.connection_number == connection_number
            and reading.base_currency == base_currency
            and now_seconds - reading.read_at_seconds < EXCHANGE_RATE_MAX_AGE_SECONDS
        ):
            return reading
        try:
            rate = await self.gateway_connection.read_exchange_rate(base_currency, BALANCE_CURRENCY)
        except GatewayRequestError as error:
            reading = ForexRateReading(connection_number, base_currency, now_seconds, None, str(error))
        else:
            reading = ForexRateReading(connection_number, base_currency, now_seconds, rate, None)
        self.forex_rate_reading = reading
        return reading

    def read_positions(self) -> list[PortfolioPosition]:
        account_id = self.read_checked_account_id()
        if account_id is None:
            return []
        return [position for position in self.gateway_connection.read_portfolio() if position.account == account_id]


def find_amount(account_values: list[AccountValue], tag: str) -> Decimal | None:
    for account_value in account_values:
        if account_value.tag != tag:
            continue
        try:
            return Decimal(account_value.value)
        except InvalidOperation:
            return None
    return None


def find_base_currency(account_values: list[AccountValue]) -> str | None:
    """The currency of NetLiquidation. IBKR sends it in the base currency of the account, and in USD when it can."""
    currencies = [
        account_value.currency
        for account_value in account_values
        if account_value.tag == NET_LIQUIDATION_TAG and account_value.currency not in NOT_A_CURRENCY
    ]
    if BALANCE_CURRENCY in currencies:
        return BALANCE_CURRENCY
    return currencies[0] if currencies else None


def find_account_exchange_rate(account_values: list[AccountValue], currency: str) -> Decimal | None:
    """The base currency units for 1 `currency` unit that IBKR sends with the account values, or None."""
    for account_value in account_values:
        if account_value.tag in EXCHANGE_RATE_TAGS and account_value.currency == currency:
            rate = find_amount([account_value], account_value.tag)
            if rate is not None and rate > 0:
                return rate
    return None


def convert_to_usd(amount_base: Decimal | None, usd_per_base_unit: Decimal | None) -> Decimal | None:
    """Converts to USD with the rate. A converted amount is rounded to the cent; a USD amount stays as IBKR sent it."""
    if amount_base is None or usd_per_base_unit is None:
        return None
    if usd_per_base_unit == 1:
        return amount_base
    return (amount_base * usd_per_base_unit).quantize(USD_CENT)


async def fetch_paper_capital_usd(paper_account_monitor: PaperAccountMonitor) -> Decimal:
    """The paper account net liquidation value in USD after a passed check. Otherwise the local value from settings."""
    balance = await paper_account_monitor.read_balance()
    if balance is None or balance.net_liquidation_usd is None:
        return paper_account_monitor.settings.local_paper_capital_usd
    return balance.net_liquidation_usd
