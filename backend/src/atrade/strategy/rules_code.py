"""The code from the rules of the rule builder (docs/architecture/strategy.md section 9.8.3, #172).

`make_rules_code` is the only function that makes the code. The save route and `POST /api/strategy-rules/code` use
it. It walks the rules in a fixed order (entry group, then exit items), so the same rules always give the same code.
"""

from dataclasses import dataclass, field

from atrade.indicator import INDICATOR_CATALOG, IndicatorDefinition
from atrade.strategy.strategy_rules import (
    IndicatorOperand,
    InnerRuleGroup,
    NumberOperand,
    PercentOfEquity,
    PriceOperand,
    RuleCondition,
    RuleGroup,
    StrategyRules,
)

RULES_CODE_DOCSTRING = (
    "Strategy from the rule builder: buy when the entry group is true, sell when an exit item is true."
)
INDENT = "    "
COMPARISON_OPERATORS = {"above": ">", "below": "<", "at_or_above": ">=", "at_or_below": "<="}
GROUP_OPERATORS = {"all_of": "and", "any_of": "or"}

type Operand = PriceOperand | IndicatorOperand | NumberOperand


@dataclass(frozen=True)
class IndicatorUse:
    """One indicator object of the code. Operands with the same indicator and parameters share it."""

    name: str
    definition: IndicatorDefinition
    parameters: dict[str, int | float]


@dataclass
class CodeParts:
    """The indicators, the configuration fields, and the values that the expressions use, in the order of use."""

    indicators: list[IndicatorUse] = field(default_factory=list[IndicatorUse])
    fields: list[tuple[str, int | float]] = field(default_factory=list[tuple[str, int | float]])
    values: dict[str, str] = field(default_factory=lambda: {"close": "bar.close.as_double()"})

    def add_field(self, name: str, default: float) -> str:
        self.fields.append((name, default))
        return f"self.settings.{name}"

    def find_indicator(self, operand: IndicatorOperand) -> IndicatorUse:
        definition = INDICATOR_CATALOG[operand.indicator]
        parameters = definition.with_defaults(operand.parameters)
        for indicator in self.indicators:
            if indicator.definition.key == definition.key and indicator.parameters == parameters:
                return indicator
        indicator = IndicatorUse(f"{definition.key}_{len(self.indicators) + 1}", definition, parameters)
        self.indicators.append(indicator)
        for parameter_name, value in parameters.items():
            self.add_field(f"{indicator.name}_{parameter_name}", value)
        return indicator

    def value_names(self, operand: Operand) -> tuple[str, str]:
        """The expressions of the operand at this bar and at the previous bar."""
        if isinstance(operand, NumberOperand):
            threshold = self.add_field(f"threshold_{self.count_thresholds() + 1}", operand.value)
            return threshold, threshold
        if isinstance(operand, PriceOperand):
            key = operand.price
            self.values[key] = f"bar.{key}.as_double()"
        else:
            indicator = self.find_indicator(operand)
            output = operand.output or "value"
            key = indicator.name if output == "value" else f"{indicator.name}_{output}"
            self.values[key] = f"self.{indicator.name}.{output}"
        return f'now["{key}"]', f'previous["{key}"]'

    def count_thresholds(self) -> int:
        return sum(1 for name, _ in self.fields if name.startswith("threshold_"))


def write_condition(parts: CodeParts, condition: RuleCondition) -> str:
    left, previous_left = parts.value_names(condition.left)
    right, previous_right = parts.value_names(condition.right)
    if condition.comparison == "crosses_above":
        return f"(previous is not None and {previous_left} <= {previous_right} and {left} > {right})"
    if condition.comparison == "crosses_below":
        return f"(previous is not None and {previous_left} >= {previous_right} and {left} < {right})"
    return f"{left} {COMPARISON_OPERATORS[condition.comparison]} {right}"


def write_group(parts: CodeParts, group: RuleGroup | InnerRuleGroup, separator: str = " ") -> str:
    """An empty group is false: it never buys and never sells."""
    if not group.items:
        return "False"
    expressions = [
        write_condition(parts, item) if isinstance(item, RuleCondition) else f"({write_group(parts, item)})"
        for item in group.items
    ]
    return f"{separator}{GROUP_OPERATORS[group.match]} ".join(expressions)


