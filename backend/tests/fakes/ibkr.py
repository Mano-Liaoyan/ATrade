"""IBKR fake: the same functions as the GatewayConnection of the `ibkr` public entry. Data stays in memory.

Tests set `is_gateway_reachable`, `managed_accounts`, `instruments`, and `search_error_message` directly. No mock library is used (section 17.3).
"""

import anyio

from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayRequestError

# The fake checks the reachable flag this often. A short wait keeps the e2e server from using a full CPU.
CHECK_INTERVAL_SECONDS = 0.05

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
        instruments: list[Instrument] | None = None,
    ) -> None:
        self.managed_accounts = managed_accounts
        self.is_gateway_reachable = is_gateway_reachable
        self.instruments = list(SAMPLE_INSTRUMENTS) if instruments is None else instruments
        # When it is set, search_instruments fails with this message, like a timeout or an API error of IBKR.
        self.search_error_message: str | None = None
        self.connected = False

    async def keep_connected(self) -> None:
        while True:
            self.connected = self.is_gateway_reachable
            await anyio.sleep(CHECK_INTERVAL_SECONDS)

    def is_connected(self) -> bool:
        return self.connected

    def read_managed_accounts(self) -> list[str]:
        if not self.connected:
            return []
        return list(self.managed_accounts)

    async def search_instruments(self, query: str) -> list[Instrument]:
        if not self.connected:
            message = "Not connected"
            raise GatewayRequestError(message)
        if self.search_error_message is not None:
            raise GatewayRequestError(self.search_error_message)
        symbol_start = query.upper()
        return [instrument for instrument in self.instruments if instrument.symbol.startswith(symbol_start)]

    def disconnect(self) -> None:
        self.connected = False
