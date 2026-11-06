"""Test strategy: buys at bar 1 and asks to close the position 2 times at bar 2."""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar, BarType, InstrumentId, OrderSide, Quantity
from nautilus_trader.trading import Strategy


class CloseTwiceConfig(StrategyConfig):
    def __init__(self, *, instrument_id: InstrumentId, bar_type: BarType, **kwargs: object) -> None:
        super().__init__(**kwargs)  # pyright: ignore[reportArgumentType] readability-exception: the stub has many keyword types.
        self.instrument_id = instrument_id
        self.bar_type = bar_type


class CloseTwiceStrategy(Strategy):
    def __init__(self, config: CloseTwiceConfig) -> None:
        super().__init__(config)
        self.settings = config
        self.bar_count = 0

    def on_start(self) -> None:
        self.subscribe_bars(self.settings.bar_type)

    def on_bar(self, bar: Bar) -> None:
        self.bar_count += 1
        if self.bar_count == 1:
            order = self.order_factory.market(self.settings.instrument_id, OrderSide.BUY, Quantity.from_int(10))
            self.submit_order(order)
        if self.bar_count == 2:
            position = self.cache.positions_open(instrument_id=self.settings.instrument_id)[0]
            self.close_position(position)
            self.close_position(position)
