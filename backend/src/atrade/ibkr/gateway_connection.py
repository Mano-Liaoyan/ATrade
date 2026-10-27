"""The connection of one process to IB Gateway through ib_async, with automatic reconnection.

Do not call `ib_async.util.patchAsyncio()` or `startLoop()` (section 7). The connection runs on the
event loop of the caller, for example the uvicorn loop.
"""

import asyncio
import logging
from typing import Protocol

from ib_async import IB, ContractDescription, Order, RequestError

from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import require_usable_client_id
from atrade.ibkr.account_data import AccountValue, PortfolioPosition, convert_account_value, convert_portfolio_item
from atrade.ibkr.orders import OpenOrder, OrderRequest, build_contract, build_order, convert_trade

DEFAULT_RETRY_SECONDS = 10.0
CONNECT_TIMEOUT_SECONDS = 10.0
OPEN_ORDERS_TIMEOUT_SECONDS = 10.0
# ATrade trades stocks only. reqMatchingSymbols also returns other security types, for example indexes.
STOCK_SECURITY_TYPE = "STK"

logger = logging.getLogger("atrade.ibkr")


class GatewayRequestError(Exception):
    """IB Gateway did not answer a request: no connection, a timeout, or an API error."""


class GatewayConnection(Protocol):
    """The functions that the Web app uses. The IBKR fake in the tests has the same functions."""

    async def keep_connected(self) -> None: ...

    def is_connected(self) -> bool: ...

    def read_port(self) -> int:
        """The Gateway API port that this connection uses."""
        ...

    def read_connection_number(self) -> int:
        """Counts the successful connections. A new number means a new connection or a reconnection."""
        ...

    def read_managed_accounts(self) -> list[str]: ...

    def read_account_values(self) -> list[AccountValue]: ...

    def read_portfolio(self) -> list[PortfolioPosition]: ...

    async def search_instruments(self, query: str) -> list[Instrument]: ...

    async def place_order(self, request: OrderRequest) -> int:
        """Sends the order and returns its IBKR order ID. Raises GatewayRequestError without a connection."""
        ...

    async def read_open_orders(self) -> list[OpenOrder]:
        """All open orders of all client IDs (reqAllOpenOrders). IBKR is the only source of order status."""
        ...

    async def cancel_order(self, order_id: int) -> None:
        """Cancels an order that this client ID sent. Raises GatewayRequestError without a connection."""
        ...

    def disconnect(self) -> None: ...


def read_stock_instruments(contract_descriptions: list[ContractDescription]) -> list[Instrument]:
    """Keeps the stocks, in the IBKR order, without duplicates. The exchange is the primary exchange."""
    instruments: list[Instrument] = []
    for description in contract_descriptions:
        contract = description.contract
        if contract is None or contract.secType != STOCK_SECURITY_TYPE:
            continue
        instrument = Instrument(symbol=contract.symbol, exchange=contract.primaryExchange, currency=contract.currency)
        if instrument not in instruments:
            instruments.append(instrument)
    return instruments


class IbAsyncGatewayConnection:
    def __init__(self, *, host: str, port: int, client_id: int, retry_seconds: float = DEFAULT_RETRY_SECONDS) -> None:
        require_usable_client_id(client_id)
        self.host = host
        self.port = port
        self.client_id = client_id
        self.retry_seconds = retry_seconds
        self.connection_number = 0
        self.ib = IB()
        # ib_async keeps one result per request type. Two parallel reqAllOpenOrders calls would lose one answer.
        self.open_orders_lock = asyncio.Lock()

    async def keep_connected(self) -> None:
        """Connects, and connects again after each lost connection. Runs until the caller cancels it."""
        while True:
            if not self.ib.isConnected():
                await self.try_to_connect()
            await asyncio.sleep(self.retry_seconds)

    async def try_to_connect(self) -> None:
        try:
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id, timeout=CONNECT_TIMEOUT_SECONDS)
        except (OSError, TimeoutError) as error:
            logger.warning(
                "IB Gateway is not reachable at %s:%s (%s). Next try in %s seconds.",
                self.host,
                self.port,
                error,
                self.retry_seconds,
            )
            return
        self.connection_number += 1
        logger.info("Connected to IB Gateway at %s:%s with client ID %s.", self.host, self.port, self.client_id)

    def is_connected(self) -> bool:
        return self.ib.isConnected()

    def read_port(self) -> int:
        return self.port

    def read_connection_number(self) -> int:
        return self.connection_number

    def read_managed_accounts(self) -> list[str]:
        if not self.ib.isConnected():
            return []
        return self.ib.managedAccounts()

    def read_account_values(self) -> list[AccountValue]:
        if not self.ib.isConnected():
            return []
        return [convert_account_value(account_value) for account_value in self.ib.accountValues()]

    def read_portfolio(self) -> list[PortfolioPosition]:
        if not self.ib.isConnected():
            return []
        return [convert_portfolio_item(portfolio_item) for portfolio_item in self.ib.portfolio()]

    async def search_instruments(self, query: str) -> list[Instrument]:
        """Finds stocks whose symbol starts with the query, or whose name has a word that matches it. IBKR allows 1
        reqMatchingSymbols request per second.

        https://interactivebrokers.github.io/tws-api/matching_symbols.html
        """
        try:
            contract_descriptions = await self.ib.reqMatchingSymbolsAsync(query)
        except (ConnectionError, RequestError) as error:
            raise GatewayRequestError(str(error)) from error
        if contract_descriptions is None:
            message = "IB Gateway did not answer the instrument search in time."
            raise GatewayRequestError(message)
        return read_stock_instruments(contract_descriptions)

    def require_connection(self) -> None:
        if not self.ib.isConnected():
            message = f"ATrade is not connected to IB Gateway at {self.host}:{self.port}."
            raise GatewayRequestError(message)

    async def place_order(self, request: OrderRequest) -> int:
        self.require_connection()
        trade = self.ib.placeOrder(build_contract(request.instrument), build_order(request))
        return trade.order.orderId

    async def read_open_orders(self) -> list[OpenOrder]:
        """https://interactivebrokers.github.io/tws-api/open_orders.html"""
        self.require_connection()
        async with self.open_orders_lock:
            try:
                trades = await asyncio.wait_for(self.ib.reqAllOpenOrdersAsync(), OPEN_ORDERS_TIMEOUT_SECONDS)
            except (ConnectionError, TimeoutError) as error:
                message = f"IB Gateway did not return the open orders: {error}"
                raise GatewayRequestError(message) from error
        return [convert_trade(trade) for trade in trades if not trade.isDone()]

    async def cancel_order(self, order_id: int) -> None:
        self.require_connection()
        self.ib.cancelOrder(Order(orderId=order_id, clientId=self.client_id))

    def disconnect(self) -> None:
        self.ib.disconnect()
