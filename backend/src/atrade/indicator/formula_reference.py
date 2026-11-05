"""The `formula` field of a stored reference to a custom indicator (docs/architecture/indicator.md section 23.10).

The reference holds the text of the expression, so it keeps working after the user changes or deletes the custom
indicator (ADR 0009). This module reads no database.
"""

import re
from collections.abc import Mapping
from functools import partial
from typing import cast

from atrade.indicator.formula_indicator import FormulaIndicator, check_expression, count_formula_bars
from atrade.indicator.indicator_catalog import VALUE, ChartPlacement, IndicatorDefinition, ScreenLookBack
from atrade.indicator.indicator_problems import IndicatorProblem

CUSTOM_KEY_PREFIX = "custom_"
CUSTOM_KEY_FORM = re.compile(rf"{CUSTOM_KEY_PREFIX}[0-9]+")
FORMULA_FIELDS = ("name", "expression", "chart_placement")
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
            ("formula", str(field)), f"Unknown field {field!r}. Known fields: {', '.join(FORMULA_FIELDS)}."
        )
        for field in fields
        if field not in FORMULA_FIELDS
    ]
    expression = fields.get("expression")
    expression_problems = (
        check_expression(expression)
        if isinstance(expression, str)
        else [IndicatorProblem(("expression",), "The expression must be a text.")]
    )
    return [
        *problems,
        *check_name(fields.get("name"), ("formula", "name")),
        *check_chart_placement(fields.get("chart_placement"), ("formula", "chart_placement")),
        *[IndicatorProblem(("formula", *problem.location), problem.message) for problem in expression_problems],
    ]


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
    """The definition of a checked `formula` object. It has no parameters and one output, `value`."""
    name = cast("str", formula["name"])
    expression = cast("str", formula["expression"])
    return IndicatorDefinition(
        key,
        name,
        name,
        cast("ChartPlacement", formula["chart_placement"]),
        (),
        VALUE,
        partial(FormulaIndicator, expression),
        ScreenLookBack((), extra_bars=count_formula_bars(expression)),
        "",
        expression=expression,
    )
