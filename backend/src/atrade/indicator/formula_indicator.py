"""Formula expressions of custom indicators (docs/architecture/indicator.md section 23.10, ADR 0009, #372).

An expression is parsed with `ast` and an allow-list. The parser builds a tree of the small classes below. Nothing runs
the text of the expression: no `eval`, no `exec`, no attribute access, and no name outside the allow-list. So a formula
needs no sandbox. `FormulaIndicator` is a normal indicator class: the screen path, the chart path, and the strategy path
use the same code (ADR 0001).
"""

import ast
import bisect
import math
import operator
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol, cast

from nautilus_trader.model import Bar as NautilusBar

from atrade.indicator.indicator_catalog import (
    INDICATOR_CATALOG,
    MAXIMUM_PERIOD,
    CatalogIndicator,
    IndicatorDefinition,
    IndicatorParameter,
    ParameterValue,
    ParameterValues,
)
from atrade.indicator.indicator_problems import IndicatorProblem, check_output, check_parameters

MAX_EXPRESSION_LENGTH = 1000
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
MEDIAN_QUANTILE = 0.5
WINDOW_ARGUMENT_COUNT = 2
QUANTILE_ARGUMENT_COUNT = 3
# A larger parameter value has no use, and a float keeps each integer to this size.
MAX_PARAMETER_SIZE = 1e15
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


class WindowQuantile:
    """The quantile `quantile` of the window, with linear interpolation between the 2 nearest values (the NumPy
    default). `ordered` holds the values of the window, the smallest first."""

    def __init__(self, quantile: float) -> None:
        self.quantile = quantile
        self.ordered: list[float] = []

    def add(self, value: float) -> None:
        bisect.insort(self.ordered, value)

    def remove(self, value: float) -> None:
        del self.ordered[bisect.bisect_left(self.ordered, value)]

    def read(self, count: int) -> float:
        position = self.quantile * (count - 1)
        lower = int(position)
        below = self.ordered[lower]
        above = self.ordered[min(lower + 1, count - 1)]
        return below + (above - below) * (position - lower)


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


class VariableNode:
    """A variable: a value with a name, for example `width = std(close, 20) / mean(close, 20)`. The program calculates it
    1 time for each bar, and each use reads that value. So a use adds no window."""

    def __init__(self, child: FormulaNode) -> None:
        self.child = child
        self.value: float | None = None
        self.window_bars = 0

    @property
    def look_back(self) -> int:
        return self.child.look_back

    def update(self, bar: NautilusBar) -> float | None:
        return self.value


@dataclass
class ProgramNode:
    """The variables in the order of the text, then the value of the indicator."""

    variables: tuple[VariableNode, ...]
    result: FormulaNode

    @property
    def look_back(self) -> int:
        return self.result.look_back

    @property
    def window_bars(self) -> int:
        return sum(variable.child.window_bars for variable in self.variables) + self.result.window_bars

    def update(self, bar: NautilusBar) -> float | None:
        for variable in self.variables:
            variable.value = variable.child.update(bar)
        return self.result.update(bar)


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
QUANTILE_FUNCTIONS = ("quantile", "median")
WINDOW_FUNCTIONS = (*ROLLING_FUNCTIONS, "lag", *QUANTILE_FUNCTIONS)
SCALAR_FUNCTIONS: dict[str, Callable[..., float]] = {"abs": find_absolute, "log": find_log}
QUANTILE_LIMIT = IndicatorParameter("quantile", float, MEDIAN_QUANTILE, 0, 1)
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
    """The first problem of an expression. `column` and `line` start at 1."""

    def __init__(self, column: int, message: str, line: int = 1) -> None:
        super().__init__(message)
        self.column = column
        self.message = message
        self.line = line

    def __reduce__(self) -> tuple[type[FormulaProblem], tuple[int, str, int]]:
        """A process pool sends an exception back with pickle. The default repeats only the `Exception` arguments."""
        return FormulaProblem, (self.column, self.message, self.line)

    def describe(self) -> str:
        place = f"Column {self.column}" if self.line == 1 else f"Line {self.line}, column {self.column}"
        return f"{place}: {self.message}"


def refuse(node: ast.AST, message: str) -> FormulaProblem:
    return FormulaProblem(getattr(node, "col_offset", 0) + 1, message, getattr(node, "lineno", 1))


@dataclass
class Scope:
    """The names of an expression that are not bar fields: the parameters with their values, and the variables."""

    parameters: dict[str, IndicatorParameter]
    values: dict[str, ParameterValue]
    variables: dict[str, VariableNode] = field(default_factory=dict[str, VariableNode])
    used: set[str] = field(default_factory=set[str])

    def read_names(self) -> str:
        return ", ".join([*BAR_FIELDS, *self.parameters, *self.variables])


