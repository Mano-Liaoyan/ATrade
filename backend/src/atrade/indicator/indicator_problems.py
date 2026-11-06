"""The check of the parameters and the output of an indicator (docs/architecture/indicator.md section 23.6).

A stored reference and a call in a formula expression use the same check.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from atrade.indicator.indicator_catalog import IndicatorDefinition, IndicatorParameter, ParameterValue


@dataclass(frozen=True)
class IndicatorProblem:
    """`location` is the path in the reference, for example `("parameters", "period")`. `()` is the reference."""

    location: tuple[str, ...]
    message: str


def to_location_text(field: object) -> str:
    """A field name from a request can hold a lone surrogate. The response must be able to encode the location."""
    return str(field).encode("utf-8", "backslashreplace").decode("utf-8")


def check_parameters(definition: IndicatorDefinition, parameters: object) -> list[IndicatorProblem]:
    if not isinstance(parameters, Mapping):
        return [IndicatorProblem(("parameters",), "The parameters must be an object.")]
    values = cast("Mapping[object, object]", parameters)
    known = {parameter.name: parameter for parameter in definition.parameters}
    problems: list[IndicatorProblem] = []
    for name, value in values.items():
        parameter = known.get(name) if isinstance(name, str) else None
        if parameter is None:
            message = f"Unknown parameter {name!r} of {definition.name}. Known parameters: {', '.join(known)}."
            problems.append(IndicatorProblem(("parameters", to_location_text(name)), message))
            continue
        message = check_parameter_value(parameter, value)
        if message is not None:
            problems.append(IndicatorProblem(("parameters", parameter.name), message))
    if problems:
        return problems
    return check_orders(definition, cast("Mapping[str, ParameterValue]", values))


def check_parameter_value(parameter: IndicatorParameter, value: object) -> str | None:
    is_number = isinstance(value, int | float) and not isinstance(value, bool)
    if parameter.value_type is int and not (is_number and isinstance(value, int)):
        return f"The {parameter.name} must be an integer, not {value!r}."
    if not is_number:
        return f"The {parameter.name} must be a number, not {value!r}."
    number = cast("ParameterValue", value)
    if not parameter.minimum <= number <= parameter.maximum:
        return f"The {parameter.name} must be from {parameter.minimum} to {parameter.maximum}, not {number}."
    return None


def check_orders(definition: IndicatorDefinition, parameters: Mapping[str, ParameterValue]) -> list[IndicatorProblem]:
    values = definition.with_defaults(parameters)
    return [
        IndicatorProblem(
            ("parameters", order.smaller),
            f"The {order.smaller} must be less than the {order.larger} ({values[order.larger]}), "
            f"not {values[order.smaller]}.",
        )
        for order in definition.orders
        if values[order.smaller] >= values[order.larger]
    ]


def check_output(definition: IndicatorDefinition, output: object) -> list[IndicatorProblem]:
    outputs = ", ".join(definition.outputs)
    if output is None:
        if len(definition.outputs) == 1:
            return []
        return [IndicatorProblem(("output",), f"{definition.name} needs an output. Known outputs: {outputs}.")]
    if output not in definition.outputs:
        message = f"Unknown output {output!r} of {definition.name}. Known outputs: {outputs}."
        return [IndicatorProblem(("output",), message)]
    return []
