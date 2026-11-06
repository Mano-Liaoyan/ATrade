"""Test strategy: sends 1 bracket order for 100 shares at bar 1. A `limit_price` makes the entry a post-only limit."""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar, BarType, InstrumentId, OrderSide, OrderType, Price, Quantity
from nautilus_trader.trading import Strategy


class BracketConfig(StrategyConfig):
    def __init__(
        self,
        *,
        instrument_id: InstrumentId,
        bar_type: BarType,
        stop_price: float = 1.0,
        limit_price: float = 0.0,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)  # pyright: ignore[reportArgumentType] readability-exception: the stub has many keyword types.
        self.instrument_id = instrument_id
        self.bar_type = bar_type
        self.stop_price = stop_price
        self.limit_price = limit_price


class BracketStrategy(Strategy):
    def __init__(self, config: BracketConfig) -> None:
        super().__init__(config)
        self.settings = config
        self.has_sent = False

    def on_start(self) -> None:
        self.subscribe_bars(self.settings.bar_type)

    def on_bar(self, bar: Bar) -> None:
        if self.has_sent:
            return
        self.has_sent = True
        limit_price = self.settings.limit_price
        order_list = self.order_factory.bracket(
            self.settings.instrument_id,
            OrderSide.BUY,
            Quantity.from_int(100),
            entry_order_type=OrderType.LIMIT if limit_price else OrderType.MARKET,
            entry_price=Price(limit_price, 2) if limit_price else None,
            entry_post_only=bool(limit_price),
            tp_price=Price.from_str("1000.00"),
            sl_trigger_price=Price(self.settings.stop_price, 2),
        )
        self.submit_order_list(order_list)
