"""Finds one exact instrument through IB Gateway. Other capabilities (watchlist) use it to check an instrument."""

from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection, GatewayRequestError


class InstrumentLookupError(Exception):
    """IBKR cannot check the instrument now. The message is for the user."""


class GatewayNotReachableError(InstrumentLookupError):
    pass


class InstrumentLookupFailedError(InstrumentLookupError):
    pass


class InstrumentLookup:
    def __init__(self, *, gateway_connection: GatewayConnection, host: str, port: int) -> None:
        self.gateway_connection = gateway_connection
        self.host = host
        self.port = port

    async def find_instrument(self, instrument: Instrument) -> Instrument | None:
        """Returns the instrument when IBKR knows the same symbol, exchange, and currency. Else returns None."""
        if not self.gateway_connection.is_connected():
            message = f"IB Gateway is not reachable at {self.host}:{self.port}. The instrument check needs IB Gateway."
            raise GatewayNotReachableError(message)
        try:
            matches = await self.gateway_connection.search_instruments(instrument.symbol)
        except GatewayRequestError as error:
            message = f"The instrument check failed: {error}"
            raise InstrumentLookupFailedError(message) from error
        if instrument in matches:
            return instrument
        return None