def fix_parameters(values: ParameterValues) -> tuple[IndicatorParameter, ...]:
    """Parameters that have only the given value, for an expression that runs with these values."""
    return tuple(IndicatorParameter(name, type(value), value, value, value) for name, value in values.items())


def read_statements(expression: str) -> list[ast.stmt]:
    """The `ast` statements of the text. `ast.parse` reads the text and runs nothing."""
    if not expression.strip():
        raise FormulaProblem(1, "The expression must not be empty.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise FormulaProblem(
            MAX_EXPRESSION_LENGTH + 1, f"An expression has at most {MAX_EXPRESSION_LENGTH} characters."
        )
    text = expression.strip()
    try:
        statements = ast.parse(text).body
    except SyntaxError as error:
        # readability-exception: ast.parse reports a syntax error only as an exception. Offset 0: the text ended early.
        column = error.offset or len(text) + 1
        message = f"The expression has a syntax error: {error.msg}."
        raise FormulaProblem(column, message, error.lineno or 1) from error
    except (ValueError, RecursionError, MemoryError) as error:
        # readability-exception: ast.parse reports a null byte or a very deep text only as these exceptions.
        raise FormulaProblem(1, "The expression is too deep or has a character that is not allowed.") from error
    if not statements:
        raise FormulaProblem(1, "The expression must not be empty.")
    return statements


def parse_expression(
    expression: str, parameters: Sequence[IndicatorParameter] = (), values: ParameterValues | None = None
) -> FormulaNode:
    """The tree of nodes of a correct expression. Raises `FormulaProblem` for the first problem.

    `values` has the value of each parameter. A parameter without a value has its default.
    """
    *assignments, last = read_statements(expression)
    scope = Scope(
        {parameter.name: parameter for parameter in parameters},
        {parameter.name: (values or {}).get(parameter.name, parameter.default) for parameter in parameters},
    )
    for statement in assignments:
        parse_assignment(statement, scope)
    if not isinstance(last, ast.Expr):
        raise refuse(last, "The last line must be the value of the indicator, for example `close / sma(50) - 1`.")
    result = parse_node(last.value, 1, scope)
    for name in (*scope.variables, *scope.parameters):
        if name not in scope.used:
            kind = "variable" if name in scope.variables else "parameter"
            raise FormulaProblem(1, f"The expression does not use the {kind} {name!r}.")
    root = ProgramNode(tuple(scope.variables.values()), result) if scope.variables else result
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


def parse_assignment(statement: ast.stmt, scope: Scope) -> None:
    """`name = expression`: a variable that the lines after it can use."""
    if not isinstance(statement, ast.Assign):
        message = "Each line before the last line must give a name to a value, for example `width = high - low`."
        raise refuse(statement, message)
    target = statement.targets[0]
    if len(statement.targets) > 1 or not isinstance(target, ast.Name):
        raise refuse(target, "A line gives 1 name to 1 value, for example `width = high - low`.")
    if target.id in BAR_FIELDS or target.id in scope.parameters or target.id in scope.variables:
        raise refuse(target, f"The name {target.id!r} is in use. Use another name.")
    # The name is known only after its line, so a variable cannot use itself.
    variable = VariableNode(parse_node(statement.value, 1, scope))
    scope.variables[target.id] = variable


def parse_node(node: ast.expr, depth: int, scope: Scope) -> FormulaNode:
    if depth > MAX_DEPTH:
        raise refuse(node, f"The expression is too deep: at most {MAX_DEPTH} levels.")
    match node:
        case ast.Constant():
            return NumberNode(read_number(node))
        case ast.Name():
            return read_name(node, scope)
        case ast.BinOp():
            return parse_binary(node, depth, scope)
        case ast.UnaryOp():
            return parse_unary(node, depth, scope)
        case ast.Call():
            return parse_call(node, depth, scope)
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


def read_name(node: ast.Name, scope: Scope) -> FormulaNode:
    if node.id in BAR_FIELDS:
        return BarFieldNode(node.id)
    scope.used.add(node.id)
    if node.id in scope.variables:
        return scope.variables[node.id]
    if node.id in scope.parameters:
        return NumberNode(float(scope.values[node.id]))
    raise refuse(node, f"Unknown name {node.id!r}. Known names: {scope.read_names()}.")


