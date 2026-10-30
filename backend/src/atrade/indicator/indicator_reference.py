"""Stored indicator references: the check and the class (docs/architecture/indicator.md section 23.6, #163).

A reference is the JSON object `{"indicator": "rsi", "parameters": {"period": 14}, "output": "value"}`. The check
returns problems with the location in the reference, so a screen (section 24.6) and the rules of the rule builder
(strategy.md section 9.6) can put the location of the condition before it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from atrade.indicator.indicator_catalog import (
    INDICATOR_CATALOG,
    CatalogIndicator,
    IndicatorDefinition,
    IndicatorParameter,
    ParameterValue,
)

REFERENCE_FIELDS = ("indicator", "parameters", "output")


@dataclass(frozen=True)
class IndicatorProblem:
    """`location` is the path in the reference, for example `("parameters", "period")`. `()` is the reference."""

    location: tuple[str, ...]
    message: str


def check_indicator_reference(reference: object) -> list[IndicatorProblem]:
    """Returns the problems of a stored indicator reference. An empty list means the reference is correct."""
    if not isinstance(reference, Mapping):
        return [IndicatorProblem((), "An indicator reference must be an object.")]
    fields = cast("Mapping[object, object]", reference)
    problems = [
        IndicatorProblem((str(field),), f"Unknown field {field!r}. Known fields: {', '.join(REFERENCE_FIELDS)}.")
        for field in fields
        if field not in REFERENCE_FIELDS
    ]
    key = fields.get("indicator")
    definition = INDICATOR_CATALOG.get(key) if isinstance(key, str) else None
    if definition is None:
        known = ", ".join(INDICATOR_CATALOG)
        return [*problems, IndicatorProblem(("indicator",), f"Unknown indicator {key!r}. Known indicators: {known}.")]
    return [
        *problems,
        *check_parameters(definition, fields.get("parameters", {})),
        *check_output(definition, fields.get("output")),
    ]


def create_indicator(reference: Mapping[str, object]) -> CatalogIndicator:
    """Creates the class of a correct reference. Missing parameters get their defaults.

    Raises `ValueError` with the problems when the reference is not correct.
    """
    problems = check_indicator_reference(reference)
    if problems:
        raise ValueError(" ".join(problem.message for problem in problems))
    definition = INDICATOR_CATALOG[cast("str", reference["indicator"])]
    parameters = cast("Mapping[str, ParameterValue]", reference.get("parameters", {}))
    return definition.indicator_class(**definition.with_defaults(parameters))


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
            problems.append(IndicatorProblem(("parameters", str(name)), message))
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
