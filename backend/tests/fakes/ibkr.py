"""IBKR fake: the same functions as the GatewayConnection of the `ibkr` public entry. Data stays in memory.

Tests set `is_gateway_reachable`, `connected`, `managed_accounts`, `account_values`, and `portfolio` directly.
No mock library is used (section 17.3).
"""

from decimal import Decimal

import anyio

from atrade.ibkr import AccountValue, PortfolioPosition

# The fake checks the reachable flag this often. A short wait keeps the e2e server from using a full CPU.
CHECK_INTERVAL_SECONDS = 0.05
PAPER_PORT = 4004


class FakeGatewayConnection:
    def __init__(
        self,
        *,
        managed_accounts: list[str],
        is_gateway_reachable: bool = True,
        port: int = PAPER_PORT,
    ) -> None:
        self.managed_accounts = managed_accounts
        self.is_gateway_reachable = is_gateway_reachable
        self.port = port
        self.account_values: list[AccountValue] = []
        self.portfolio: list[PortfolioPosition] = []
        self.connection_number = 0
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    @connected.setter
    def connected(self, connected: bool) -> None:
        # Each new connection gets a new number, like each successful connect of the real connection.
        if connected and not self._connected:
            self.connection_number += 1
        self._connected = connected

    async def keep_connected(self) -> None:
        while True:
            self.connected = self.is_gateway_reachable
            await anyio.sleep(CHECK_INTERVAL_SECONDS)

    def is_connected(self) -> bool:
        return self.connected

    def read_port(self) -> int:
        return self.port

    def read_connection_number(self) -> int:
        return self.connection_number

    def read_managed_accounts(self) -> list[str]:
        if not self.connected:
            return []
        return list(self.managed_accounts)

    def read_account_values(self) -> list[AccountValue]:
        if not self.connected:
            return []
        return list(self.account_values)

    def read_portfolio(self) -> list[PortfolioPosition]:
        if not self.connected:
            return []
        return list(self.portfolio)

    def disconnect(self) -> None:
        self.connected = False


def make_balance_values(account_id: str, *, net_liquidation_usd: str, cash_usd: str) -> list[AccountValue]:
    return [
        AccountValue(account=account_id, tag="NetLiquidation", value=net_liquidation_usd, currency="USD"),
        AccountValue(account=account_id, tag="TotalCashValue", value=cash_usd, currency="USD"),
        AccountValue(account=account_id, tag="AccountType", value="INDIVIDUAL", currency=""),
    ]


def make_stock_position(account_id: str, *, symbol: str, quantity: str, market_price: str) -> PortfolioPosition:
    price = Decimal(market_price)
    position_quantity = Decimal(quantity)
    return PortfolioPosition(
        account=account_id,
        symbol=symbol,
        security_type="STK",
        exchange="NASDAQ",
        currency="USD",
        quantity=position_quantity,
        average_cost=price,
        market_price=price,
        market_value=price * position_quantity,
        unrealized_pnl=Decimal(0),
    )
