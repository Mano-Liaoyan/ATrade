"""Test strategy: buys 10 shares of each member of the universe in one `on_bar` call, at the first bar."""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar, BarType, DataType, OrderSide, Quantity
from nautilus_trader.trading import Strategy


class RebalanceConfig(StrategyConfig):
    """A multi-instrument configuration has no `instrument_id` and no `bar_type`."""


class RebalanceStrategy(Strategy):
    def __init__(self, config: RebalanceConfig) -> None:
        super().__init__(config)
        self.bar_types: list[BarType] = []
        self.has_bought = False

    def on_start(self) -> None:
        self.subscribe_data(DataType("UniverseUpdate"))

    def on_data(self, data: object) -> None:
        names = str(data.data.bar_types).split(",")  # pyright: ignore[reportAttributeAccessIssue]
        self.bar_types = [BarType.from_str(name) for name in names if name]
        for bar_type in self.bar_types:
            self.subscribe_bars(bar_type)

    def on_bar(self, bar: Bar) -> None:
        if self.has_bought:
            return
        self.has_bought = True
        for bar_type in self.bar_types:
            order = self.order_factory.market(bar_type.instrument_id, OrderSide.BUY, Quantity.from_int(10))
            self.submit_order(order)
