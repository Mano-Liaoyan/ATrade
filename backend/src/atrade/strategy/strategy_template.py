"""The code that a new strategy starts with (docs/architecture/strategy.md section 9.2).

It shows the required file format: 1 Strategy subclass, 1 StrategyConfig subclass with a keyword-only
__init__ (NautilusTrader 2.0 requires it), and indicator warm-up with request_bars in on_start.
"""

STRATEGY_TEMPLATE = '''"""Moving average cross: buy when the close goes above the average, sell when it goes below."""

from datetime import timedelta

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import SimpleMovingAverage
from nautilus_trader.model import Bar, BarType, InstrumentId, OrderSide, Quantity
from nautilus_trader.trading import Strategy

# The warm-up asks for 3 average periods of bars, and for 1 week at least, so that nights, weekends,
# and holidays do not leave the indicator without bars. A long warm-up of short bars means many IBKR requests.
WARM_UP_AVERAGE_PERIODS = 3
MIN_WARM_UP_LENGTH = timedelta(days=7)


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
        self.is_long = False

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
        close_price = bar.close.as_double()
        if close_price > self.average.value and not self.is_long:
            self.send_market_order(OrderSide.BUY)
            self.is_long = True
        elif close_price < self.average.value and self.is_long:
            self.send_market_order(OrderSide.SELL)
            self.is_long = False

    def send_market_order(self, order_side: OrderSide) -> None:
        order = self.order_factory.market(
            self.settings.instrument_id,
            order_side,
            Quantity.from_int(self.settings.trade_quantity_shares),
        )
        self.submit_order(order)
'''
