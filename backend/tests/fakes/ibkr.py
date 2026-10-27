"""IBKR fake: the same functions as the GatewayConnection of the `ibkr` public entry. Data stays in memory.

Tests set `is_gateway_reachable`, `connected`, `port`, `managed_accounts`, `account_values`, `portfolio`,
`instruments`, `search_error_message`, `open_orders`, and `order_error_message` directly. No mock library is used (section 17.3).
"""

from decimal import Decimal

import anyio

from atrade.foundation.instrument import Instrument
from atrade.ibkr import AccountValue, GatewayRequestError, OpenOrder, OrderRequest, PortfolioPosition

# The fake checks the reachable flag this often. A short wait keeps the e2e server from using a full CPU.
CHECK_INTERVAL_SECONDS = 0.05
PAPER_PORT = 4004
# The client ID of the Web process (settings.ibkr_web_client_id). Orders of the fake come from this client ID.
WEB_CLIENT_ID = 1
FIRST_ORDER_ID = 1001

# Many symbols start with "A", so a search for "A" fills more than one screen of results in the e2e tests.
SAMPLE_US_SYMBOLS = [
    "AAPL", "ABBV", "ABNB", "ABT", "ACN", "ADBE", "ADI", "ADP", "AEP", "AIG", "AMAT", "AMD", "AMGN", "AMZN",
    "ANET", "AON", "APD", "APH", "AVGO", "AXP", "AZO",
]  # fmt: skip
SAMPLE_INSTRUMENTS = [
    Instrument(symbol="700", exchange="SEHK", currency="HKD"),
    Instrument(symbol="9988", exchange="SEHK", currency="HKD"),
    *[Instrument(symbol=symbol, exchange="NASDAQ", currency="USD") for symbol in SAMPLE_US_SYMBOLS],
]


class FakeGatewayConnection:
    def __init__(
        self,
        *,
        managed_accounts: list[str],
        is_gateway_reachable: bool = True,
        port: int = PAPER_PORT,
        instruments: list[Instrument] | None = None,
        client_id: int = WEB_CLIENT_ID,
    ) -> None:
        self.managed_accounts = managed_accounts
        self.is_gateway_reachable = is_gateway_reachable
        self.port = port
        self.account_values: list[AccountValue] = []
        self.portfolio: list[PortfolioPosition] = []
        self.instruments = list(SAMPLE_INSTRUMENTS) if instruments is None else instruments
        # When it is set, search_instruments fails with this message, like a timeout or an API error of IBKR.
        self.search_error_message: str | None = None
        self.client_id = client_id
        # All open orders of the account, like reqAllOpenOrders. Tests add orders of other client IDs here.
        self.open_orders: list[OpenOrder] = []
        # When it is set, place_order fails with this message, like an API error of IBKR.
        self.order_error_message: str | None = None
        self.next_order_id = FIRST_ORDER_ID
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

    async def search_instruments(self, query: str) -> list[Instrument]:
        if not self.connected:
            message = "Not connected"
            raise GatewayRequestError(message)
        if self.search_error_message is not None:
            raise GatewayRequestError(self.search_error_message)
        symbol_start = query.upper()
        return [instrument for instrument in self.instruments if instrument.symbol.startswith(symbol_start)]

    def require_connection(self) -> None:
        if not self.connected:
            message = "Not connected"
            raise GatewayRequestError(message)

    async def place_order(self, request: OrderRequest) -> int:
        self.require_connection()
        if self.order_error_message is not None:
            raise GatewayRequestError(self.order_error_message)
        order_id = self.next_order_id
        self.next_order_id += 1
        self.open_orders.append(
            OpenOrder(
                order_id=order_id,
                client_id=self.client_id,
                perm_id=order_id * 10,
                account=request.account,
                instrument=request.instrument,
                side=request.side,
                quantity=Decimal(request.quantity),
                order_type=request.order_type,
                limit_price=request.limit_price,
                time_in_force=request.time_in_force,
                status="Submitted",
                filled_quantity=Decimal(0),
                order_ref=request.order_ref,
            )
        )
        return order_id

    async def read_open_orders(self) -> list[OpenOrder]:
        self.require_connection()
        return list(self.open_orders)

    async def cancel_order(self, order_id: int) -> None:
        # Like IBKR: a client can cancel only its own orders.
        self.require_connection()
        self.open_orders = [
            order
            for order in self.open_orders
            if not (order.order_id == order_id and order.client_id == self.client_id)
        ]

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


def make_forward_test_order(
    account_id: str, *, forward_test_id: int, order_id: int, client_id: int, symbol: str = "AAPL"
) -> OpenOrder:
    """An open order that a forward test child sent. NautilusTrader writes the ClientOrderId into orderRef."""
    return OpenOrder(
        order_id=order_id,
        client_id=client_id,
        perm_id=order_id * 10,
        account=account_id,
        instrument=Instrument(symbol=symbol, exchange="NASDAQ", currency="USD"),
        side="BUY",
        quantity=Decimal(5),
        order_type="LMT",
        limit_price=Decimal("10.50"),
        time_in_force="GTC",
        status="Submitted",
        filled_quantity=Decimal(0),
        order_ref=f"O-20260102-030405-001-FT{forward_test_id}-{order_id}",
    )
