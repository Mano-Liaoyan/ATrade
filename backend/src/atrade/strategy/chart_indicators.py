"""Chart indicators in the strategy code (docs/architecture/strategy.md sections 9.2 and 9.3, #334).

The code can have a top-level `CHART_INDICATORS`: a list literal of `{"indicator": ..., "parameters": {...}}` dict
literals. A parameter value is an `int` or `float` literal, or the name of a configuration field with an `int` or
`float` default. The bar chart of a backtest or a forward test shows these indicators
(docs/architecture/indicator.md section 23.9.8). The reading uses `ast` only. It does not import or run the code.
"""

import ast
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import NotRequired, TypedDict, cast

from atrade.indicator import check_indicator_reference
from atrade.strategy.code_syntax import CodeProblem
from atrade.strategy.strategy_parameters import read_module_parameters

CHART_INDICATORS_NAME = "CHART_INDICATORS"
NUMBER_FIELD_TYPES = ("int", "float")
# The location of a parameter in an indicator problem is ("parameters", <name>).
PARAMETERS_LOCATION = ("parameters",)
LIST_MESSAGE = f"{CHART_INDICATORS_NAME} must be a list literal of dict literals."

type ParameterNumber = int | float


class ChartIndicatorFormula(TypedDict):
    name: str
    expression: str
    chart_placement: str
    parameters: NotRequired[list[dict[str, object]]]


class ChartIndicator(TypedDict):
    """A whole indicator of the chart with its parameter values, as `{"indicator", "parameters"}` JSON. A custom
    indicator also has `formula` (indicator.md section 23.10)."""

    indicator: str
    parameters: dict[str, ParameterNumber]
    formula: NotRequired[ChartIndicatorFormula]


@dataclass(frozen=True)
class FieldName:
    """A parameter value that names a configuration field."""

    name: str


@dataclass
class ChartItem:
    """One item of `CHART_INDICATORS` as written. `parameters` values are literals or `FieldName`."""

    number: int
    line: int
    fields: dict[str, object] = field(default_factory=dict[str, object])
    parameters: dict[str, object] = field(default_factory=dict[str, object])
    parameter_lines: dict[str, int] = field(default_factory=dict[str, int])


def find_chart_indicator_problems(module: ast.Module) -> list[CodeProblem]:
    """The problems of each `CHART_INDICATORS` of the module. Each problem has the line of its item or value."""
    field_defaults = read_number_fields(module)
    problems: list[CodeProblem] = []
    for value in find_chart_values(module):
        items, format_problems = read_items(value)
        problems += format_problems
        for item in items:
            problems += check_item(item, field_defaults)
    return problems


def list_chart_indicators(code: str, parameters: Mapping[str, object]) -> list[ChartIndicator]:
    """The indicators of `CHART_INDICATORS`. A configuration field name becomes its value in `parameters` (a
    parameter sweep run), else the default of the field.

    Code without `CHART_INDICATORS`, or with a syntax error, gives an empty list. An item that is not correct with
    these values is left out.
    """
    try:
        module = ast.parse(code)
    except SyntaxError:
        # readability-exception: ast.parse reports a syntax error only as an exception.
        return []
    values = find_chart_values(module)
    if not values:
        return []
    field_values = read_number_fields(module)
    for name in field_values:
        run_value = parameters.get(name)
        if isinstance(run_value, int | float) and not isinstance(run_value, bool):
            field_values[name] = run_value
    items, _ = read_items(values[-1])
    chart_indicators: list[ChartIndicator] = []
    for item in items:
        if check_item(item, field_values):
            continue
        resolved = resolve_parameters(item, field_values)
        chart_indicator: ChartIndicator = {
            "indicator": str(item.fields["indicator"]),
            "parameters": cast_numbers(resolved),
        }
        formula = item.fields.get("formula")
        if isinstance(formula, dict):
            chart_indicator["formula"] = cast("ChartIndicatorFormula", formula)
        chart_indicators.append(chart_indicator)
    return chart_indicators


def read_number_fields(module: ast.Module) -> dict[str, ParameterNumber]:
    return {
        parameter.name: parameter.default
        for parameter in read_module_parameters(module)
        if parameter.type in NUMBER_FIELD_TYPES and not isinstance(parameter.default, bool)
    }


