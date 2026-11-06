"""Formula expressions of custom indicators (docs/architecture/indicator.md section 23.10, ADR 0009, #372).

An expression is parsed with `ast` and an allow-list. The parser builds a tree of the small classes below. Nothing runs
the text of the expression: no `eval`, no `exec`, no attribute access, and no name outside the allow-list. So a formula
needs no sandbox. `FormulaIndicator` is a normal indicator class: the screen path, the chart path, and the strategy path
use the same code (ADR 0001).
"""

import ast
import math
import operator
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol, cast

from nautilus_trader.model import Bar as NautilusBar

from atrade.foundation.bar import Bar
from atrade.indicator.indicator_catalog import (
    INDICATOR_CATALOG,
    MAXIMUM_PERIOD,
    CatalogIndicator,
    IndicatorDefinition,
    ParameterValue,
)
from atrade.indicator.indicator_problems import IndicatorProblem, check_output, check_parameters
from atrade.indicator.wrapped_indicator import make_nautilus_bar

MAX_EXPRESSION_LENGTH = 500
MAX_DEPTH = 20
MAX_EXPONENT = 10
# The largest look-back of a catalog indicator is 8 x (1000 + 1000): MACD. A formula must not read more.
MAX_LOOK_BACK_BARS = 20_000
# The window bars of all nodes x the bars of the look-back. 10 windows of 1000 bars reach it. The limit stops the
# longest formulas only. A formula near it can run for minutes on many instruments, in a thread (section 23.10.3).
MAX_CALCULATION_BARS = 10_000_000
MIN_STD_WINDOW = 2
BAR_FIELDS = ("open", "high", "low", "close", "volume")
OUTPUT_KEYWORD = "output"
FORMULA_ARGUMENT_COUNT = 2
# Each finite float is an integer multiple of 2^-1074, so a window sum in this unit has no rounding error.
EXACT_UNIT_BITS = 1074
EXACT_ONE = 1 << EXACT_UNIT_BITS
# The extra bits of the square root of a variance: more than the 53 bits of a float.
SQUARE_ROOT_BITS = 64


def calculate(function: Callable[[], float | None]) -> float | None:
    """A divide by zero, a math domain problem, an overflow, NaN, and infinity give "no value"."""
    try:
        value = function()
    except ArithmeticError, ValueError:
        # readability-exception: the math functions report these cases only as exceptions.
        return None
    return value if value is not None and math.isfinite(value) else None


class FormulaNode(Protocol):
    """One part of an expression. Each node gets each bar, so a rolling part never misses a bar."""

    @property
    def look_back(self) -> int: ...

    @property
    def window_bars(self) -> int:
        """The sum of the windows of this node and its children (`MAX_CALCULATION_BARS`)."""
        ...

    def update(self, bar: NautilusBar) -> float | None: ...


@dataclass
class NumberNode:
    number: float
    look_back: int = 1
    window_bars: int = 0

    def update(self, bar: NautilusBar) -> float | None:
        return self.number


@dataclass
class BarFieldNode:
    name: str
    look_back: int = 1
    window_bars: int = 0

    def update(self, bar: NautilusBar) -> float | None:
        return cast("float", getattr(bar, self.name).as_double())


@dataclass
class ScalarNode:
    """A function of the values of its children at this bar."""

    function: Callable[..., float]
    children: tuple[FormulaNode, ...]

    @property
    def look_back(self) -> int:
        return max(child.look_back for child in self.children)

    @property
    def window_bars(self) -> int:
        return sum(child.window_bars for child in self.children)

    def update(self, bar: NautilusBar) -> float | None:
        values = [child.update(bar) for child in self.children]
        if any(value is None for value in values):
            return None
        return calculate(lambda: self.function(*values))


def to_exact(value: float) -> int:
    """A finite float as an integer number of `EXACT_ONE` parts."""
    numerator, denominator = value.as_integer_ratio()
    return numerator << (EXACT_UNIT_BITS + 1 - denominator.bit_length())


