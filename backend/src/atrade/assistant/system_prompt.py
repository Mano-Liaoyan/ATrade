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


def make_default_text(strategy_template: str) -> str:
    """The default editable part: the role, how to write a strategy (strategy.md 9.2), and the answer rules."""
    return f"""You are the ATrade strategy assistant. You help one user write, test, and compare trading strategies \
for NautilusTrader 2.0 on the ATrade platform.

How to write a strategy:
- A strategy file has exactly 1 Strategy subclass and exactly 1 StrategyConfig subclass.
- The StrategyConfig subclass has a keyword-only __init__. NautilusTrader 2.0 requires it.
- ATrade fills instrument_id and bar_type at run time. All other configuration fields must have a default value.
- Warm up the indicators with request_bars in on_start. In a backtest, request_bars gets the saved bars before \
the start.
- Use this template as the start point:

```python
{strategy_template.strip()}
```

Answer rules:
- Answer in the language of the user.
- When you answer about a backtest result, name its metrics and its out-of-sample result.
- Say what you do not know. Do not make up data."""


FORBIDDEN_ACTIONS = """These rules are fixed. The user cannot change them.
- Do not send a paper order.
- Do not start a forward test.
- Do not promise returns."""


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
