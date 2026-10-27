"""The paper account state of the Web process: the check result in memory, the balance, and the positions.

The check runs once after each connection and reconnection. A lost connection clears the result (section 11.2).
"""

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import anyio

from atrade.foundation.settings import Settings
from atrade.ibkr import AccountValue, GatewayConnection, PortfolioPosition
from atrade.paper_trading.paper_account_check import PaperAccountCheck, PaperAccountCheckError, check_paper_account

REFRESH_INTERVAL_SECONDS = 0.5
NET_LIQUIDATION_TAG = "NetLiquidation"
CASH_TAG = "TotalCashValue"
BALANCE_CURRENCY = "USD"

logger = logging.getLogger("atrade.paper_trading")


@dataclass(frozen=True)
class PaperAccountBalance:
    net_liquidation_usd: Decimal | None
    cash_usd: Decimal | None


class PaperAccountMonitor:
    def __init__(self, *, settings: Settings, gateway_connection: GatewayConnection) -> None:
        self.settings = settings
        self.gateway_connection = gateway_connection
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

    def read_balance(self) -> PaperAccountBalance | None:
        account_id = self.read_checked_account_id()
        if account_id is None:
            return None
        account_values = [
            account_value
            for account_value in self.gateway_connection.read_account_values()
            if account_value.account == account_id and account_value.currency == BALANCE_CURRENCY
        ]
        return PaperAccountBalance(
            net_liquidation_usd=find_amount(account_values, NET_LIQUIDATION_TAG),
            cash_usd=find_amount(account_values, CASH_TAG),
        )

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


def fetch_paper_capital_usd(paper_account_monitor: PaperAccountMonitor) -> Decimal:
    """The paper account net liquidation value after a passed check. Otherwise the local value from settings."""
    balance = paper_account_monitor.read_balance()
    if balance is None or balance.net_liquidation_usd is None:
        return paper_account_monitor.settings.local_paper_capital_usd
    return balance.net_liquidation_usd