class WindowMeasure(Protocol):
    """A function of a window. Each bar adds one value and removes one value, so no bar reads the full window."""

    def add(self, value: float) -> None: ...

    def remove(self, value: float) -> None: ...

    def read(self, count: int) -> float: ...


class WindowSum:
    """`math.fsum` of the window. Integers keep each digit, so a large value that leaves the window leaves no error."""

    def __init__(self) -> None:
        self.total = 0

    def add(self, value: float) -> None:
        self.total += to_exact(value)

    def remove(self, value: float) -> None:
        self.total -= to_exact(value)

    def read(self, count: int) -> float:
        return self.total / EXACT_ONE


class WindowMean(WindowSum):
    def read(self, count: int) -> float:
        return super().read(count) / count


class WindowDeviation(WindowSum):
    """The sample standard deviation: sqrt((n x sum of squares - sum x sum) / (n x (n - 1)))."""

    def __init__(self) -> None:
        super().__init__()
        self.squares = 0

    def add(self, value: float) -> None:
        super().add(value)
        self.squares += to_exact(value) ** 2

    def remove(self, value: float) -> None:
        super().remove(value)
        self.squares -= to_exact(value) ** 2

    def read(self, count: int) -> float:
        spread = count * self.squares - self.total * self.total
        scaled_variance = (spread << (2 * SQUARE_ROOT_BITS)) // (count * (count - 1))
        return math.isqrt(scaled_variance) / (EXACT_ONE << SQUARE_ROOT_BITS)


class WindowExtreme:
    """`max` or `min` of the window. `kept` holds the values that can become the extreme, the extreme first."""

    def __init__(self, is_beaten_by: Callable[[float, float], bool]) -> None:
        self.is_beaten_by = is_beaten_by
        self.kept: deque[float] = deque()

    def add(self, value: float) -> None:
        while self.kept and self.is_beaten_by(self.kept[-1], value):
            self.kept.pop()
        self.kept.append(value)

    def remove(self, value: float) -> None:
        if self.kept[0] == value:
            self.kept.popleft()

    def read(self, count: int) -> float:
        return self.kept[0]


class RollingNode:
    """A function of the last `window` values of its child. A value is "no value" while one value of the window is."""

    def __init__(self, measure: WindowMeasure, child: FormulaNode, window: int) -> None:
        self.measure = measure
        self.child = child
        self.window = window
        self.values: deque[float | None] = deque(maxlen=window)
        self.known_count = 0

    @property
    def look_back(self) -> int:
        return self.child.look_back + self.window - 1

    @property
    def window_bars(self) -> int:
        return self.child.window_bars + self.window

    def update(self, bar: NautilusBar) -> float | None:
        if len(self.values) == self.window and self.values[0] is not None:
            self.measure.remove(self.values[0])
            self.known_count -= 1
        value = self.child.update(bar)
        self.values.append(value)
        if value is not None:
            self.measure.add(value)
            self.known_count += 1
        if self.known_count < self.window:
            return None
        return calculate(lambda: self.measure.read(self.window))


class LagNode:
    """The value of the child `bars` bars ago."""

    def __init__(self, child: FormulaNode, bars: int) -> None:
        self.child = child
        self.bars = bars
        self.values: deque[float | None] = deque(maxlen=bars + 1)

    @property
    def look_back(self) -> int:
        return self.child.look_back + self.bars

    @property
    def window_bars(self) -> int:
        return self.child.window_bars + self.bars

    def update(self, bar: NautilusBar) -> float | None:
        self.values.append(self.child.update(bar))
        return self.values[0] if len(self.values) > self.bars else None


class CatalogNode:
    """One output of a class of the indicator catalog."""

    def __init__(self, indicator: CatalogIndicator, output: str, look_back: int, window_bars: int) -> None:
        self.indicator = indicator
        self.output = output
        self.look_back = look_back
        self.window_bars = window_bars

    def update(self, bar: NautilusBar) -> float | None:
        self.indicator.handle_bar(bar)
        return calculate(lambda: cast("float | None", getattr(self.indicator, self.output)))


def add(left: float, right: float) -> float:
    return left + right


def subtract(left: float, right: float) -> float:
    return left - right


