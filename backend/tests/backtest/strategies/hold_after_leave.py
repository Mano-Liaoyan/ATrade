"""Test strategy of a multi-instrument backtest: keeps the bar subscription of a held member after it leaves.

It buys 10 shares of each member on its first bar. When a held member leaves, it does not sell at once. It sells on
the first bar of that instrument after the leave, and then unsubscribes.
"""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar, BarType, DataType, OrderSide, Quantity
from nautilus_trader.trading import Strategy

TRADE_QUANTITY_SHARES = 10


class HoldAfterLeaveConfig(StrategyConfig):
    """A multi-instrument configuration has no `instrument_id` and no `bar_type`."""


class HoldAfterLeaveStrategy(Strategy):
    def __init__(self, config: HoldAfterLeaveConfig) -> None:
        super().__init__(config)
        self.members: set[str] = set()
        self.held: set[str] = set()

    def on_start(self) -> None:
        self.subscribe_data(DataType("UniverseUpdate"))

    def on_data(self, data: object) -> None:
        bar_type_names = str(data.data.bar_types).split(",")  # pyright: ignore[reportAttributeAccessIssue]
        new_members = {name for name in bar_type_names if name}
        for name in self.members - new_members:
            if name not in self.held:
                self.unsubscribe_bars(BarType.from_str(name))
        for name in new_members - self.members:
            if name not in self.held:
                self.subscribe_bars(BarType.from_str(name))
        self.members = new_members

    def on_bar(self, bar: Bar) -> None:
        name = str(bar.bar_type)
        if name in self.members and name not in self.held:
            self.send_market_order(bar.bar_type, OrderSide.BUY)
            self.held.add(name)
        elif name not in self.members and name in self.held:
            self.send_market_order(bar.bar_type, OrderSide.SELL)
            self.held.discard(name)
            self.unsubscribe_bars(bar.bar_type)

    def send_market_order(self, bar_type: BarType, order_side: OrderSide) -> None:
        order = self.order_factory.market(bar_type.instrument_id, order_side, Quantity.from_int(TRADE_QUANTITY_SHARES))
        self.submit_order(order)