def write_exit_checks(parts: CodeParts, rules: StrategyRules) -> list[str]:
    exits = rules.exits
    checks: list[str] = []
    if exits.stop_loss_percent is not None:
        stop_loss = parts.add_field("stop_loss_percent", exits.stop_loss_percent)
        checks.append(f'now["close"] <= position.avg_px_open * (1 - {stop_loss} / 100)')
    if exits.take_profit_percent is not None:
        take_profit = parts.add_field("take_profit_percent", exits.take_profit_percent)
        checks.append(f'now["close"] >= position.avg_px_open * (1 + {take_profit} / 100)')
    if exits.exit_after_bars is not None:
        checks.append(f"self.bars_in_position >= {parts.add_field('exit_after_bars', exits.exit_after_bars)}")
    if exits.exit_when_entry_is_false:
        checks.append("not self.entry_is_true(now, previous)")
    if exits.exit_group is not None:
        checks.append(write_group(parts, exits.exit_group))
    return checks


def write_config(parts: CodeParts) -> list[str]:
    field_lines = [f"        {name}: {type(default).__name__} = {default!r}," for name, default in parts.fields]
    assignments = [f"        self.{name} = {name}" for name, _ in parts.fields]
    return [
        "class RulesConfig(StrategyConfig):",
        "    # NautilusTrader 2.0 needs a keyword-only __init__. ATrade fills instrument_id and bar_type at run time.",
        "    def __init__(",
        "        self,",
        "        *,",
        "        instrument_id: InstrumentId,",
        "        bar_type: BarType,",
        *field_lines,
        "        **kwargs,",
        "    ) -> None:",
        "        super().__init__(**kwargs)",
        "        self.instrument_id = instrument_id",
        "        self.bar_type = bar_type",
        *assignments,
    ]


def write_on_start(parts: CodeParts) -> list[str]:
    registrations = [
        f"        self.register_indicator_for_bars(self.settings.bar_type, self.{indicator.name})"
        for indicator in parts.indicators
    ]
    warm_up = (
        [
            "        bar_length = self.settings.bar_type.spec.timedelta",
            "        warm_up_length = max(bar_length * WARM_UP_BAR_COUNT * WARM_UP_CALENDAR_FACTOR, MIN_WARM_UP_LENGTH)",
            "        self.request_bars(self.settings.bar_type, start=self.clock.utc_now() - warm_up_length)",
        ]
        if parts.indicators
        else []
    )
    return [
        "    def on_start(self) -> None:",
        *registrations,
        *warm_up,
        "        self.subscribe_bars(self.settings.bar_type)",
    ]


def write_buy(rules: StrategyRules, parts: CodeParts) -> list[str]:
    size = rules.settings.position_size
    if isinstance(size, PercentOfEquity):
        percent = parts.add_field("equity_percent", size.percent)
        quantity_lines = [
            "        account = self.portfolio.account(self.settings.instrument_id.venue)",
            "        equity = None if account is None else account.balance_total()",
            "        if equity is None:",
            "            return",
            f"        quantity = math.floor(equity.as_double() * {percent} / 100 / bar.close.as_double())",
        ]
    else:
        quantity_lines = [f"        quantity = {parts.add_field('position_shares', size.shares)}"]
    return [
        "    def buy(self, bar: Bar) -> None:",
        *quantity_lines,
        "        if quantity < 1:",
        "            return",
        "        order = self.order_factory.market(self.settings.instrument_id, OrderSide.BUY, Quantity.from_int(quantity))",
        "        self.submit_order(order)",
    ]


def write_imports(rules: StrategyRules, parts: CodeParts) -> list[str]:
    standard = [
        *(["import math"] if isinstance(rules.settings.position_size, PercentOfEquity) else []),
        *(["from datetime import timedelta"] if parts.indicators else []),
    ]
    return [
        *standard,
        *([""] if standard else []),
        "from nautilus_trader.config import StrategyConfig",
        "from nautilus_trader.model import Bar, BarType, InstrumentId, OrderSide, Position, Quantity",
        "from nautilus_trader.trading import Strategy",
        *(["", "import atrade.indicator"] if parts.indicators else []),
    ]


def count_warm_up_bars(parts: CodeParts) -> int | None:
    """The bars that the longest indicator needs (section 23.4), or None without an indicator."""
    if not parts.indicators:
        return None
    return max(indicator.definition.screen_look_back_bars(indicator.parameters) for indicator in parts.indicators)


