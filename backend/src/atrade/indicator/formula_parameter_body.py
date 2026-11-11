"""The JSON form of one parameter of a custom indicator (docs/architecture/indicator.md section 23.10.1).

The routes and the rules of the rule builder use this model, so the API has one type for it. `check_formula_parameters`
checks the values, so a wrong value is a problem with its location.
"""

from pydantic import BaseModel, StrictFloat, StrictInt


class FormulaParameterBody(BaseModel):
    """An expression uses `name` as a number. Each reference holds its own value (ADR 0009)."""

    name: str
    # The name that the UI shows.
    label: str
    # `int` or `float`.
    value_type: str
    default: StrictInt | StrictFloat
    minimum: StrictInt | StrictFloat
    maximum: StrictInt | StrictFloat
    description: str = ""
