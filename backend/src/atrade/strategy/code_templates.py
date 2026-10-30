"""The code of the multi-instrument code templates M1 to M4 (docs/architecture/strategy.md section 9.9.3, #202).

All 4 templates share 1 body: 1-day bars, long only, equal weight, and a rebalance on the first trading day of each
month. The strategy sells first and buys after the sell orders fill (#142). Only the score of an instrument and the
volatility target of M4 are different.
"""

MOMENTUM_SCORE = '''def find_score(closes: list[float], highs: list[float]) -> float | None:
    """12-1 momentum: the return from 252 bars ago to 21 bars ago. A higher score ranks first."""
    if len(closes) <= LOOK_BACK_BARS:
        return None
    return closes[-1 - SKIP_BARS] / closes[-1 - LOOK_BACK_BARS] - 1
'''

LOW_VOLATILITY_SCORE = '''def find_score(closes: list[float], highs: list[float]) -> float | None:
    """The negative 252-day realized volatility of the daily log returns. Lower volatility ranks first."""
    if len(closes) <= LOOK_BACK_BARS:
        return None
    window = closes[-1 - LOOK_BACK_BARS :]
    returns = [math.log(window[index + 1] / window[index]) for index in range(LOOK_BACK_BARS)]
    return -statistics.pstdev(returns) * math.sqrt(BARS_PER_YEAR)
'''

HIGH_52_WEEK_SCORE = '''def find_score(closes: list[float], highs: list[float]) -> float | None:
    """The close divided by the 52-week high. Nearer to the high ranks first."""
    if len(highs) < LOOK_BACK_BARS:
        return None
    return closes[-1] / max(highs[-LOOK_BACK_BARS:])
'''

