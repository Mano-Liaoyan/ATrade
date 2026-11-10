"""The `formula` field of a stored reference to a custom indicator (docs/architecture/indicator.md section 23.10).

The reference holds the text of the expression, so it keeps working after the user changes or deletes the custom
indicator (ADR 0009). This module reads no database.
"""

import re
from collections.abc import Mapping
from typing import cast

from atrade.indicator.formula_indicator import (
    BAR_FIELDS,
    MAX_PARAMETER_SIZE,
    SCALAR_FUNCTIONS,
    WINDOW_FUNCTIONS,
    FormulaIndicator,
    check_expression,
    count_formula_bars,
    fix_parameters,
)
from atrade.indicator.indicator_catalog import (
    INDICATOR_CATALOG,
    VALUE,
    CatalogIndicator,
    ChartPlacement,
    IndicatorDefinition,
    IndicatorParameter,
    ParameterValue,
    ParameterValues,
    ScreenLookBack,
)
from atrade.indicator.indicator_problems import IndicatorProblem, to_location_text

CUSTOM_KEY_PREFIX = "custom_"
CUSTOM_KEY_FORM = re.compile(rf"{CUSTOM_KEY_PREFIX}[0-9]+")
FORMULA_FIELDS = ("name", "expression", "chart_placement", "parameters")
PARAMETER_FIELDS = ("name", "label", "value_type", "default", "minimum", "maximum", "description")
VALUE_TYPES: Mapping[object, type[int | float]] = {"int": int, "float": float}
PARAMETER_NAME_FORM = re.compile("[a-z][a-z0-9_]*")
MAX_PARAMETER_COUNT = 10
MAX_PARAMETER_NAME_LENGTH = 40
MAX_PARAMETER_DESCRIPTION_LENGTH = 200
type Location = tuple[str, ...]
CHART_PLACEMENTS = ("price", "own")
MAX_NAME_LENGTH = 60
UNSTORABLE_CHARACTER = re.compile("[\x00\ud800-\udfff]")


def is_custom_key(key: object) -> bool:
    return isinstance(key, str) and CUSTOM_KEY_FORM.fullmatch(key) is not None


def has_unstorable_character(text: str) -> bool:
    """PostgreSQL text has no NUL, and UTF-8 has no lone surrogate."""
    return UNSTORABLE_CHARACTER.search(text) is not None


def check_formula(formula: object) -> list[IndicatorProblem]:
    """Returns the problems of a `formula` object. Each location starts with `formula`."""
    if not isinstance(formula, Mapping):
        return [IndicatorProblem(("formula",), "A custom indicator needs a formula object.")]
    fields = cast("Mapping[object, object]", formula)
    problems = [
        IndicatorProblem(
            ("formula", to_location_text(field)), f"Unknown field {field!r}. Known fields: {', '.join(FORMULA_FIELDS)}."
        )
        for field in fields
        if field not in FORMULA_FIELDS
    ]
    expression_problems = check_expression_with_parameters(fields.get("expression"), fields.get("parameters", []))
    return [
        *problems,
        *check_name(fields.get("name"), ("formula", "name")),
        *check_chart_placement(fields.get("chart_placement"), ("formula", "chart_placement")),
        *[IndicatorProblem(("formula", *problem.location), problem.message) for problem in expression_problems],
    ]


def check_expression_with_parameters(expression: object, parameters: object) -> list[IndicatorProblem]:
    """The problems of the parameter list, at `parameters`. Without them, the problem of the expression, at
    `expression`: the check of the expression needs correct parameters."""
    if not isinstance(expression, str):
        return [IndicatorProblem(("expression",), "The expression must be a text.")]
    return check_formula_parameters(parameters) or check_expression(expression, read_formula_parameters(parameters))


def check_formula_parameters(parameters: object) -> list[IndicatorProblem]:
    """Returns the problems of the parameter list of a custom indicator. Each location starts with `parameters`."""
    if not isinstance(parameters, list):
        return [IndicatorProblem(("parameters",), "The parameters must be a list.")]
    items = cast("list[object]", parameters)
    if len(items) > MAX_PARAMETER_COUNT:
        message = f"A custom indicator has at most {MAX_PARAMETER_COUNT} parameters, not {len(items)}."
        return [IndicatorProblem(("parameters",), message)]
    problems: list[IndicatorProblem] = []
    names: set[object] = set()
    for index, item in enumerate(items):
        location = ("parameters", str(index))
        item_problems = check_formula_parameter(item, location)
        name = cast("Mapping[object, object]", item).get("name") if isinstance(item, Mapping) else None
        if not item_problems and name in names:
            item_problems = [IndicatorProblem((*location, "name"), f"The parameter {name!r} is in the list 2 times.")]
        names.add(name)
        problems.extend(item_problems)
    return problems


def check_formula_parameter(parameter: object, location: Location) -> list[IndicatorProblem]:
    if not isinstance(parameter, Mapping):
        return [IndicatorProblem(location, "A parameter must be an object.")]
    fields = cast("Mapping[object, object]", parameter)
    known = ", ".join(PARAMETER_FIELDS)
    return [
        *[
            IndicatorProblem((*location, to_location_text(field)), f"Unknown field {field!r}. Known fields: {known}.")
            for field in fields
            if field not in PARAMETER_FIELDS
        ],
        *check_parameter_name(fields.get("name"), (*location, "name")),
        *check_parameter_text(fields.get("label"), (*location, "label"), "label", 1, MAX_NAME_LENGTH),
        *check_parameter_text(
            fields.get("description", ""),
            (*location, "description"),
            "description",
            0,
            MAX_PARAMETER_DESCRIPTION_LENGTH,
        ),
        *check_parameter_range(fields, location),
    ]


