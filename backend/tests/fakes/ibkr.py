"""IBKR fake: the same functions as the GatewayConnection of the `ibkr` public entry. Data stays in memory.

Tests set `is_gateway_reachable`, `connected`, `port`, `managed_accounts`, `account_values`, `portfolio`,
`instruments`, `search_error_message`, and `historical_bars_error_message` directly, and read
`historical_bar_requests`. No mock library is used (section 17.3).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import anyio

from atrade.foundation.bar import Bar, BarPeriod, TimeRange, ceil_to_bar_start
from atrade.foundation.instrument import Instrument
from atrade.ibkr import AccountValue, GatewayRequestError, PortfolioPosition

# The fake checks the reachable flag this often. A short wait keeps the e2e server from using a full CPU.
CHECK_INTERVAL_SECONDS = 0.05
PAPER_PORT = 4004

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

# The fake prices move in a saw-tooth between 100 and 149, one step for each bar period from the UNIX epoch.
SAMPLE_PRICE_BASE = 100
SAMPLE_PRICE_STEPS = 50
SAMPLE_VOLUME = Decimal(1000)


@dataclass(frozen=True)
class HistoricalBarRequest:
    instrument: Instrument
    bar_period: BarPeriod
    time_range: TimeRange


def create_sample_bar(start_utc: datetime, bar_period: BarPeriod) -> Bar:
    step = int(start_utc.timestamp()) // int(bar_period.length.total_seconds())
    open_price = Decimal(SAMPLE_PRICE_BASE + step % SAMPLE_PRICE_STEPS)
    return Bar(
        start_utc=start_utc,
        open=open_price,
        high=open_price + Decimal(2),
        low=open_price - Decimal(1),
        close=open_price + Decimal("0.5"),
        volume=SAMPLE_VOLUME,
    )


class FakeGatewayConnection:
    def __init__(
        self,
        *,
        managed_accounts: list[str],
        is_gateway_reachable: bool = True,
        port: int = PAPER_PORT,
        instruments: list[Instrument] | None = None,
    ) -> None:
        self.managed_accounts = managed_accounts
        self.is_gateway_reachable = is_gateway_reachable
        self.port = port
        self.account_values: list[AccountValue] = []
        self.portfolio: list[PortfolioPosition] = []
        self.instruments = list(SAMPLE_INSTRUMENTS) if instruments is None else instruments
        # When it is set, search_instruments fails with this message, like a timeout or an API error of IBKR.
        self.search_error_message: str | None = None
        # When it is set, read_historical_bars fails with this message.
        self.historical_bars_error_message: str | None = None
        # Each call of read_historical_bars, in order. Tests assert that only missing ranges reach IBKR.
        self.historical_bar_requests: list[HistoricalBarRequest] = []
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

    async def read_historical_bars(
        self, instrument: Instrument, bar_period: BarPeriod, time_range: TimeRange
    ) -> list[Bar]:
        """Returns one sample bar for each bar period in the range: the market of the fake never closes."""
        if not self.connected:
            message = "Not connected"
            raise GatewayRequestError(message)
        self.historical_bar_requests.append(HistoricalBarRequest(instrument, bar_period, time_range))
        if self.historical_bars_error_message is not None:
            raise GatewayRequestError(self.historical_bars_error_message)
        bars: list[Bar] = []
        bar_start_utc = ceil_to_bar_start(time_range.start_utc, bar_period)
        while bar_start_utc < time_range.end_utc:
            bars.append(create_sample_bar(bar_start_utc, bar_period))
            bar_start_utc += bar_period.length
        return bars

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
