"""Test strategy of a multi-instrument backtest: holds 10 shares of each member of the current universe.

It gets the list of each universe period as `UniverseUpdate` custom data. For each new member, it warms up an
SMA(20) on the look-back bars and buys on the first bar after the warm-up. It sells a member that leaves the list.
"""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false

from datetime import timedelta

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import SimpleMovingAverage
from nautilus_trader.model import Bar, BarType, DataType, OrderSide, Quantity
from nautilus_trader.trading import Strategy

WARM_UP_LENGTH = timedelta(days=60)
AVERAGE_PERIOD = 20
TRADE_QUANTITY_SHARES = 10


class FollowUniverseConfig(StrategyConfig):
    """A multi-instrument configuration has no `instrument_id` and no `bar_type`."""


class FollowUniverseStrategy(Strategy):
    def __init__(self, config: FollowUniverseConfig) -> None:
        super().__init__(config)
        self.members: dict[str, BarType] = {}
        self.averages: dict[str, SimpleMovingAverage] = {}
        self.held: set[str] = set()

    def on_start(self) -> None:
        self.subscribe_data(DataType("UniverseUpdate"))

    def on_data(self, data: object) -> None:
        bar_type_names = str(data.data.bar_types).split(",")  # pyright: ignore[reportAttributeAccessIssue]
        new_members = {name: BarType.from_str(name) for name in bar_type_names if name}
        for name, bar_type in list(self.members.items()):
            if name in new_members:
                continue
            self.unsubscribe_bars(bar_type)
            del self.members[name]
            if name in self.held:
                self.send_market_order(bar_type, OrderSide.SELL)
                self.held.discard(name)
        for name, bar_type in new_members.items():
            if name in self.members:
                continue
            self.members[name] = bar_type
            self.averages[name] = SimpleMovingAverage(AVERAGE_PERIOD)
            self.register_indicator_for_bars(bar_type, self.averages[name])
            self.request_bars(bar_type, start=self.clock.utc_now() - WARM_UP_LENGTH)
            self.subscribe_bars(bar_type)

    def on_bar(self, bar: Bar) -> None:
        name = str(bar.bar_type)
        if name in self.members and name not in self.held and self.averages[name].initialized:
            self.send_market_order(bar.bar_type, OrderSide.BUY)
            self.held.add(name)

    def send_market_order(self, bar_type: BarType, order_side: OrderSide) -> None:
        order = self.order_factory.market(bar_type.instrument_id, order_side, Quantity.from_int(TRADE_QUANTITY_SHARES))
        self.submit_order(order)