def check_parameter_name(name: object, location: Location) -> list[IndicatorProblem]:
    """An expression uses the name as a number, so the name is a lower-case Python name that the parser does not
    have."""
    is_name = isinstance(name, str) and PARAMETER_NAME_FORM.fullmatch(name) is not None
    if not is_name or len(cast("str", name)) > MAX_PARAMETER_NAME_LENGTH:
        message = (
            f"The name of a parameter has 1 to {MAX_PARAMETER_NAME_LENGTH} characters: a lower-case letter, then "
            "lower-case letters, digits, and `_`, for example `lookback_days`."
        )
        return [IndicatorProblem(location, message)]
    if name in BAR_FIELDS or name in WINDOW_FUNCTIONS or name in SCALAR_FUNCTIONS or name in INDICATOR_CATALOG:
        message = f"The name {name!r} is a bar field or a function of an expression. Use another name."
        return [IndicatorProblem(location, message)]
    return []


def check_parameter_text(
    text: object, location: Location, field: str, minimum: int, maximum: int
) -> list[IndicatorProblem]:
    if not isinstance(text, str) or not minimum <= len(text.strip()) <= maximum:
        return [IndicatorProblem(location, f"The {field} must have {minimum} to {maximum} characters.")]
    if has_unstorable_character(text):
        return [IndicatorProblem(location, f"The {field} has a character that is not allowed.")]
    return []


def check_parameter_range(fields: Mapping[object, object], location: Location) -> list[IndicatorProblem]:
    value_type = VALUE_TYPES.get(fields.get("value_type"))
    if value_type is None:
        return [IndicatorProblem((*location, "value_type"), "The value type must be `int` or `float`.")]
    problems: list[IndicatorProblem] = []
    for field in ("minimum", "default", "maximum"):
        value = fields.get(field)
        is_number = type(value) in {int, float} and abs(cast("ParameterValue", value)) <= MAX_PARAMETER_SIZE
        if not is_number or (value_type is int and type(value) is not int):
            kind = "an integer" if value_type is int else "a number"
            message = f"The {field} must be {kind} from -1e15 to 1e15, not {value!r}."
            problems.append(IndicatorProblem((*location, field), message))
    if problems:
        return problems
    minimum, default, maximum = (cast("ParameterValue", fields[field]) for field in ("minimum", "default", "maximum"))
    if not minimum <= default <= maximum:
        message = f"The default must be from the minimum ({minimum}) to the maximum ({maximum}), not {default}."
        return [IndicatorProblem((*location, "default"), message)]
    return []


def read_formula_parameters(parameters: object) -> tuple[IndicatorParameter, ...]:
    """The parameters of a checked parameter list."""
    return tuple(
        IndicatorParameter(
            cast("str", item["name"]),
            VALUE_TYPES[item["value_type"]],
            cast("ParameterValue", item["default"]),
            cast("ParameterValue", item["minimum"]),
            cast("ParameterValue", item["maximum"]),
            label=cast("str", item["label"]),
            description=cast("str", item.get("description", "")),
        )
        for item in cast("list[Mapping[str, object]]", parameters)
    )


def check_formula_values(formula: Mapping[str, object], values: ParameterValues) -> list[IndicatorProblem]:
    """The problem of a checked formula with these parameter values, at `parameters`. The ranges of the parameters
    cannot give it: for example `macd(fast, slow)` needs `fast` less than `slow`."""
    parameters = read_formula_parameters(formula.get("parameters", []))
    defaults = {parameter.name: parameter.default for parameter in parameters}
    problems = check_expression(cast("str", formula["expression"]), fix_parameters({**defaults, **values}))
    return [IndicatorProblem(("parameters",), problem.message) for problem in problems]


def check_name(name: object, location: tuple[str, ...]) -> list[IndicatorProblem]:
    """The UI name of a built-in indicator has parentheses, so a custom name without them cannot be equal to it."""
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= MAX_NAME_LENGTH:
        return [IndicatorProblem(location, f"The name must have 1 to {MAX_NAME_LENGTH} characters.")]
    if has_unstorable_character(name):
        return [IndicatorProblem(location, "The name has a character that is not allowed.")]
    if "(" in name or ")" in name:
        return [IndicatorProblem(location, "The name must not have parentheses.")]
    return []


def check_chart_placement(placement: object, location: tuple[str, ...]) -> list[IndicatorProblem]:
    if placement in CHART_PLACEMENTS:
        return []
    known = ", ".join(CHART_PLACEMENTS)
    return [IndicatorProblem(location, f"Unknown chart placement {placement!r}. Known chart placements: {known}.")]


def make_formula_definition(key: str, formula: Mapping[str, object]) -> IndicatorDefinition:
    """The definition of a checked `formula` object. It has the parameters of the formula and one output, `value`."""
    name = cast("str", formula["name"])
    expression = cast("str", formula["expression"])

    def create(**values: ParameterValue) -> CatalogIndicator:
        return FormulaIndicator(expression, values)

    def count_look_back_bars(values: ParameterValues) -> int:
        return count_formula_bars(expression, tuple(values.items()))

    return IndicatorDefinition(
        key,
        name,
        name,
        cast("ChartPlacement", formula["chart_placement"]),
        read_formula_parameters(formula.get("parameters", [])),
        VALUE,
        create,
        ScreenLookBack(()),
        "",
        expression=expression,
        count_look_back_bars=count_look_back_bars,
    )