def read_parameter_value(node: ast.expr, scope: Scope, limit: IndicatorParameter) -> ParameterValue | None:
    """The value of the parameter that `node` names, or None when `node` is not a parameter.

    The range of the parameter must be in the range of `limit`, so each value that the user can set is correct.
    """
    if not isinstance(node, ast.Name) or node.id in BAR_FIELDS or node.id in scope.variables:
        return None
    if node.id not in scope.parameters:
        raise refuse(node, f"Unknown name {node.id!r}. Known names: {scope.read_names()}.")
    parameter = scope.parameters[node.id]
    scope.used.add(node.id)
    if limit.value_type is int and parameter.value_type is not int:
        message = f"The {limit.name} must be an integer, but the parameter {parameter.name!r} is not an integer."
        raise refuse(node, message)
    if not limit.minimum <= parameter.minimum <= parameter.maximum <= limit.maximum:
        message = (
            f"The {limit.name} must be from {limit.minimum} to {limit.maximum}, but the parameter {parameter.name!r} "
            f"is from {parameter.minimum} to {parameter.maximum}."
        )
        raise refuse(node, message)
    return scope.values[node.id]


def parse_binary(node: ast.BinOp, depth: int, scope: Scope) -> FormulaNode:
    if isinstance(node.op, ast.Pow):
        exponent = read_exponent(node.right)

        def raise_to_exponent(base: float) -> float:
            return math.pow(base, exponent)

        return ScalarNode(raise_to_exponent, (parse_node(node.left, depth + 1, scope),))
    known = BINARY_OPERATORS.get(type(node.op))
    if known is None:
        raise refuse(node, f"The operator {OPERATOR_SYMBOLS.get(type(node.op), '?')} is not allowed.")
    return ScalarNode(known, (parse_node(node.left, depth + 1, scope), parse_node(node.right, depth + 1, scope)))


def read_exponent(node: ast.expr) -> float:
    """`**` takes a fixed exponent, so a run cannot calculate a huge power."""
    is_negative = isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
    constant = node.operand if isinstance(node, ast.UnaryOp) and is_negative else node
    if isinstance(constant, ast.Constant) and type(constant.value) in {int, float}:
        exponent = cast("float", constant.value)
        if abs(exponent) <= MAX_EXPONENT:
            return -exponent if is_negative else exponent
    raise refuse(node, f"The exponent must be a number from -{MAX_EXPONENT} to {MAX_EXPONENT}.")


def parse_unary(node: ast.UnaryOp, depth: int, scope: Scope) -> FormulaNode:
    operand = parse_node_after_operator(node, depth, scope)
    if isinstance(node.op, ast.UAdd):
        return operand
    return ScalarNode(negate, (operand,))


def parse_node_after_operator(node: ast.UnaryOp, depth: int, scope: Scope) -> FormulaNode:
    if not isinstance(node.op, ast.USub | ast.UAdd):
        raise refuse(node, f"The operator {OPERATOR_SYMBOLS.get(type(node.op), '?')} is not allowed.")
    return parse_node(node.operand, depth + 1, scope)


def parse_call(node: ast.Call, depth: int, scope: Scope) -> FormulaNode:
    if isinstance(node.func, ast.Attribute):
        raise refuse(node.func, "Attribute access is not allowed.")
    name = node.func.id if isinstance(node.func, ast.Name) else None
    if name is None:
        raise refuse(node, "Only a function name can be called.")
    if name in WINDOW_FUNCTIONS:
        return parse_window_call(node, name, depth, scope)
    if name in SCALAR_FUNCTIONS:
        return parse_scalar_call(node, name, depth, scope)
    definition = INDICATOR_CATALOG.get(name)
    if definition is None:
        known = ", ".join([*WINDOW_FUNCTIONS, *SCALAR_FUNCTIONS, *INDICATOR_CATALOG])
        raise refuse(node, f"Unknown function {name!r}. Known functions: {known}.")
    return parse_catalog_call(node, definition, scope)


def parse_window_call(node: ast.Call, name: str, depth: int, scope: Scope) -> FormulaNode:
    if node.keywords:
        raise refuse(node, f"{name} takes no keyword arguments.")
    if name == "quantile":
        if len(node.args) != QUANTILE_ARGUMENT_COUNT:
            raise refuse(node, "quantile needs 3 arguments: a value, a number of bars, and a quantile from 0 to 1.")
    elif len(node.args) != WINDOW_ARGUMENT_COUNT:
        raise refuse(node, f"{name} needs 2 arguments: a value and a number of bars.")
    child = parse_node(node.args[0], depth + 1, scope)
    size = read_window(node.args[1], MIN_STD_WINDOW if name == "std" else 1, scope)
    if name == "lag":
        return LagNode(child, size)
    if name in QUANTILE_FUNCTIONS:
        quantile = MEDIAN_QUANTILE if name == "median" else read_quantile(node.args[2], scope)
        return RollingNode(WindowQuantile(quantile), child, size)
    return RollingNode(ROLLING_FUNCTIONS[name](), child, size)


