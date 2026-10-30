"""IBKR fake: the same functions as the GatewayConnection of the `ibkr` public entry. Data stays in memory.

Tests set `is_gateway_reachable`, `connected`, `port`, `managed_accounts`, `account_values`, `portfolio`,
`instruments`, `search_error_message`, `historical_bars_error_message`, `open_orders`, `order_error_message`,
`cancel_error_message`, `executions`, `exchange_rates`, `exchange_rate_error_message`, `daily_exchange_rates`,
`live_bars_error_message`, `live_bar_now_utc`, and `live_bar_interval_seconds` directly, and read
`historical_bar_requests`, `exchange_rate_requests`, `daily_exchange_rate_requests`, `live_bar_subscriptions`, and
`active_live_bar_stream_count`.
No mock library is used (section 17.3).
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal

import anyio

from atrade.foundation.bar import Bar, BarPeriod, TimeRange, ceil_to_bar_start, floor_to_bar_start
from atrade.foundation.instrument import Instrument
from atrade.ibkr import (
    AccountValue,
    DailyExchangeRate,
    Execution,
    GatewayRequestError,
    OpenOrder,
    OrderRequest,
    PortfolioPosition,
)

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

# The fake prices move in a saw-tooth between 100 and 149, one step for each bar period from the UNIX epoch.
SAMPLE_PRICE_BASE = 100
SAMPLE_PRICE_STEPS = 50
SAMPLE_VOLUME = Decimal(1000)
# The live bar of the fake: the current bar at this time. It is the time of the test clock and of the e2e server clock.
LIVE_BAR_NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
LIVE_BAR_INTERVAL_SECONDS = 0.2
# Each update moves the close 0.25 up, from the open to the open + 1.75, and then starts again at the open.
LIVE_CLOSE_STEP = Decimal("0.25")
LIVE_CLOSE_STEP_COUNT = 8
# Each update adds this volume, so the volume grows like the volume of a real bar that is not complete.
LIVE_VOLUME_STEP = Decimal(10)


@dataclass(frozen=True)
class HistoricalBarRequest:
    instrument: Instrument
    bar_period: BarPeriod
    time_range: TimeRange


@dataclass(frozen=True)
class DailyExchangeRateRequest:
    currency: str
    quote_currency: str
    time_range: TimeRange


@dataclass(frozen=True)
class LiveBarSubscription:
    instrument: Instrument
    bar_period: BarPeriod


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
        # When it is set, cancel_order_and_wait fails with this message, like a cancel without a confirmation.
        self.cancel_error_message: str | None = None
        # All executions that reqExecutions returns. Tests add them.
        self.executions: list[Execution] = []
        self.next_order_id = FIRST_ORDER_ID
        # When it is set, read_historical_bars fails with this message.
        self.historical_bars_error_message: str | None = None
        # Each call of read_historical_bars, in order. Tests assert that only missing ranges reach IBKR.
        self.historical_bar_requests: list[HistoricalBarRequest] = []
        # When it is set, stream_live_bars fails with this message, like missing market data permissions.
        self.live_bars_error_message: str | None = None
        self.live_bar_now_utc = LIVE_BAR_NOW_UTC
        self.live_bar_interval_seconds = LIVE_BAR_INTERVAL_SECONDS
        # Each call of stream_live_bars, in order, and the number of streams that did not end yet.
        self.live_bar_subscriptions: list[LiveBarSubscription] = []
        self.active_live_bar_stream_count = 0
        # The IBKR forex rates: (currency, quote currency) -> quote currency units for 1 currency unit.
        self.exchange_rates: dict[tuple[str, str], Decimal] = {}
        # When it is set, read_exchange_rate fails with this message, like missing forex market data.
        self.exchange_rate_error_message: str | None = None
        # Each call of read_exchange_rate, in order.
        self.exchange_rate_requests: list[tuple[str, str]] = []
        # The daily IBKR forex rates: (currency, quote currency) -> the rate of each day. The forex market of the fake
        # never closes, so each day in the range has a rate.
        self.daily_exchange_rates: dict[tuple[str, str], Decimal] = {}
        # Each call of read_daily_exchange_rates, in order. Tests assert that only missing ranges reach IBKR.
        self.daily_exchange_rate_requests: list[DailyExchangeRateRequest] = []
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

    async def connect(self) -> None:
        self.connected = self.is_gateway_reachable
        self.require_connection()

    async def read_own_open_orders(self) -> list[OpenOrder]:
        self.require_connection()
        return [order for order in self.open_orders if order.client_id == self.client_id]

    async def cancel_order_and_wait(self, order_id: int) -> None:
        self.require_connection()
        if self.cancel_error_message is not None:
            raise GatewayRequestError(self.cancel_error_message)
        await self.cancel_order(order_id)

    async def read_executions(self) -> list[Execution]:
        self.require_connection()
        return list(self.executions)

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

    async def stream_live_bars(self, instrument: Instrument, bar_period: BarPeriod) -> AsyncGenerator[Bar]:
        """Updates the current bar (at `live_bar_now_utc`) every `live_bar_interval_seconds` while connected."""
        if not self.connected:
            message = "Not connected"
            raise GatewayRequestError(message)
        self.live_bar_subscriptions.append(LiveBarSubscription(instrument, bar_period))
        if self.live_bars_error_message is not None:
            raise GatewayRequestError(self.live_bars_error_message)
        sample_bar = create_sample_bar(floor_to_bar_start(self.live_bar_now_utc, bar_period), bar_period)
        self.active_live_bar_stream_count += 1
        try:
            update_number = 0
            while self.connected:
                close = sample_bar.open + LIVE_CLOSE_STEP * (update_number % LIVE_CLOSE_STEP_COUNT)
                update_number += 1
                yield replace(sample_bar, close=close, volume=LIVE_VOLUME_STEP * update_number)
                await anyio.sleep(self.live_bar_interval_seconds)
            message = "The connection to IB Gateway was lost."
            raise GatewayRequestError(message)
        finally:
            self.active_live_bar_stream_count -= 1

    async def read_exchange_rate(self, currency: str, quote_currency: str) -> Decimal:
        if not self.connected:
            message = "ATrade is not connected to IB Gateway."
            raise GatewayRequestError(message)
        self.exchange_rate_requests.append((currency, quote_currency))
        if self.exchange_rate_error_message is not None:
            raise GatewayRequestError(self.exchange_rate_error_message)
        rate = self.exchange_rates.get((currency, quote_currency))
        if rate is None:
            message = f"IBKR has no {currency} to {quote_currency} exchange rate."
            raise GatewayRequestError(message)
        return rate

    async def read_daily_exchange_rates(
        self, currency: str, quote_currency: str, time_range: TimeRange
    ) -> list[DailyExchangeRate]:
        if not self.connected:
            message = "ATrade is not connected to IB Gateway."
            raise GatewayRequestError(message)
        self.daily_exchange_rate_requests.append(DailyExchangeRateRequest(currency, quote_currency, time_range))
        rate = self.daily_exchange_rates.get((currency, quote_currency))
        if rate is None:
            message = f"IBKR has no {currency} to {quote_currency} exchange rate."
            raise GatewayRequestError(message)
        rates: list[DailyExchangeRate] = []
        day_start_utc = ceil_to_bar_start(time_range.start_utc, BarPeriod.ONE_DAY)
        while day_start_utc < time_range.end_utc:
            rates.append(DailyExchangeRate(day_start_utc=day_start_utc, rate=rate))
            day_start_utc += BarPeriod.ONE_DAY.length
        return rates

    def disconnect(self) -> None:
        self.connected = False


def make_balance_values(account_id: str, *, net_liquidation_usd: str, cash_usd: str) -> list[AccountValue]:
    return [
        AccountValue(account=account_id, tag="NetLiquidation", value=net_liquidation_usd, currency="USD"),
        AccountValue(account=account_id, tag="TotalCashValue", value=cash_usd, currency="USD"),
        AccountValue(account=account_id, tag="AccountType", value="INDIVIDUAL", currency=""),
    ]


def make_stock_position(  # noqa: PLR0913 readability-exception: one keyword argument per field of a position.
    account_id: str, *, symbol: str, quantity: str, market_price: str, exchange: str = "NASDAQ", currency: str = "USD"
) -> PortfolioPosition:
    price = Decimal(market_price)
    position_quantity = Decimal(quantity)
    return PortfolioPosition(
        account=account_id,
        symbol=symbol,
        security_type="STK",
        exchange=exchange,
        currency=currency,
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


def make_execution(  # noqa: PLR0913 readability-exception: one keyword argument per field of a fill.
    account_id: str,
    *,
    order_id: int,
    quantity: str,
    price: str,
    client_id: int = WEB_CLIENT_ID,
    side: str = "BOT",
    commission: str = "0",
) -> Execution:
    """One fill from reqExecutions. The execution ID is unique for the order, the quantity, and the price."""
    return Execution(
        execution_id=f"0000e0d5.{order_id}.{quantity}.{price}",
        order_id=order_id,
        client_id=client_id,
        account=account_id,
        time_utc=LIVE_BAR_NOW_UTC,
        side=side,
        quantity=Decimal(quantity),
        price=Decimal(price),
        commission=Decimal(commission),
    )
