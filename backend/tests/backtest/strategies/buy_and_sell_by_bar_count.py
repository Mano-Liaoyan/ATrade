"""Test strategy: buy 10 shares at the close of bar 3, sell them at the close of bar 8, buy again at bar 13.

The backtest tests save this file as a strategy version and assert the exact results.
"""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar, BarType, InstrumentId, OrderSide, Quantity
from nautilus_trader.trading import Strategy

BUY_BAR_NUMBERS = (3, 13)
SELL_BAR_NUMBERS = (8,)


class BarCountConfig(StrategyConfig):
    def __init__(
        self, *, instrument_id: InstrumentId, bar_type: BarType, trade_quantity_shares: int = 10, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)  # pyright: ignore[reportArgumentType] readability-exception: the stub has many keyword types.
        self.instrument_id = instrument_id
        self.bar_type = bar_type
        self.trade_quantity_shares = trade_quantity_shares


class BarCountStrategy(Strategy):
    def __init__(self, config: BarCountConfig) -> None:
        super().__init__(config)
        self.settings = config
        self.bar_count = 0

    def on_start(self) -> None:
        self.subscribe_bars(self.settings.bar_type)

    def on_bar(self, bar: Bar) -> None:
        self.bar_count += 1
        if self.bar_count in BUY_BAR_NUMBERS:
            self.send_market_order(OrderSide.BUY)
        if self.bar_count in SELL_BAR_NUMBERS:
            self.send_market_order(OrderSide.SELL)

    def send_market_order(self, order_side: OrderSide) -> None:
        quantity = Quantity.from_int(self.settings.trade_quantity_shares)
        order = self.order_factory.market(self.settings.instrument_id, order_side, quantity)
        self.submit_order(order)