def multiply(left: float, right: float) -> float:
    return left * right


def divide(left: float, right: float) -> float:
    return left / right


def negate(value: float) -> float:
    return -value


def find_absolute(value: float) -> float:
    return abs(value)


def find_log(value: float) -> float:
    return math.log(value)


BINARY_OPERATORS: dict[type[ast.operator], Callable[..., float]] = {
    ast.Add: add,
    ast.Sub: subtract,
    ast.Mult: multiply,
    ast.Div: divide,
}


def make_maximum() -> WindowExtreme:
    return WindowExtreme(operator.lt)


def make_minimum() -> WindowExtreme:
    return WindowExtreme(operator.gt)


ROLLING_FUNCTIONS: dict[str, Callable[[], WindowMeasure]] = {
    "mean": WindowMean,
    "max": make_maximum,
    "min": make_minimum,
    "sum": WindowSum,
    "std": WindowDeviation,
}
SCALAR_FUNCTIONS: dict[str, Callable[..., float]] = {"abs": find_absolute, "log": find_log}
OPERATOR_SYMBOLS: dict[type[ast.AST], str] = {
    ast.Mod: "%",
    ast.FloorDiv: "//",
    ast.MatMult: "@",
    ast.LShift: "<<",
    ast.RShift: ">>",
    ast.BitOr: "|",
    ast.BitXor: "^",
    ast.BitAnd: "&",
    ast.Not: "not",
    ast.Invert: "~",
}


class FormulaProblem(Exception):
    """The first problem of an expression. `column` starts at 1."""

    def __init__(self, column: int, message: str) -> None:
        super().__init__(message)
        self.column = column
        self.message = message


def refuse(node: ast.AST, message: str) -> FormulaProblem:
    return FormulaProblem(getattr(node, "col_offset", 0) + 1, message)


def read_tree(expression: str) -> ast.expr:
    """The `ast` tree of the text. `ast.parse` reads the text and runs nothing."""
    if not expression.strip():
        raise FormulaProblem(1, "The expression must not be empty.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise FormulaProblem(
            MAX_EXPRESSION_LENGTH + 1, f"An expression has at most {MAX_EXPRESSION_LENGTH} characters."
        )
    try:
        return ast.parse(expression.strip(), mode="eval").body
    except SyntaxError as error:
        # readability-exception: ast.parse reports a syntax error only as an exception.
        raise FormulaProblem(error.offset or 1, f"The expression has a syntax error: {error.msg}.") from error
    except (ValueError, RecursionError, MemoryError) as error:
        # readability-exception: ast.parse reports a null byte or a very deep text only as these exceptions.
        raise FormulaProblem(1, "The expression is too deep or has a character that is not allowed.") from error


def parse_expression(expression: str) -> FormulaNode:
    """The tree of nodes of a correct expression. Raises `FormulaProblem` for the first problem."""
    tree = read_tree(expression)
    root = parse_node(tree, 1)
    if root.look_back > MAX_LOOK_BACK_BARS:
        message = f"An expression reads at most {MAX_LOOK_BACK_BARS} bars, not {root.look_back}."
        raise FormulaProblem(1, message)
    calculation_bars = root.window_bars * root.look_back
    if calculation_bars > MAX_CALCULATION_BARS:
        message = (
            f"The windows of the expression have {root.window_bars} bars, and the expression reads {root.look_back} "
            f"bars. Window bars x bars read must be at most {MAX_CALCULATION_BARS}, not {calculation_bars}. "
            "Use fewer or shorter windows."
        )
        raise FormulaProblem(1, message)
    return root


def parse_node(node: ast.expr, depth: int) -> FormulaNode:
    if depth > MAX_DEPTH:
        raise refuse(node, f"The expression is too deep: at most {MAX_DEPTH} levels.")
    match node:
        case ast.Constant():
            return NumberNode(read_number(node))
        case ast.Name():
            return read_bar_field(node)
        case ast.BinOp():
            return parse_binary(node, depth)
        case ast.UnaryOp():
            return parse_unary(node, depth)
        case ast.Call():
            return parse_call(node, depth)
        case ast.Attribute():
            raise refuse(node, "Attribute access is not allowed.")
        case _:
            raise refuse(node, f"{type(node).__name__} is not allowed.")


