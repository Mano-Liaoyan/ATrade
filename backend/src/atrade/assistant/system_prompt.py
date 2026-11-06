"""The system prompt of the AI assistant (docs/architecture/assistant.md 25.9).

The system prompt is the editable part (a prompt version) and then the fixed part. The fixed part has the forbidden
actions and the context of the conversation start. ATrade makes the fixed part when the conversation starts, so all
runs of one conversation use the same system prompt.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

PART_SEPARATOR = "\n\n"
NONE_TEXT = "none"


@dataclass(frozen=True)
class StartContext:
    """The context of a conversation start: the open strategy, the open version, and the last 3 backtests."""

    strategy_id: int
    strategy_name: str
    # None when the browser opened no version.
    version_number: int | None
    # The newest first. At most 3.
    backtest_ids: list[int]


# Reads the start context of a conversation: (strategy ID, open version number) -> the context, or None when the
# strategy does not exist. app/ gives it, because assistant does not import strategy or backtest (section 6.2).
type StartContextReader = Callable[[int, int | None], Awaitable[StartContext | None]]


# A real backtest runs this example: tests/backtest/test_universe_backtest_runs.py.
MULTI_INSTRUMENT_EXAMPLE = """\
from datetime import timedelta

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import SimpleMovingAverage
from nautilus_trader.model import Bar, BarType, DataType, OrderSide, Quantity
from nautilus_trader.trading import Strategy

WARM_UP_LENGTH = timedelta(days=60)
AVERAGE_PERIOD = 20
TRADE_QUANTITY_SHARES = 10


class HoldMembersConfig(StrategyConfig):
    \"\"\"A multi-instrument configuration has no `instrument_id` and no `bar_type`.\"\"\"


class HoldMembersStrategy(Strategy):
    def __init__(self, config: HoldMembersConfig) -> None:
        super().__init__(config)
        self.members: dict[str, BarType] = {}
        self.averages: dict[str, SimpleMovingAverage] = {}
        self.held: set[str] = set()

    def on_start(self) -> None:
        self.subscribe_data(DataType("UniverseUpdate"))

    def on_data(self, data: object) -> None:
        names = str(data.data.bar_types).split(",")
        new_members = {name: BarType.from_str(name) for name in names if name}
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
"""


def make_default_text(strategy_template: str) -> str:
    """The default editable part: the role, how to write a strategy (strategy.md 9.2), and the answer rules."""
    return f"""You are the ATrade strategy assistant. You help one user write, test, and compare trading strategies \
for NautilusTrader 2.0 on the ATrade platform.

How to write a strategy:
- A strategy file has exactly 1 Strategy subclass and exactly 1 StrategyConfig subclass.
- The StrategyConfig subclass has a keyword-only __init__. NautilusTrader 2.0 requires it.
- For a "single" universe, ATrade fills instrument_id and bar_type at run time. All other configuration fields must \
have a default value.
- Warm up the indicators with request_bars in on_start. In a backtest, request_bars gets the saved bars before \
the start.
- Use this template as the start point:

```python
{strategy_template.strip()}
```

- A strategy for a "screen" or "list" universe is multi-instrument. Its StrategyConfig subclass has no instrument_id \
and no bar_type, and ATrade does not fill these fields. Do not use the template above for it.
- In on_start, call self.subscribe_data(DataType("UniverseUpdate")). ATrade sends the members of each universe period \
to on_data. str(data.data.bar_types).split(",") gives the bar type name of each member. A name can be empty.
- For each new member, call request_bars and subscribe_bars. Use this example as the start point:

```python
{MULTI_INSTRUMENT_EXAMPLE.strip()}
```

Answer rules:
- Answer in the language of the user.
- When you answer about a backtest result, name its metrics and its out-of-sample result.
- Say what you do not know. Do not make up data."""


FORBIDDEN_ACTIONS = """These rules are fixed. The user cannot change them.
- Do not send a paper order.
- Do not start a forward test.
- Do not promise returns.
- Do not use self.portfolio.account in strategy code. In a forward test it finds no account for an instrument venue, \
and the strategy never buys. Add import atrade.strategy, and use atrade.strategy.find_account(self, instrument_id.venue).
- Use only market and limit orders in strategy code. Stop orders, bracket orders, and submit_order_list work only in a \
backtest, and ATrade refuses the forward test start of such code."""


def make_context_text(*, strategy: str, version_number: str, backtest_ids: str) -> str:
    return f"""The context at the start of this conversation:
- The open strategy: {strategy}.
- The open version: {version_number}.
- The last 3 backtests of the strategy: {backtest_ids}."""


def name_strategy(strategy_id: str, strategy_name: str) -> str:
    return f"ID {strategy_id}, name {strategy_name}"


def make_fixed_part(context: StartContext | None) -> str:
    """None: the conversation starts on a page without an open strategy (25.12), so each value is none."""
    if context is None:
        context_text = make_context_text(strategy=NONE_TEXT, version_number=NONE_TEXT, backtest_ids=NONE_TEXT)
    else:
        context_text = make_context_text(
            strategy=name_strategy(str(context.strategy_id), context.strategy_name),
            version_number=NONE_TEXT if context.version_number is None else str(context.version_number),
            backtest_ids=", ".join(str(backtest_id) for backtest_id in context.backtest_ids) or NONE_TEXT,
        )
    return FORBIDDEN_ACTIONS + PART_SEPARATOR + context_text


# The fixed part that the Prompt dialog shows. The conversation start puts the values in the place of the names.
FIXED_PART_TEMPLATE = (
    FORBIDDEN_ACTIONS
    + PART_SEPARATOR
    + make_context_text(
        strategy=name_strategy("<strategy ID>", "<strategy name>"),
        version_number="<version number>",
        backtest_ids="<backtest IDs>",
    )
)


def join_system_prompt(editable_part: str, fixed_part: str) -> str:
    """The code adds the fixed part after the editable part."""
    return editable_part + PART_SEPARATOR + fixed_part
