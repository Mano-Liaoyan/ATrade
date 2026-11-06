"""The code that a new strategy starts with (docs/architecture/strategy.md section 9.2).

It shows the required file format: 1 Strategy subclass, 1 StrategyConfig subclass with a keyword-only
__init__ (NautilusTrader 2.0 requires it), indicator warm-up with request_bars in on_start, and the
CHART_INDICATORS of the bar chart.
"""

STRATEGY_TEMPLATE = '''"""Moving average cross: buy when the close goes above the average, sell when it goes below."""

from datetime import timedelta

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import SimpleMovingAverage
from nautilus_trader.model import Bar, BarType, InstrumentId, OrderSide, Position, Quantity
from nautilus_trader.trading import Strategy

# The warm-up asks for 3 average periods of bars, and for 1 week at least, so that nights, weekends,
# and holidays do not leave the indicator without bars. A long warm-up of short bars means many IBKR requests.
WARM_UP_AVERAGE_PERIODS = 3
MIN_WARM_UP_LENGTH = timedelta(days=7)

# The bar chart of a backtest or a forward test shows these indicators. It has no effect on the run.
# A parameter is a number or the name of a configuration field with an int or float default.
CHART_INDICATORS = [
    {"indicator": "sma", "parameters": {"period": "average_period"}},
]


def find_warm_up_length(bar_type: BarType, average_period: int) -> timedelta:
    return max(bar_type.spec.timedelta * average_period * WARM_UP_AVERAGE_PERIODS, MIN_WARM_UP_LENGTH)


class MovingAverageConfig(StrategyConfig):
    # NautilusTrader 2.0 needs a keyword-only __init__. ATrade fills instrument_id and bar_type
    # at run time. All other fields must have a default value.
    def __init__(
        self,
        *,
        instrument_id: InstrumentId,
        bar_type: BarType,
        average_period: int = 20,
        trade_quantity_shares: int = 10,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.instrument_id = instrument_id
        self.bar_type = bar_type
        self.average_period = average_period
        self.trade_quantity_shares = trade_quantity_shares


class MovingAverageStrategy(Strategy):
    def __init__(self, config: MovingAverageConfig) -> None:
        super().__init__(config)
        self.settings = config
        self.average = SimpleMovingAverage(config.average_period)

    def on_start(self) -> None:
        self.register_indicator_for_bars(self.settings.bar_type, self.average)
        # Warm up the indicator with historical bars before live bars arrive.
        warm_up_length = find_warm_up_length(self.settings.bar_type, self.settings.average_period)
        warm_up_start = self.clock.utc_now() - warm_up_length
        self.request_bars(self.settings.bar_type, start=warm_up_start)
        self.subscribe_bars(self.settings.bar_type)

    def on_bar(self, bar: Bar) -> None:
        if not self.average.initialized:
            return
        # Each bar reads the position and the orders, because an order can be denied, rejected, or fill in parts.
        close_price = bar.close.as_double()
        positions = self.cache.positions_open(instrument_id=self.settings.instrument_id, strategy_id=self.strategy_id)
        if close_price > self.average.value and not positions and not self.has_orders():
            self.send_buy_order()
        elif close_price < self.average.value:
            self.send_exit_orders(positions)

    def has_orders(self, side: OrderSide | None = None) -> bool:
        filters = {"instrument_id": self.settings.instrument_id, "strategy_id": self.strategy_id, "side": side}
        return self.cache.orders_inflight_count(**filters) + self.cache.orders_open_count(**filters) > 0

    def send_exit_orders(self, positions: list[Position]) -> None:
        open_orders = self.cache.orders_open(instrument_id=self.settings.instrument_id, strategy_id=self.strategy_id)
        for order in open_orders:
            if order.side == OrderSide.BUY:
                self.cancel_order(order.client_order_id)
        if not self.has_orders(OrderSide.SELL):
            for position in positions:
                self.close_position(position)

    def send_buy_order(self) -> None:
        order = self.order_factory.market(
            self.settings.instrument_id,
            OrderSide.BUY,
            Quantity.from_int(self.settings.trade_quantity_shares),
        )
        self.submit_order(order)
'''
