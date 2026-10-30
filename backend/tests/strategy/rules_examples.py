"""Builders of rule builder rules as JSON (docs/architecture/strategy.md section 9.8.2) for the tests."""

from typing import Any

type Json = dict[str, Any]

PRICES = ("close", "open", "high", "low")
COMPARISONS = ("above", "below", "at_or_above", "at_or_below", "crosses_above", "crosses_below")
FIXED_10_SHARES: Json = {"type": "fixed_shares", "shares": 10}


def price(name: str = "close") -> Json:
    return {"type": "price", "price": name}


def number(value: float) -> Json:
    return {"type": "number", "value": value}


def indicator(key: str, output: str | None = None, **parameters: float) -> Json:
    operand: Json = {"type": "indicator", "indicator": key, "parameters": parameters}
    if output is not None:
        operand["output"] = output
    return operand


def condition(left: Json, comparison: str, right: Json) -> Json:
    return {"type": "condition", "left": left, "comparison": comparison, "right": right}


def group(match: str, *items: Json) -> Json:
    return {"type": "group", "match": match, "items": list(items)}


def make_rules(entry: Json | None = None, *, exits: Json | None = None, position_size: Json = FIXED_10_SHARES) -> Json:
    return {
        "format_version": 1,
        "settings": {"position_size": position_size},
        "entry": group("all_of") if entry is None else entry,
        "exits": {} if exits is None else exits,
    }


def make_full_rules() -> Json:
    """Rules with each kind of left side, multi-line output, comparison, right side, nested group, and exit item."""
    lines = [indicator("macd", output) for output in ("value", "signal", "histogram")] + [
        indicator(key, output)
        for key in ("bollinger_bands", "donchian_channel")
        for output in ("upper", "middle", "lower")
    ]
    single_line = [
        indicator(key)
        for key in (
            "sma",
            "ema",
            "momentum_12_1",
            "distance_to_52_week_high",
            "realized_volatility",
            "atr",
            "average_trading_value",
            "rsi",
        )
    ]
    lefts = [price(name) for name in PRICES] + single_line + lines
    rights = [number(1.5), number(2), price("open"), indicator("sma", period=10)]
    conditions = [
        condition(left, COMPARISONS[index % len(COMPARISONS)], rights[index % len(rights)])
        for index, left in enumerate(lefts)
    ]
    return make_rules(
        group("all_of", *conditions[:10], group("any_of", *conditions[10:])),
        exits={
            "stop_loss_percent": 5,
            "take_profit_percent": 10.5,
            "exit_after_bars": 3,
            "exit_when_entry_is_false": True,
            "exit_group": group("any_of", condition(price("low"), "crosses_below", indicator("sma", period=10))),
        },
        position_size={"type": "percent_of_equity", "percent": 50},
    )
