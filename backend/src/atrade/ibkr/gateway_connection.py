"""The connection of one process to IB Gateway through ib_async, with automatic reconnection.

Do not call `ib_async.util.patchAsyncio()` or `startLoop()` (section 7). The connection runs on the
event loop of the caller, for example the uvicorn loop.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from ib_async import IB, BarData, BarDataList, Contract, ContractDescription, Forex, Order, RequestError, Trade

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import require_usable_client_id
from atrade.ibkr.account_data import AccountValue, PortfolioPosition, convert_account_value, convert_portfolio_item
from atrade.ibkr.historical_bars import (
    BAR_SIZE_SETTINGS,
    LIVE_BAR_DURATIONS,
    keep_bars_in_chunk,
    plan_historical_data_requests,
    to_bar,
)
from atrade.ibkr.orders import (
    Execution,
    OpenOrder,
    OrderRequest,
    build_contract,
    build_order,
    convert_fill,
    convert_trade,
)

DEFAULT_RETRY_SECONDS = 10.0
CONNECT_TIMEOUT_SECONDS = 10.0
OPEN_ORDERS_TIMEOUT_SECONDS = 10.0
CANCEL_CONFIRMATION_TIMEOUT_SECONDS = 10.0
CANCEL_CONFIRMATION_CHECK_SECONDS = 0.1
# ATrade trades stocks only. reqMatchingSymbols also returns other security types, for example indexes.
STOCK_SECURITY_TYPE = "STK"
HISTORICAL_DATA_TIMEOUT_SECONDS = 60.0
# IBKR refuses 6 or more historical data requests for the same contract within 2 seconds (pacing violation).
HISTORICAL_DATA_REQUEST_INTERVAL_SECONDS = 0.5
# reqHistoricalData answers error 162 with this text when the range has no bars, for example a holiday.
NO_DATA_MESSAGE = "query returned no data"
# formatDate=2: intraday bar times come as UNIX seconds, so ib_async returns UTC datetimes.
UTC_FORMAT_DATE = 2
# The forex market closes on the weekend. 1 week of hourly bars always has a last bar.
EXCHANGE_RATE_DURATION = "1 W"
EXCHANGE_RATE_BAR_SIZE = "1 hour"
# While no live bar update comes, the live bar stream checks the connection this often.
LIVE_BAR_CONNECTION_CHECK_SECONDS = 1.0

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

    async def read_exchange_rate(self, currency: str, quote_currency: str) -> Decimal:
        """The IBKR forex rate: `quote_currency` units for 1 `currency` unit, for example 1.11 USD for 1 EUR.

        Raises GatewayRequestError when IBKR has no rate or does not answer (section 7.2).
        """
        ...

    async def place_order(self, request: OrderRequest) -> int:
        """Sends the order and returns its IBKR order ID. Raises GatewayRequestError without a connection."""
        ...

    async def read_open_orders(self) -> list[OpenOrder]:
        """All open orders of all client IDs (reqAllOpenOrders). IBKR is the only source of order status."""
        ...

    async def cancel_order(self, order_id: int) -> None:
        """Cancels an order that this client ID sent. Raises GatewayRequestError without a connection."""
        ...

    async def connect(self) -> None:
        """Connects one time. Raises GatewayRequestError when IB Gateway is not reachable. A forward test child uses
        it instead of keep_connected, because it needs the connection only for a short time (section 12.5)."""
        ...

    async def read_own_open_orders(self) -> list[OpenOrder]:
        """The open orders of this client ID only (reqOpenOrders)."""
        ...

    async def cancel_order_and_wait(self, order_id: int) -> None:
        """Cancels an order of this client ID and waits until IBKR confirms that the order is done.

        Raises GatewayRequestError without a connection or without the confirmation in time.
        """
        ...

    async def read_executions(self) -> list[Execution]:
        """The executions that IBKR returns for reqExecutions, of all client IDs of the account that IBKR shows."""
        ...

    async def read_historical_bars(
        self, instrument: Instrument, bar_period: BarPeriod, time_range: TimeRange
    ) -> list[Bar]: ...

    def stream_live_bars(self, instrument: Instrument, bar_period: BarPeriod) -> AsyncGenerator[Bar]:
        """Yields the current bar at once and after each IBKR update. The bar can be new or the same bar, changed.

        Raises GatewayRequestError when the subscription fails or the connection is lost. Close the generator
        (`contextlib.aclosing`) to end the IBKR subscription.
        """
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
        # ib_async reports the API as ready before connectAsync has read the accounts, the open orders and the
        # balance. ATrade reports "connected" only after that startup synchronization.
        self.synchronized = False
        self.ib = IB()
        # ib_async keeps one result per request type. Two parallel reqAllOpenOrders calls would lose one answer.
        self.open_orders_lock = asyncio.Lock()
        # Without this, ib_async ends a failed request with an empty result, the same as "no bars in the range".
        self.ib.RaiseRequestErrors = True

    async def keep_connected(self) -> None:
        """Connects, and connects again after each lost connection. Runs until the caller cancels it."""
        while True:
            if not self.ib.isConnected():
                await self.try_to_connect()
            await asyncio.sleep(self.retry_seconds)

    async def try_to_connect(self) -> None:
        self.synchronized = False
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
        self.synchronized = True
        self.connection_number += 1
        logger.info("Connected to IB Gateway at %s:%s with client ID %s.", self.host, self.port, self.client_id)

    def is_connected(self) -> bool:
        return self.synchronized and self.ib.isConnected()

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

    async def read_exchange_rate(self, currency: str, quote_currency: str) -> Decimal:
        """The close of the last hourly MIDPOINT bar of the IDEALPRO pair. IBKR lists each pair in one direction
        only, for example EUR.USD and USD.JPY, so the other direction gives the inverse rate.

        https://interactivebrokers.github.io/tws-api/historical_bars.html
        """
        self.require_connection()
        for pair, is_inverse in ((currency + quote_currency, False), (quote_currency + currency, True)):
            try:
                contracts = await self.ib.qualifyContractsAsync(Forex(pair))
            except ConnectionError, RequestError:
                continue
            contract = contracts[0] if contracts else None
            # qualifyContractsAsync gives None or a list of candidates when the pair does not exist in one form.
            if not isinstance(contract, Contract) or not contract.conId:
                continue
            close = await self.request_last_midpoint(contract)
            if close is not None and close > 0:
                return Decimal(1) / close if is_inverse else close
        message = f"IBKR has no {currency} to {quote_currency} exchange rate."
        raise GatewayRequestError(message)

    async def request_last_midpoint(self, contract: Contract) -> Decimal | None:
        try:
            bars_data = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime="",
                durationStr=EXCHANGE_RATE_DURATION,
                barSizeSetting=EXCHANGE_RATE_BAR_SIZE,
                whatToShow="MIDPOINT",
                useRTH=False,
                formatDate=UTC_FORMAT_DATE,
                timeout=HISTORICAL_DATA_TIMEOUT_SECONDS,
            )
        except (ConnectionError, RequestError) as error:
            message = f"IB Gateway did not return the {contract.localSymbol or contract.symbol} rate: {error}"
            raise GatewayRequestError(message) from error
        if not bars_data:
            return None
        # str() first, so that the Decimal has the short form of the float, for example 1.1139.
        return Decimal(str(bars_data[-1].close))

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
            except (ConnectionError, RequestError, TimeoutError) as error:
                message = f"IB Gateway did not return the open orders: {error}"
                raise GatewayRequestError(message) from error
        return [convert_trade(trade) for trade in trades if not trade.isDone()]

    async def cancel_order(self, order_id: int) -> None:
        self.require_connection()
        self.ib.cancelOrder(Order(orderId=order_id, clientId=self.client_id))

    async def connect(self) -> None:
        await self.try_to_connect()
        self.require_connection()

    async def read_own_open_orders(self) -> list[OpenOrder]:
        """https://interactivebrokers.github.io/tws-api/open_orders.html"""
        self.require_connection()
        trades = await self.request_own_open_trades()
        return [convert_trade(trade) for trade in trades]

    async def request_own_open_trades(self) -> list[Trade]:
        async with self.open_orders_lock:
            try:
                trades = await asyncio.wait_for(self.ib.reqOpenOrdersAsync(), OPEN_ORDERS_TIMEOUT_SECONDS)
            except (ConnectionError, RequestError, TimeoutError) as error:
                message = f"IB Gateway did not return the open orders of client ID {self.client_id}: {error}"
                raise GatewayRequestError(message) from error
        return [trade for trade in trades if not trade.isDone() and trade.order.clientId == self.client_id]

    async def cancel_order_and_wait(self, order_id: int) -> None:
        self.require_connection()
        trades = [trade for trade in await self.request_own_open_trades() if trade.order.orderId == order_id]
        if not trades:
            return
        trade = trades[0]
        self.ib.cancelOrder(trade.order)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + CANCEL_CONFIRMATION_TIMEOUT_SECONDS
        while not trade.isDone():
            if loop.time() >= deadline or not self.ib.isConnected():
                message = f"IB Gateway did not confirm the cancel of order {order_id} in time."
                raise GatewayRequestError(message)
            await asyncio.sleep(CANCEL_CONFIRMATION_CHECK_SECONDS)

    async def read_executions(self) -> list[Execution]:
        """https://interactivebrokers.github.io/tws-api/executions_commissions.html"""
        self.require_connection()
        try:
            fills = await asyncio.wait_for(self.ib.reqExecutionsAsync(), OPEN_ORDERS_TIMEOUT_SECONDS)
        except (ConnectionError, RequestError, TimeoutError) as error:
            message = f"IB Gateway did not return the executions: {error}"
            raise GatewayRequestError(message) from error
        return [convert_fill(fill) for fill in fills]

    async def read_historical_bars(
        self, instrument: Instrument, bar_period: BarPeriod, time_range: TimeRange
    ) -> list[Bar]:
        """Reads the TRADES bars of regular trading hours that start in the range, oldest first.

        https://interactivebrokers.github.io/tws-api/historical_bars.html
        """
        contract = build_contract(instrument)
        bars: list[Bar] = []
        for request_index, request in enumerate(plan_historical_data_requests(time_range, bar_period)):
            if request_index > 0:
                await asyncio.sleep(HISTORICAL_DATA_REQUEST_INTERVAL_SECONDS)
            bars_data = await self.request_historical_data(
                contract, request.chunk.end_utc, request.duration, bar_period
            )
            bars.extend(keep_bars_in_chunk(bars_data, request.chunk))
        return bars

    async def request_historical_data(
        self, contract: Contract, end_utc: datetime, duration: str, bar_period: BarPeriod
    ) -> list[BarData]:
        loop = asyncio.get_running_loop()
        started_at = loop.time()
        try:
            bars_data = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime=end_utc,
                durationStr=duration,
                barSizeSetting=BAR_SIZE_SETTINGS[bar_period],
                whatToShow="TRADES",
                useRTH=True,
                formatDate=UTC_FORMAT_DATE,
                timeout=HISTORICAL_DATA_TIMEOUT_SECONDS,
            )
        except RequestError as error:
            if NO_DATA_MESSAGE in error.message:
                return []
            raise GatewayRequestError(str(error)) from error
        except ConnectionError as error:
            raise GatewayRequestError(str(error)) from error
        # After a timeout, ib_async cancels the request and returns an empty list. Do not save that as "no bars".
        if not bars_data and loop.time() - started_at >= HISTORICAL_DATA_TIMEOUT_SECONDS:
            message = "IB Gateway did not answer the historical data request in time."
            raise GatewayRequestError(message)
        return list(bars_data)

    async def stream_live_bars(self, instrument: Instrument, bar_period: BarPeriod) -> AsyncGenerator[Bar]:
        """Live TRADES bars of regular trading hours: reqHistoricalData with keepUpToDate (section 21).

        IBKR sends an update of the last bar about every 5 seconds. The subscription ends when the generator closes.
        https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_request
        """
        bars_data = await self.subscribe_to_live_bars(build_contract(instrument), bar_period)
        updates: asyncio.Queue[None] = asyncio.Queue()

        def receive_update(_bars_data: BarDataList, _has_new_bar: bool) -> None:
            updates.put_nowait(None)

        bars_data.updateEvent += receive_update
        try:
            if bars_data:
                yield to_bar(bars_data[-1])
            while True:
                try:
                    await asyncio.wait_for(updates.get(), LIVE_BAR_CONNECTION_CHECK_SECONDS)
                except TimeoutError:
                    if not self.ib.isConnected():
                        message = "The connection to IB Gateway was lost."
                        raise GatewayRequestError(message) from None
                    continue
                # Only the newest state counts. Updates that came at the same time are one update.
                while not updates.empty():
                    updates.get_nowait()
                yield to_bar(bars_data[-1])
        finally:
            bars_data.updateEvent -= receive_update
            if self.ib.isConnected():
                self.ib.cancelHistoricalData(bars_data)

    async def subscribe_to_live_bars(self, contract: Contract, bar_period: BarPeriod) -> BarDataList:
        try:
            # keepUpToDate needs an empty end time: the bars go up to now.
            return await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime="",
                durationStr=LIVE_BAR_DURATIONS[bar_period],
                barSizeSetting=BAR_SIZE_SETTINGS[bar_period],
                whatToShow="TRADES",
                useRTH=True,
                formatDate=UTC_FORMAT_DATE,
                keepUpToDate=True,
                timeout=HISTORICAL_DATA_TIMEOUT_SECONDS,
            )
        except (ConnectionError, RequestError) as error:
            raise GatewayRequestError(str(error)) from error

    def disconnect(self) -> None:
        self.synchronized = False
        self.ib.disconnect()
