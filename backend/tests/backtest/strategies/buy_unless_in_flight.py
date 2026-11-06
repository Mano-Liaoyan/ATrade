"""Test strategy: at bar 1, sends a buy and a second buy when the order count of the cache has no order in flight."""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar, BarType, InstrumentId, OrderSide, Quantity
from nautilus_trader.trading import Strategy


class BuyUnlessInFlightConfig(StrategyConfig):
    def __init__(self, *, instrument_id: InstrumentId, bar_type: BarType, **kwargs: object) -> None:
        super().__init__(**kwargs)  # pyright: ignore[reportArgumentType] readability-exception: the stub has many keyword types.
        self.instrument_id = instrument_id
        self.bar_type = bar_type


class BuyUnlessInFlightStrategy(Strategy):
    def __init__(self, config: BuyUnlessInFlightConfig) -> None:
        super().__init__(config)
        self.settings = config
        self.bar_count = 0

    def on_start(self) -> None:
        self.subscribe_bars(self.settings.bar_type)

    def on_bar(self, bar: Bar) -> None:
        self.bar_count += 1
        if self.bar_count != 1:
            return
        self.buy()
        instrument_id = self.settings.instrument_id
        if self.cache.orders_inflight_count(instrument_id=instrument_id, strategy_id=self.strategy_id) == 0:
            self.buy()

    def buy(self) -> None:
        self.submit_order(self.order_factory.market(self.settings.instrument_id, OrderSide.BUY, Quantity.from_int(10)))