def read_number(node: ast.Constant) -> float:
    if isinstance(node.value, str):
        raise refuse(node, "Text is allowed only as the output of an indicator.")
    # bool is a subclass of int, so this is `type`, not `isinstance`.
    if type(node.value) not in {int, float}:
        raise refuse(node, f"Only numbers, bar fields, and functions are allowed, not {node.value!r}.")
    try:
        number = float(cast("int | float", node.value))
    except OverflowError:
        # readability-exception: float() reports a too large integer only as an exception.
        number = math.inf
    if not math.isfinite(number):
        raise refuse(node, "A number must be finite.")
    return number


def read_bar_field(node: ast.Name) -> FormulaNode:
    if node.id not in BAR_FIELDS:
        raise refuse(node, f"Unknown name {node.id!r}. Known names: {', '.join(BAR_FIELDS)}.")
    return BarFieldNode(node.id)


def parse_binary(node: ast.BinOp, depth: int) -> FormulaNode:
    if isinstance(node.op, ast.Pow):
        exponent = read_exponent(node.right)

        def raise_to_exponent(base: float) -> float:
            return math.pow(base, exponent)

        return ScalarNode(raise_to_exponent, (parse_node(node.left, depth + 1),))
    known = BINARY_OPERATORS.get(type(node.op))
    if known is None:
        raise refuse(node, f"The operator {OPERATOR_SYMBOLS.get(type(node.op), '?')} is not allowed.")
    return ScalarNode(known, (parse_node(node.left, depth + 1), parse_node(node.right, depth + 1)))


def read_exponent(node: ast.expr) -> float:
    """`**` takes a fixed exponent, so a run cannot calculate a huge power."""
    is_negative = isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
    constant = node.operand if isinstance(node, ast.UnaryOp) and is_negative else node
    if isinstance(constant, ast.Constant) and type(constant.value) in {int, float}:
        exponent = cast("float", constant.value)
        if abs(exponent) <= MAX_EXPONENT:
            return -exponent if is_negative else exponent
    raise refuse(node, f"The exponent must be a number from -{MAX_EXPONENT} to {MAX_EXPONENT}.")


def parse_unary(node: ast.UnaryOp, depth: int) -> FormulaNode:
    operand = parse_node_after_operator(node, depth)
    if isinstance(node.op, ast.UAdd):
        return operand
    return ScalarNode(negate, (operand,))


def parse_node_after_operator(node: ast.UnaryOp, depth: int) -> FormulaNode:
    if not isinstance(node.op, ast.USub | ast.UAdd):
        raise refuse(node, f"The operator {OPERATOR_SYMBOLS.get(type(node.op), '?')} is not allowed.")
    return parse_node(node.operand, depth + 1)


def parse_call(node: ast.Call, depth: int) -> FormulaNode:
    if isinstance(node.func, ast.Attribute):
        raise refuse(node.func, "Attribute access is not allowed.")
    name = node.func.id if isinstance(node.func, ast.Name) else None
    if name is None:
        raise refuse(node, "Only a function name can be called.")
    if name in ROLLING_FUNCTIONS or name == "lag":
        return parse_window_call(node, name, depth)
    if name in SCALAR_FUNCTIONS:
        return parse_scalar_call(node, name, depth)
    definition = INDICATOR_CATALOG.get(name)
    if definition is None:
        known = ", ".join([*ROLLING_FUNCTIONS, "lag", *SCALAR_FUNCTIONS, *INDICATOR_CATALOG])
        raise refuse(node, f"Unknown function {name!r}. Known functions: {known}.")
    return parse_catalog_call(node, definition)


def parse_window_call(node: ast.Call, name: str, depth: int) -> FormulaNode:
    if node.keywords:
        raise refuse(node, f"{name} takes no keyword arguments.")
    if len(node.args) != FORMULA_ARGUMENT_COUNT:
        raise refuse(node, f"{name} needs 2 arguments: a value and a number of bars.")
    child = parse_node(node.args[0], depth + 1)
    size = read_window(node.args[1], MIN_STD_WINDOW if name == "std" else 1)
    return LagNode(child, size) if name == "lag" else RollingNode(ROLLING_FUNCTIONS[name](), child, size)