BODY = '''
import math
import statistics
from collections import deque
from collections.abc import Sequence
from datetime import date, timedelta

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import Bar, BarType, DataType, InstrumentId, OrderSide, Quantity, Venue
from nautilus_trader.trading import Strategy

HOLD_COUNT = 50
LOOK_BACK_BARS = 252
SKIP_BARS = 21
BARS_PER_YEAR = 252
# M4 only: the target annual volatility of the strategy. None: no scaling.
TARGET_VOLATILITY: float | None = __TARGET_VOLATILITY__
VOLATILITY_BARS = 126
WARM_UP_LENGTH = timedelta(days=400)
# Cash that stays free, because a market order fills at the open of the next bar.
CASH_RESERVE = 0.02


__SCORE__

def find_position_scale(equity_values: list[float]) -> float:
    """The total position as a part of the equity: target volatility / volatility of the last 6 months, at most 1."""
    if TARGET_VOLATILITY is None or len(equity_values) < 3:
        return 1.0
    window = equity_values[-1 - VOLATILITY_BARS :]
    returns = [window[index + 1] / window[index] - 1 for index in range(len(window) - 1)]
    volatility = statistics.pstdev(returns) * math.sqrt(BARS_PER_YEAR)
    if volatility <= 0:
        return 1.0
    return min(1.0, TARGET_VOLATILITY / volatility)


class RankedUniverseConfig(StrategyConfig):
    """A multi-instrument configuration has no `instrument_id` and no `bar_type`."""


class RankedUniverseStrategy(Strategy):
    def __init__(self, config: RankedUniverseConfig) -> None:
        super().__init__(config)
        self.members: set[str] = set()
        self.closes: dict[str, deque[float]] = {}
        self.highs: dict[str, deque[float]] = {}
        self.shares: dict[str, int] = {}
        self.equity_values: deque[float] = deque(maxlen=VOLATILITY_BARS + 1)
        self.last_day: date | None = None
        self.last_rebalance_month: tuple[int, int] | None = None
        self.open_sell_count = 0
        self.waiting_buys: list[str] = []
        self.target_count = 0
        self.position_scale = 1.0
        self.rank_again = False
        self.buy_after_sells = False
        self.venue: Venue | None = None

    def on_start(self) -> None:
        self.subscribe_data(DataType("UniverseUpdate"))

    def on_data(self, data: object) -> None:
        names = str(data.data.bar_types).split(",")  # pyright: ignore[reportAttributeAccessIssue]
        # A new universe period starts on the first trading day of a month. When a bar of this day came before the
        # list, a later bar rebalances again with the new members.
        self.rank_again = True
        self.members = set()
        for name in names:
            if not name:
                continue
            bar_type = BarType.from_str(name)
            instrument = str(bar_type.instrument_id)
            self.venue = bar_type.instrument_id.venue
            self.members.add(instrument)
            if instrument in self.closes:
                continue
            self.closes[instrument] = deque(maxlen=LOOK_BACK_BARS + 1)
            self.highs[instrument] = deque(maxlen=LOOK_BACK_BARS)
            self.request_bars(bar_type, start=self.clock.utc_now() - WARM_UP_LENGTH)
            self.subscribe_bars(bar_type)

    def on_historical_bars(self, bars: Sequence[Bar]) -> None:
        for bar in bars:
            self.add_bar(bar)
        # The look-back bars of a new member can come after the rebalance of the period start. A later bar ranks
        # again with them.
        self.rank_again = True

    def on_bar(self, bar: Bar) -> None:
        day = self.clock.utc_now().date()
        if day != self.last_day:
            self.last_day = day
            self.equity_values.append(self.find_equity())
        self.add_bar(bar)
        if self.buy_after_sells:
            self.buy_after_sells = False
            self.buy()
        month = (day.year, day.month)
        is_new_month = month != self.last_rebalance_month
        if (is_new_month or self.rank_again) and self.open_sell_count == 0 and self.waiting_for_member(bar):
            self.last_rebalance_month = month
            self.rank_again = False
            self.rebalance()

    def waiting_for_member(self, bar: Bar) -> bool:
        return str(bar.bar_type.instrument_id) in self.members

    def add_bar(self, bar: Bar) -> None:
        instrument = str(bar.bar_type.instrument_id)
        if instrument in self.closes:
            self.closes[instrument].append(bar.close.as_double())
            self.highs[instrument].append(bar.high.as_double())

    def find_cash(self) -> float:
        account = None if self.venue is None else self.portfolio.account(self.venue)
        balance = None if account is None else account.balance_total()
        return 0.0 if balance is None else balance.as_double()

    def find_equity(self) -> float:
        held = sum(count * self.closes[name][-1] for name, count in self.shares.items() if self.closes.get(name))
        return self.find_cash() + held

    def rebalance(self) -> None:
        scores: dict[str, float] = {}
        for name in self.members:
            score = find_score(list(self.closes[name]), list(self.highs[name]))
            if score is not None:
                scores[name] = score
        targets = sorted(scores, key=lambda name: scores[name], reverse=True)[:HOLD_COUNT]
        self.position_scale = find_position_scale(list(self.equity_values))
        self.target_count = len(targets)
        self.waiting_buys = [name for name in targets if self.shares.get(name, 0) == 0]
        sells = [name for name, count in self.shares.items() if count > 0 and name not in targets]
        self.open_sell_count = len(sells)
        for name in sells:
            self.send_order(name, OrderSide.SELL, self.shares[name])
        if not sells:
            self.buy()

    def on_order_filled(self, event: object) -> None:
        name = str(event.instrument_id)  # pyright: ignore[reportAttributeAccessIssue]
        count = int(event.last_qty.as_double())  # pyright: ignore[reportAttributeAccessIssue]
        if event.order_side == OrderSide.SELL:  # pyright: ignore[reportAttributeAccessIssue]
            self.shares[name] = self.shares.get(name, 0) - count
            if self.shares[name] <= 0:
                self.open_sell_count -= 1
                # The account gets the cash of the sell after this event. So the next bar buys.
                self.buy_after_sells = self.open_sell_count == 0
        else:
            self.shares[name] = self.shares.get(name, 0) + count

    def buy(self) -> None:
        if not self.waiting_buys or self.target_count == 0:
            return
        cash = self.find_cash()
        equity = self.find_equity()
        held_value = equity - cash
        # The total position stays at most position_scale (at most 100%) of the equity.
        budget = max(0.0, min(equity * self.position_scale - held_value, cash - equity * CASH_RESERVE))
        target_value = equity * self.position_scale / self.target_count
        for name in self.waiting_buys:
            price = self.closes[name][-1]
            quantity = math.floor(min(target_value, budget) / price)
            if quantity < 1:
                continue
            budget -= quantity * price
            self.send_order(name, OrderSide.BUY, quantity)
        self.waiting_buys = []

    def send_order(self, name: str, side: OrderSide, quantity: int) -> None:
        order = self.order_factory.market(InstrumentId.from_str(name), side, Quantity.from_int(quantity))
        self.submit_order(order)
'''


def make_code_template(docstring: str, score: str, target_volatility: float | None = None) -> str:
    """The code of 1 code template: the template docstring, then the shared body with the score of the template."""
    body = BODY.replace("__TARGET_VOLATILITY__", repr(target_volatility)).replace("__SCORE__", score.rstrip("\n"))
    return f'"""{docstring}\n"""\n' + body