def read_window(node: ast.expr, minimum: int, scope: Scope) -> int:
    limit = IndicatorParameter("number of bars", int, minimum, minimum, MAXIMUM_PERIOD)
    value = read_parameter_value(node, scope, limit)
    if value is not None:
        return int(value)
    if not (isinstance(node, ast.Constant) and type(node.value) is int):
        raise refuse(node, "The number of bars must be an integer.")
    if not minimum <= node.value <= MAXIMUM_PERIOD:
        raise refuse(node, f"The number of bars must be from {minimum} to {MAXIMUM_PERIOD}, not {node.value}.")
    return node.value


def read_quantile(node: ast.expr, scope: Scope) -> float:
    value = read_parameter_value(node, scope, QUANTILE_LIMIT)
    if value is not None:
        return float(value)
    if isinstance(node, ast.Constant) and type(node.value) in {int, float} and 0 <= cast("float", node.value) <= 1:
        return float(cast("float", node.value))
    raise refuse(node, "The quantile must be a number from 0 to 1, for example 0.5 for the median.")


def parse_scalar_call(node: ast.Call, name: str, depth: int, scope: Scope) -> FormulaNode:
    if node.keywords or len(node.args) != 1:
        raise refuse(node, f"{name} needs 1 argument.")
    return ScalarNode(SCALAR_FUNCTIONS[name], (parse_node(node.args[0], depth + 1, scope),))


def parse_catalog_call(node: ast.Call, definition: IndicatorDefinition, scope: Scope) -> FormulaNode:
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
    limits = {parameter.name: parameter for parameter in definition.parameters}
    parameters = {name: read_parameter(name, value, scope, limits.get(name)) for name, value in written.items()}
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


def read_parameter(name: str, node: ast.expr, scope: Scope, limit: IndicatorParameter | None) -> ParameterValue:
    """`limit` is None for a name that the indicator does not have. `check_parameters` gives that problem."""
    value = None if limit is None else read_parameter_value(node, scope, limit)
    if value is not None:
        return value
    if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
        return cast("ParameterValue", node.value)
    raise refuse(node, f"The {name} must be a number.")


def check_expression(expression: str, parameters: Sequence[IndicatorParameter] = ()) -> list[IndicatorProblem]:
    """Returns the problem of an expression. An empty list means the expression is correct.

    The check uses the maximum of each parameter, then the default. The bars of an expression do not decrease when a
    parameter increases, so an expression that passes stays in the limits for each value that the user can set.
    """
    try:
        parse_expression(expression, parameters, {parameter.name: parameter.maximum for parameter in parameters})
        parse_expression(expression, parameters)
    except FormulaProblem as problem:
        return [IndicatorProblem(("expression",), problem.describe())]
    return []


# A screen run reads the name of each indicator for each instrument and condition, on the event loop.
@lru_cache(maxsize=1024)
def count_formula_bars(expression: str, values: tuple[tuple[str, ParameterValue], ...] = ()) -> int:
    """The bars that a correct expression needs for its value with these parameter values. The parser calculates it
    (section 23.10.3)."""
    return parse_expression(expression, fix_parameters(dict(values))).look_back


class FormulaIndicator:
    """The value of a formula expression, for example `close / sma(50) - 1`. A strategy version holds the text of the
    expression, so a run needs no database read. The value is None ("no value") when the expression has no number.
    """

    def __init__(self, expression: str, parameters: ParameterValues | None = None) -> None:
        """`parameters` has the value of each parameter name of the expression, for example `{"lookback_days": 20}`."""
        self.expression = expression
        self.parameters = dict(parameters or {})
        for name, value in self.parameters.items():
            if type(value) not in {int, float} or not abs(value) <= MAX_PARAMETER_SIZE:
                message = f"The parameter {name!r} must be a number from -1e15 to 1e15, not {value!r}."
                raise ValueError(message)
        self.value: float | None = None
        self._root = self._parse()

    def _parse(self) -> FormulaNode:
        try:
            return parse_expression(self.expression, fix_parameters(self.parameters))
        except FormulaProblem as problem:
            raise ValueError(problem.describe()) from problem

    @property
    def initialized(self) -> bool:
        return self.value is not None

    def handle_bar(self, bar: NautilusBar) -> None:
        self.value = self._root.update(bar)

    def reset(self) -> None:
        self.value = None
        self._root = self._parse()
