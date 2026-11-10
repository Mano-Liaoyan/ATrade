"""Stored indicator references: the check and the class (docs/architecture/indicator.md section 23.6, #163).

A reference is the JSON object `{"indicator": "rsi", "parameters": {"period": 14}, "output": "value"}`. A reference to a
custom indicator also has `formula` (section 23.10). The check
returns problems with the location in the reference, so a screen (section 24.6) and the rules of the rule builder
(strategy.md section 9.6) can put the location of the condition before it.
"""

from collections.abc import Mapping
from typing import cast

from atrade.indicator.formula_reference import (
    check_formula,
    check_formula_values,
    is_custom_key,
    make_formula_definition,
)
from atrade.indicator.indicator_catalog import (
    INDICATOR_CATALOG,
    CatalogIndicator,
    IndicatorDefinition,
    ParameterValue,
)
from atrade.indicator.indicator_problems import IndicatorProblem, check_output, check_parameters, to_location_text

REFERENCE_FIELDS = ("indicator", "parameters", "output")
CHART_REFERENCE_FIELDS = ("indicator", "parameters")


def check_indicator_reference(reference: object, *, has_output: bool = True) -> list[IndicatorProblem]:
    """Returns the problems of a stored indicator reference. An empty list means the reference is correct.

    With `has_output=False` the reference names a whole indicator with all its outputs, as a bar chart does
    (section 23.9): `output` is then an unknown field.
    """
    if not isinstance(reference, Mapping):
        return [IndicatorProblem((), "An indicator reference must be an object.")]
    fields = cast("Mapping[object, object]", reference)
    key = fields.get("indicator")
    is_custom = is_custom_key(key)
    known_fields = (*(REFERENCE_FIELDS if has_output else CHART_REFERENCE_FIELDS), *(("formula",) if is_custom else ()))
    problems = [
        IndicatorProblem(
            (to_location_text(field),), f"Unknown field {field!r}. Known fields: {', '.join(known_fields)}."
        )
        for field in fields
        if field not in known_fields
    ]
    if is_custom:
        formula_problems = check_formula(fields.get("formula"))
        if formula_problems:
            return [*problems, *formula_problems]
    definition = read_indicator_definition(cast("Mapping[str, object]", fields))
    if definition is None:
        known = ", ".join(INDICATOR_CATALOG)
        return [*problems, IndicatorProblem(("indicator",), f"Unknown indicator {key!r}. Known indicators: {known}.")]
    parameters = fields.get("parameters", {})
    parameter_problems = check_parameters(definition, parameters)
    if is_custom and not parameter_problems:
        formula = cast("Mapping[str, object]", fields["formula"])
        parameter_problems = check_formula_values(formula, cast("Mapping[str, ParameterValue]", parameters))
    return [
        *problems,
        *parameter_problems,
        *(check_output(definition, fields.get("output")) if has_output else []),
    ]


def create_indicator(reference: Mapping[str, object], *, has_output: bool = True) -> CatalogIndicator:
    """Creates the class of a correct reference. Missing parameters get their defaults.

    Raises `ValueError` with the problems when the reference is not correct. `has_output` is the same as in
    `check_indicator_reference`.
    """
    problems = check_indicator_reference(reference, has_output=has_output)
    if problems:
        raise ValueError(" ".join(problem.message for problem in problems))
    definition = find_indicator_definition(reference)
    parameters = cast("Mapping[str, ParameterValue]", reference.get("parameters", {}))
    return definition.indicator_class(**definition.with_defaults(parameters))


def find_indicator_definition(reference: Mapping[str, object]) -> IndicatorDefinition:
    """The definition of a checked reference: a catalog definition, or the definition of its `formula`."""
    definition = read_indicator_definition(reference)
    if definition is None:
        message = f"Unknown indicator {reference.get('indicator')!r}."
        raise ValueError(message)
    return definition


def read_indicator_definition(reference: Mapping[str, object]) -> IndicatorDefinition | None:
    key = reference.get("indicator")
    if is_custom_key(key):
        return make_formula_definition(cast("str", key), cast("Mapping[str, object]", reference["formula"]))
    return INDICATOR_CATALOG.get(key) if isinstance(key, str) else None