def read_window(node: ast.expr, minimum: int) -> int:
    if not (isinstance(node, ast.Constant) and type(node.value) is int):
        raise refuse(node, "The number of bars must be an integer.")
    if not minimum <= node.value <= MAXIMUM_PERIOD:
        raise refuse(node, f"The number of bars must be from {minimum} to {MAXIMUM_PERIOD}, not {node.value}.")
    return node.value


def parse_scalar_call(node: ast.Call, name: str, depth: int) -> FormulaNode:
    if node.keywords or len(node.args) != 1:
        raise refuse(node, f"{name} needs 1 argument.")
    return ScalarNode(SCALAR_FUNCTIONS[name], (parse_node(node.args[0], depth + 1),))


def parse_catalog_call(node: ast.Call, definition: IndicatorDefinition) -> FormulaNode:
    if len(node.args) > len(definition.parameters):
        raise refuse(node, f"{definition.key} takes at most {len(definition.parameters)} argument(s).")
    names = [parameter.name for parameter in definition.parameters]
    written: dict[str, ast.expr] = dict(zip(names, node.args, strict=False))
    output: str | None = None
    for keyword in node.keywords:
        if keyword.arg is None:
            raise refuse(node, "`**` is not allowed.")
        if keyword.arg == OUTPUT_KEYWORD:
            output = read_output_name(keyword.value)
        elif keyword.arg in written:
            raise refuse(keyword.value, f"The parameter {keyword.arg!r} is given more than 1 time.")
        else:
            written[keyword.arg] = keyword.value
    parameters = {name: read_parameter(name, value) for name, value in written.items()}
    problems: list[IndicatorProblem] = [*check_parameters(definition, parameters), *check_output(definition, output)]
    if problems:
        raise refuse(node, problems[0].message)
    values = definition.with_defaults(parameters)
    indicator = definition.indicator_class(**values)
    look_back = definition.screen_look_back_bars(values)
    # A look-back factor marks an exponential average: it keeps one number for each bar, and has no window.
    return CatalogNode(indicator, output or "value", look_back, 0 if definition.look_back.factor > 1 else look_back)


def read_output_name(node: ast.expr) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    raise refuse(node, 'The output must be a text, for example "signal".')


def read_parameter(name: str, node: ast.expr) -> ParameterValue:
    if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
        return cast("ParameterValue", node.value)
    raise refuse(node, f"The {name} must be a number.")


def check_expression(expression: str) -> list[IndicatorProblem]:
    """Returns the problem of an expression. An empty list means the expression is correct."""
    try:
        parse_expression(expression)
    except FormulaProblem as problem:
        return [IndicatorProblem(("expression",), f"Column {problem.column}: {problem.message}")]
    return []


# A screen run reads the name of each indicator for each instrument and condition, on the event loop.
@lru_cache(maxsize=1024)
def count_formula_bars(expression: str) -> int:
    """The bars that a correct expression needs for its value. The parser calculates it (section 23.10.3)."""
    return parse_expression(expression).look_back


class FormulaIndicator:
    """The value of a formula expression, for example `close / sma(50) - 1`. A strategy version holds the text of the
    expression, so a run needs no database read. The value is None ("no value") when the expression has no number.
    """

    def __init__(self, expression: str) -> None:
        problems = check_expression(expression)
        if problems:
            raise ValueError(problems[0].message)
        self.expression = expression
        self.value: float | None = None
        self._root = parse_expression(expression)

    @property
    def initialized(self) -> bool:
        return self.value is not None

    def handle_bar(self, bar: NautilusBar) -> None:
        self.value = self._root.update(bar)

    def update(self, bar: Bar) -> None:
        self.handle_bar(make_nautilus_bar(bar))

    def reset(self) -> None:
        self.value = None
        self._root = parse_expression(self.expression)
