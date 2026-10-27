"""The connection of one process to IB Gateway through ib_async, with automatic reconnection.

Do not call `ib_async.util.patchAsyncio()` or `startLoop()` (section 7). The connection runs on the
event loop of the caller, for example the uvicorn loop.
"""

import asyncio
import logging
from typing import Protocol

from ib_async import IB, ContractDescription, RequestError

from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import require_usable_client_id

DEFAULT_RETRY_SECONDS = 10.0
CONNECT_TIMEOUT_SECONDS = 10.0
# ATrade trades stocks only. reqMatchingSymbols also returns other security types, for example indexes.
STOCK_SECURITY_TYPE = "STK"

logger = logging.getLogger("atrade.ibkr")


class GatewayRequestError(Exception):
    """IB Gateway did not answer a request: no connection, a timeout, or an API error."""


class GatewayConnection(Protocol):
    """The functions that the Web app uses. The IBKR fake in the tests has the same functions."""

    async def keep_connected(self) -> None: ...

    def is_connected(self) -> bool: ...

    def read_managed_accounts(self) -> list[str]: ...

    async def search_instruments(self, query: str) -> list[Instrument]: ...

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
        self.ib = IB()

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
        logger.info("Connected to IB Gateway at %s:%s with client ID %s.", self.host, self.port, self.client_id)

    def is_connected(self) -> bool:
        return self.ib.isConnected()

    def read_managed_accounts(self) -> list[str]:
        if not self.ib.isConnected():
            return []
        return self.ib.managedAccounts()

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

    def disconnect(self) -> None:
        self.ib.disconnect()