def find_warm_up_bar_count(rules: StrategyRules) -> int | None:
    """The look-back bar count of a rule builder version: the bars of its longest indicator (#164).

    The backtest and the forward test give the strategy the last bars of this count before the start.
    """
    parts = CodeParts()
    write_group(parts, rules.entry)
    write_exit_checks(parts, rules)
    return count_warm_up_bars(parts)


def write_warm_up_constants(parts: CodeParts) -> list[str]:
    bar_count = count_warm_up_bars(parts)
    if bar_count is None:
        return []
    return [
        "# The warm-up asks for the bars that the longest indicator needs. The platform gives only the last bars of",
        "# this count before the start. A bar comes only in the trading hours, so the request goes 6 times further back",
        "# in calendar time, and 1 week at least.",
        f"WARM_UP_BAR_COUNT = {bar_count}",
        "WARM_UP_CALENDAR_FACTOR = 6",
        "MIN_WARM_UP_LENGTH = timedelta(days=7)",
        "",
        "",
    ]


def write_strategy(parts: CodeParts, entry: str, exit_checks: list[str], buy: list[str]) -> list[str]:
    indicators = [
        f"        self.{indicator.name} = atrade.indicator.{type_name(indicator)}("
        + ", ".join(f"{name}=config.{indicator.name}_{name}" for name in indicator.parameters)
        + ")"
        for indicator in parts.indicators
    ]
    values = [f'            "{key}": {expression},' for key, expression in parts.values.items()]
    exits = [line for check in exit_checks for line in (f"        if {check}:", "            return True")]
    return [
        "class RulesStrategy(Strategy):",
        "    def __init__(self, config: RulesConfig) -> None:",
        "        super().__init__(config)",
        "        self.settings = config",
        *indicators,
        "        self.previous_values: dict[str, float] | None = None",
        "        self.bars_in_position = 0",
        "",
        *write_on_start(parts),
        "",
        "    def on_bar(self, bar: Bar) -> None:",
        "        position = self.read_open_position()",
        "        self.bars_in_position = 0 if position is None else self.bars_in_position + 1",
        "        now = self.read_values(bar)",
        "        previous = self.previous_values",
        "        self.previous_values = now",
        "        # No rule runs while an indicator has no value or an order waits for its fill.",
        "        waits_for_fill = self.cache.orders_inflight_count(strategy_id=self.strategy_id) > 0",
        "        if now is None or waits_for_fill or self.cache.orders_open_count(strategy_id=self.strategy_id) > 0:",
        "            return",
        "        if position is None:",
        "            if self.entry_is_true(now, previous):",
        "                self.buy(bar)",
        "        elif self.exit_is_true(now, previous, position):",
        "            self.close_position(position)",
        "",
        "    def read_values(self, bar: Bar) -> dict[str, float] | None:",
        '        """The prices and the indicator outputs of the rules at this bar. None when an indicator has no value."""',
        "        values = {",
        *values,
        "        }",
        "        known = {name: value for name, value in values.items() if value is not None}",
        "        return known if len(known) == len(values) else None",
        "",
        "    def entry_is_true(self, now: dict[str, float], previous: dict[str, float] | None) -> bool:",
        "        return (",
        f"            {entry}",
        "        )",
        "",
        "    def exit_is_true(self, now: dict[str, float], previous: dict[str, float] | None, position: Position) -> bool:",
        *exits,
        "        return False",
        "",
        *buy,
        "",
        "    def read_open_position(self) -> Position | None:",
        "        positions = self.cache.positions_open(instrument_id=self.settings.instrument_id, strategy_id=self.strategy_id)",
        "        return positions[0] if positions else None",
    ]


def type_name(indicator: IndicatorUse) -> str:
    return indicator.definition.indicator_class.__name__


def make_rules_code(rules: StrategyRules) -> str:
    """Makes the strategy code of section 9.2 from correct rules."""
    parts = CodeParts()
    entry = write_group(parts, rules.entry, separator="\n            ")
    exit_checks = write_exit_checks(parts, rules)
    buy = write_buy(rules, parts)
    lines = [
        f'"""{RULES_CODE_DOCSTRING}"""',
        "",
        *write_imports(rules, parts),
        "",
        "",
        *write_warm_up_constants(parts),
        *write_config(parts),
        "",
        "",
        *write_strategy(parts, entry, exit_checks, buy),
    ]
    return "\n".join(lines) + "\n"
