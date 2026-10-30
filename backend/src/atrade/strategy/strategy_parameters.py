"""The parameters of a strategy for a parameter sweep (docs/architecture/backtest.md section 10.11.1).

The reading uses ast.parse only. It does not import or run the user code (docs/architecture/strategy.md 9.3).
"""

import ast
from dataclasses import dataclass
from typing import Literal

from atrade.strategy.code_checks import has_base_class

type ParameterType = Literal["int", "float", "bool"]
# The fields that ATrade sets itself. They are not parameters.
NOT_PARAMETERS = frozenset({"instrument_id", "bar_type", "instrument_ids", "universe"})


@dataclass(frozen=True)
class StrategyParameter:
    name: str
    type: ParameterType
    default: int | float | bool


def read_strategy_parameters(code: str) -> list[StrategyParameter]:
    """The `__init__` arguments of the StrategyConfig subclass that have an `int`, `float`, or `bool` annotation and a
    constant default. Code with a syntax error has no parameters."""
    try:
        module = ast.parse(code)
    except SyntaxError:
        # readability-exception: ast.parse reports a syntax error only as an exception.
        return []
    for node in module.body:
        if isinstance(node, ast.ClassDef) and has_base_class(node, "StrategyConfig"):
            return read_init_parameters(node)
    return []


def read_init_parameters(class_node: ast.ClassDef) -> list[StrategyParameter]:
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            arguments = node.args
            positional = arguments.posonlyargs + arguments.args
            no_defaults: list[ast.expr | None] = [None] * (len(positional) - len(arguments.defaults))
            pairs = list(zip(positional, no_defaults + list(arguments.defaults), strict=True))
            pairs += list(zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True))
            parameters = [to_parameter(argument, default) for argument, default in pairs]
            return [parameter for parameter in parameters if parameter is not None]
    return []


def to_parameter(argument: ast.arg, default: ast.expr | None) -> StrategyParameter | None:
    annotation = argument.annotation
    if argument.arg in NOT_PARAMETERS or not isinstance(annotation, ast.Name) or not isinstance(default, ast.Constant):
        return None
    value = default.value
    if annotation.id == "bool" and isinstance(value, bool):
        return StrategyParameter(name=argument.arg, type="bool", default=value)
    if isinstance(value, bool):
        return None
    if annotation.id == "int" and isinstance(value, int):
        return StrategyParameter(name=argument.arg, type="int", default=value)
    if annotation.id == "float" and isinstance(value, int | float):
        return StrategyParameter(name=argument.arg, type="float", default=float(value))
    return None
