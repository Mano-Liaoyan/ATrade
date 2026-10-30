"""The check of a screen before a save or a run (docs/architecture/screen.md sections 24.4.1 and 24.6).

The check reads the JSON as it comes in, so each problem can give its location in the request, for example
`("definition", "indicator_conditions", 0, "indicator", "parameters", "period")`.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import cast

from atrade.indicator import check_indicator_reference

type Location = tuple[str | int, ...]

MARKETS = ("US", "HK")
MAX_NAME_LENGTH = 100
START_INSTRUMENTS = {
    "US": ("quarter_universe", "all_with_daily_bars", "watchlist"),
    "HK": ("hk_instrument_list", "watchlist"),
}
OPERATORS = ("<", "<=", ">", ">=")
NUMBER_FILTER_FIELDS = ("last_price", "average_trading_value_20")
FILTER_FIELDS = ("still_trading", *NUMBER_FILTER_FIELDS, "exchange")
LINE_INDICATORS = {"sma": "value", "ema": "value", "donchian_channel": "upper"}
SIDES = ("above", "below")
RANK_ENDS = ("top", "bottom")
MAX_RANK_PERCENT = 100
DIRECTIONS = ("ascending", "descending")
# A screen result has at most 500 rows (section 24.4).
MAX_KEEP_FIRST = 500


@dataclass(frozen=True)
class ScreenProblem:
    location: Location
    message: str


def check_screen(*, name: str, market: str, definition: object) -> list[ScreenProblem]:
    """Returns the problems of a screen. An empty list means the screen is correct."""
    problems: list[ScreenProblem] = []
    if not 1 <= len(name) <= MAX_NAME_LENGTH:
        problems.append(
            ScreenProblem(("name",), f"The name must have 1 to {MAX_NAME_LENGTH} characters, not {len(name)}.")
        )
    if market not in MARKETS:
        problems.append(ScreenProblem(("market",), f"Unknown market {market!r}. Known markets: {', '.join(MARKETS)}."))
    return [*problems, *check_definition(market, definition, ("definition",))]


def check_definition(market: str, definition: object, location: Location) -> list[ScreenProblem]:
    problems, fields = check_object(
        definition, location, required=("start", "filters", "indicator_conditions", "order"), optional=()
    )
    if fields is None:
        return problems
    # check_object gives the problem of a missing key. A key with the value null is a problem of its value.
    if market in MARKETS and "start" in fields:
        problems += check_start(market, fields["start"], (*location, "start"))
    if "filters" in fields:
        problems += check_list(fields["filters"], (*location, "filters"), check_filter)
    if "indicator_conditions" in fields:
        problems += check_list(fields["indicator_conditions"], (*location, "indicator_conditions"), check_condition)
    if "order" in fields:
        problems += check_order(fields["order"], (*location, "order"))
    return problems


def check_start(market: str, start: object, location: Location) -> list[ScreenProblem]:
    known = START_INSTRUMENTS[market]
    if start in known:
        return []
    message = (
        f"The start instruments {start!r} do not belong to the market {market}. "
        f"Known start instruments: {', '.join(known)}."
    )
    return [ScreenProblem(location, message)]


def read_key(value: object, key: str) -> object:
    """The value of the key when the value is an object, else None."""
    if not isinstance(value, Mapping):
        return None
    return cast("Mapping[str, object]", value).get(key)


def check_filter(item: object, location: Location) -> list[ScreenProblem]:
    field = read_key(item, "field")
    if field == "still_trading":
        return check_object(item, location, required=("field",), optional=())[0]
    if field in NUMBER_FILTER_FIELDS:
        problems, fields = check_object(item, location, required=("field", "operator", "value"), optional=())
        return problems + check_comparison(fields or {}, location)
    if field == "exchange":
        problems, fields = check_object(item, location, required=("field", "values"), optional=())
        if fields is None or "values" not in fields:
            return problems
        return problems + check_exchanges(fields["values"], (*location, "values"))
    if not isinstance(item, Mapping):
        return check_object(item, location, required=("field",), optional=())[0]
    return [ScreenProblem((*location, "field"), unknown_message("field", field, FILTER_FIELDS))]


def check_condition(item: object, location: Location) -> list[ScreenProblem]:
    kind = read_key(item, "kind")
    if kind == "compare":
        problems, fields = check_object(item, location, required=("kind", "indicator", "operator", "value"))
        return problems + check_indicator(fields, location) + check_comparison(fields or {}, location)
    if kind == "close_versus_line":
        problems, fields = check_object(item, location, required=("kind", "indicator", "side"))
        problems += check_choice(fields, location, "side", SIDES)
        return problems + check_indicator(fields, location) + check_line(fields, location)
    if kind == "rank":
        problems, fields = check_object(item, location, required=("kind", "indicator", "end", "percent"))
        problems += check_choice(fields, location, "end", RANK_ENDS)
        return problems + check_indicator(fields, location) + check_percent(fields, location)
    if not isinstance(item, Mapping):
        return check_object(item, location, required=("kind",))[0]
    known = ("compare", "close_versus_line", "rank")
    return [ScreenProblem((*location, "kind"), unknown_message("kind", kind, known))]


def check_order(order: object, location: Location) -> list[ScreenProblem]:
    problems, fields = check_object(order, location, required=("indicator", "direction"), optional=("keep_first",))
    if fields is None:
        return problems
    problems += check_indicator(fields, location) + check_choice(fields, location, "direction", DIRECTIONS)
    keep_first = fields.get("keep_first")
    if "keep_first" in fields and not is_integer_in(keep_first, 1, MAX_KEEP_FIRST):
        message = f"The keep_first must be an integer from 1 to {MAX_KEEP_FIRST}, not {keep_first!r}."
        problems.append(ScreenProblem((*location, "keep_first"), message))
    return problems


def check_indicator(fields: Mapping[str, object] | None, location: Location) -> list[ScreenProblem]:
    if fields is None or "indicator" not in fields:
        return []
    return [
        ScreenProblem((*location, "indicator", *problem.location), problem.message)
        for problem in check_indicator_reference(fields["indicator"])
    ]


def check_line(fields: Mapping[str, object] | None, location: Location) -> list[ScreenProblem]:
    """A line is SMA, EMA, or the upper line of the Donchian channel (section 24.3)."""
    reference = (fields or {}).get("indicator")
    key = read_key(reference, "indicator")
    output = read_key(reference, "output") or "value"
    # check_indicator gives the problem of a reference that is not an object or has no indicator.
    if key is None or (isinstance(key, str) and output == LINE_INDICATORS.get(key)):
        return []
    lines = "sma value, ema value, donchian_channel upper"
    message = f"The line must be one of: {lines}. Not {key!r} {output!r}."
    return [ScreenProblem((*location, "indicator"), message)]


def check_percent(fields: Mapping[str, object] | None, location: Location) -> list[ScreenProblem]:
    if fields is None or "percent" not in fields or is_integer_in(fields["percent"], 1, MAX_RANK_PERCENT):
        return []
    message = f"The percent must be an integer from 1 to {MAX_RANK_PERCENT}, not {fields['percent']!r}."
    return [ScreenProblem((*location, "percent"), message)]


def check_comparison(fields: Mapping[str, object], location: Location) -> list[ScreenProblem]:
    problems = check_choice(fields, location, "operator", OPERATORS)
    if "value" in fields and not is_decimal_string(fields["value"]):
        message = f'The value must be a decimal string, for example "30", not {fields["value"]!r}.'
        problems.append(ScreenProblem((*location, "value"), message))
    return problems


def check_exchanges(values: object, location: Location) -> list[ScreenProblem]:
    if not is_list(values) or not values:
        return [ScreenProblem(location, "The values must be a list of 1 or more exchanges.")]
    return [
        ScreenProblem((*location, index), f"An exchange must be a text, not {value!r}.")
        for index, value in enumerate(cast("Sequence[object]", values))
        if not isinstance(value, str) or not value
    ]


def check_choice(
    fields: Mapping[str, object] | None, location: Location, key: str, known: tuple[str, ...]
) -> list[ScreenProblem]:
    if fields is None or key not in fields or fields[key] in known:
        return []
    return [ScreenProblem((*location, key), unknown_message(key, fields[key], known))]


def check_list(
    items: object, location: Location, check_item: Callable[[object, Location], list[ScreenProblem]]
) -> list[ScreenProblem]:
    if not is_list(items):
        return [ScreenProblem(location, "This must be a list.")]
    return [
        problem
        for index, item in enumerate(cast("Sequence[object]", items))
        for problem in check_item(item, (*location, index))
    ]


def check_object(
    value: object, location: Location, *, required: tuple[str, ...], optional: tuple[str, ...] = ()
) -> tuple[list[ScreenProblem], Mapping[str, object] | None]:
    """Checks that the value is an object with the required keys and no unknown key."""
    if not isinstance(value, Mapping):
        return [ScreenProblem(location, "This must be an object.")], None
    fields = cast("Mapping[str, object]", value)
    known = (*required, *optional)
    problems = [
        ScreenProblem((*location, str(key)), unknown_message("key", key, known)) for key in fields if key not in known
    ]
    problems += [
        ScreenProblem((*location, key), f"The key {key!r} is missing.") for key in required if key not in fields
    ]
    return problems, fields


def unknown_message(what: str, value: object, known: Sequence[str]) -> str:
    return f"Unknown {what} {value!r}. Known: {', '.join(known)}."


def is_list(value: object) -> bool:
    return isinstance(value, list)


def is_integer_in(value: object, minimum: int, maximum: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= maximum


def is_decimal_string(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return Decimal(value).is_finite()
    except InvalidOperation:
        return False