def find_chart_values(module: ast.Module) -> list[ast.expr]:
    """The values that the module assigns to `CHART_INDICATORS` at the top level, in the order of the code."""
    values: list[ast.expr] = []
    for node in module.body:
        targets = (
            node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        value = node.value if isinstance(node, ast.Assign | ast.AnnAssign) else None
        if value is not None and any(is_chart_name(target) for target in targets):
            values.append(value)
    return values


def is_chart_name(target: ast.expr) -> bool:
    return isinstance(target, ast.Name) and target.id == CHART_INDICATORS_NAME


def read_items(value: ast.expr) -> tuple[list[ChartItem], list[CodeProblem]]:
    if not isinstance(value, ast.List):
        return [], [CodeProblem(line=value.lineno, message=LIST_MESSAGE)]
    items: list[ChartItem] = []
    problems: list[CodeProblem] = []
    for number, element in enumerate(value.elts, start=1):
        item_or_problem = read_item(number, element)
        if isinstance(item_or_problem, CodeProblem):
            problems.append(item_or_problem)
        else:
            items.append(item_or_problem)
    return items, problems


def read_item(number: int, element: ast.expr) -> ChartItem | CodeProblem:
    prefix = f"{CHART_INDICATORS_NAME} item {number}"
    keys = read_string_keys(element)
    if not isinstance(element, ast.Dict) or keys is None:
        message = f"{prefix} must be a dict literal with the keys 'indicator' and 'parameters'."
        return CodeProblem(line=element.lineno, message=message)
    item = ChartItem(number=number, line=element.lineno)
    for key, key_value in zip(keys, element.values, strict=True):
        if key == "indicator":
            if not (isinstance(key_value, ast.Constant) and isinstance(key_value.value, str)):
                return CodeProblem(line=key_value.lineno, message=f"{prefix}: the indicator must be a string literal.")
            item.fields[key] = key_value.value
        elif key == "parameters":
            problem = read_parameters(prefix, item, key_value)
            if problem is not None:
                return problem
            item.fields[key] = item.parameters
        elif key == "formula":
            item.fields[key] = read_formula(key_value)
        else:
            item.fields[key] = None
    return item


def read_formula(value: ast.expr) -> dict[str, object] | None:
    """The `formula` of a custom indicator: a dict literal of literals. None makes a problem of the check."""
    if read_string_keys(value) is None:
        return None
    try:
        return cast("dict[str, object]", ast.literal_eval(value))
    except ValueError:
        # readability-exception: ast.literal_eval reports a value that is not a literal only as an exception.
        return None


def read_string_keys(element: ast.expr) -> list[str] | None:
    """The keys of a dict literal when each key is a string literal, else None."""
    if not isinstance(element, ast.Dict):
        return None
    keys: list[str] = []
    for key in element.keys:
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            return None
        keys.append(key.value)
    return keys


def read_parameters(prefix: str, item: ChartItem, value: ast.expr) -> CodeProblem | None:
    names = read_string_keys(value)
    if not isinstance(value, ast.Dict) or names is None:
        return CodeProblem(
            line=value.lineno, message=f"{prefix}: the parameters must be a dict literal with string keys."
        )
    for name, parameter_value in zip(names, value.values, strict=True):
        literal = read_parameter_value(parameter_value)
        if literal is None:
            message = (
                f"{prefix}: a parameter value must be an int or float literal or the name of a configuration field."
            )
            return CodeProblem(line=parameter_value.lineno, message=message)
        item.parameters[name] = literal
        item.parameter_lines[name] = parameter_value.lineno
    return None


def read_parameter_value(node: ast.expr) -> object | None:
    """A constant (the catalog check reports a wrong one), a negative number, or a `FieldName`. None otherwise."""
    if isinstance(node, ast.Constant) and node.value is not None:
        return FieldName(node.value) if isinstance(node.value, str) else node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
        operand = node.operand.value
        if isinstance(operand, int | float) and not isinstance(operand, bool):
            return -operand
    return None


def check_item(item: ChartItem, field_values: Mapping[str, ParameterNumber]) -> list[CodeProblem]:
    prefix = f"{CHART_INDICATORS_NAME} item {item.number}"
    field_problems = [
        CodeProblem(
            line=item.parameter_lines[name],
            message=f"{prefix}: {value.name!r} is not a configuration field with an int or float default.",
        )
        for name, value in item.parameters.items()
        if isinstance(value, FieldName) and value.name not in field_values
    ]
    if field_problems:
        return field_problems
    reference = {**item.fields}
    if "parameters" in reference:
        reference["parameters"] = resolve_parameters(item, field_values)
    return [
        CodeProblem(line=find_problem_line(item, problem.location), message=f"{prefix}: {problem.message}")
        for problem in check_indicator_reference(reference, has_output=False)
    ]


def resolve_parameters(item: ChartItem, field_values: Mapping[str, ParameterNumber]) -> dict[str, object]:
    return {
        name: field_values[value.name] if isinstance(value, FieldName) else value
        for name, value in item.parameters.items()
    }


def cast_numbers(parameters: Mapping[str, object]) -> dict[str, ParameterNumber]:
    """The parameters of a checked item: the catalog check has made sure that each value is a number."""
    return {name: value for name, value in parameters.items() if isinstance(value, int | float)}


def find_problem_line(item: ChartItem, location: tuple[str, ...]) -> int:
    if location[:1] == PARAMETERS_LOCATION and len(location) == len(PARAMETERS_LOCATION) + 1:
        return item.parameter_lines.get(location[-1], item.line)
    return item.line
