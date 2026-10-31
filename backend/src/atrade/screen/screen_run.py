"""The 2 steps of a screen run (docs/architecture/screen.md sections 24.3 and 24.5).

Step 1 applies the filters to the daily bar summary. Step 2 reads the daily bars of all instruments that step 1
keeps in one read, gives each indicator only its look-back bars (section 23.4), and applies the indicator
conditions. A check with `check_screen` comes first, so the definition here is correct.
"""

import bisect
import math
import operator
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, cast

from atrade.foundation.bar import Bar
from atrade.foundation.instrument import Instrument
from atrade.indicator import INDICATOR_CATALOG, create_indicator
from atrade.market_data import DailyBarSummary

type DailyBarsReader = Callable[[list[Instrument], datetime, int], Awaitable[dict[Instrument, list[Bar]]]]
type Definition = Mapping[str, Any]

# A screen result has at most 500 rows (section 24.4). More passing instruments: the first 500 of the order.
MAX_RESULT_ROWS = 500
# "Still trading": the last daily bar is at most 7 calendar days older than the newest last daily bar of the start
# instruments (the daily bars date). 7 days cover a long holiday weekend and 1 missed daily bar update.
STILL_TRADING_DAYS = 7
NO_DAILY_BARS = "No daily bars"
AVERAGE_TRADING_VALUE_NAME = "Avg trading value (20)"
COMPARISONS: Mapping[str, Callable[[Any, Any], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


@dataclass(frozen=True)
class ScreenRow:
    instrument: Instrument
    last_price: Decimal
    average_trading_value_20: float | None
    # The value of each indicator of a condition or of the order, by its name, for example "RSI(14)".
    indicator_values: dict[str, float]
    # The percentile of each rank condition, by the name of its indicator.
    percentiles: dict[str, float]


@dataclass(frozen=True)
class ScreenExclusion:
    instrument: Instrument
    # "<location>: <condition>", "No value: <indicator>", or "No daily bars".
    reason: str


@dataclass(frozen=True)
class ScreenOutcome:
    daily_bars_date: date | None
    start_count: int
    after_filters_count: int
    after_indicator_conditions_count: int
    rows: list[ScreenRow]
    exclusions: list[ScreenExclusion]

    @property
    def result_count(self) -> int:
        return len(self.rows)


@dataclass(frozen=True)
class IndicatorColumn:
    """One indicator of a condition or of the order."""

    name: str
    reference: Mapping[str, object]
    output: str
    look_back_bars: int


def name_indicator(reference: Mapping[str, object]) -> str:
    """For example "RSI(14)", or "Donchian channel(20) upper" for an output that is not `value`."""
    definition = INDICATOR_CATALOG[cast("str", reference["indicator"])]
    name = definition.display_name(cast("Mapping[str, int | float]", reference.get("parameters", {})))
    output = cast("str", reference.get("output", "value"))
    return name if output == "value" else f"{name} {output}"


def make_column(reference: Mapping[str, object]) -> IndicatorColumn:
    definition = INDICATOR_CATALOG[cast("str", reference["indicator"])]
    parameters = cast("Mapping[str, int | float]", reference.get("parameters", {}))
    return IndicatorColumn(
        name=name_indicator(reference),
        reference=reference,
        output=cast("str", reference.get("output", "value")),
        look_back_bars=definition.screen_look_back_bars(parameters),
    )


def list_columns(definition: Definition) -> list[IndicatorColumn]:
    """The indicators of the conditions and of the order, each one time, in the order of the definition."""
    references = [
        *(condition["indicator"] for condition in definition["indicator_conditions"]),
        definition["order"]["indicator"],
    ]
    columns = [make_column(cast("Mapping[str, object]", reference)) for reference in references]
    return list({column.name: column for column in reversed(columns)}.values())[::-1]


def describe_filter(item: Mapping[str, Any]) -> str:
    field = item["field"]
    if field == "still_trading":
        return "Still trading"
    if field == "exchange":
        return f"Exchange in {', '.join(item['values'])}"
    name = "Close" if field == "last_price" else AVERAGE_TRADING_VALUE_NAME
    return f"{name} {item['operator']} {item['value']}"


def describe_condition(condition: Mapping[str, Any]) -> str:
    name = name_indicator(condition["indicator"])
    if condition["kind"] == "compare":
        return f"{name} {condition['operator']} {condition['value']}"
    if condition["kind"] == "close_versus_line":
        return f"Close {condition['side']} {name}"
    return f"{name} {condition['end']} {condition['percent']}%"


def check_filter(item: Mapping[str, Any], summary: DailyBarSummary, daily_bars_date: date) -> bool | None:
    """True when the filter is true, None when the summary has no value."""
    field = item["field"]
    if field == "still_trading":
        return summary.last_day_start_utc.date() >= daily_bars_date - timedelta(days=STILL_TRADING_DAYS)
    if field == "exchange":
        return summary.instrument.exchange in item["values"]
    if field == "last_price":
        return COMPARISONS[item["operator"]](summary.last_close, Decimal(item["value"]))
    if summary.average_trading_value_20 is None:
        return None
    return COMPARISONS[item["operator"]](summary.average_trading_value_20, float(item["value"]))


def find_filter_reason(
    filters: Sequence[Mapping[str, Any]], summary: DailyBarSummary, daily_bars_date: date
) -> str | None:
    """The reason of the first filter that is not true, or None when all filters are true."""
    for index, item in enumerate(filters):
        is_true = check_filter(item, summary, daily_bars_date)
        if is_true is None:
            return f"No value: {AVERAGE_TRADING_VALUE_NAME}"
        if not is_true:
            return f"filters[{index}]: {describe_filter(item)}"
    return None


def calculate_value(column: IndicatorColumn, bars: list[Bar]) -> float | None:
    indicator = create_indicator(column.reference)
    for bar in bars[-column.look_back_bars :]:
        indicator.update(bar)
    value = cast("float | None", getattr(indicator, column.output))
    return value if value is not None and math.isfinite(value) else None


def calculate_percentiles(values: list[float]) -> tuple[list[float], list[float]]:
    """For each value: 100 x the share of the values that are lower or equal (the "Percentile" column), and 100 x the
    share of the values that are lower. Equal values get the same percentiles."""
    ordered = sorted(values)
    count = len(values)
    at_or_below = [100.0 * bisect.bisect_right(ordered, value) / count for value in values]
    below = [100.0 * bisect.bisect_left(ordered, value) / count for value in values]
    return at_or_below, below


@dataclass(frozen=True)
class Candidate:
    """An instrument that step 1 keeps and that has a value for each indicator."""

    summary: DailyBarSummary
    last_close: Decimal
    values: dict[str, float]


def is_in_rank(condition: Mapping[str, Any], at_or_below: float, below: float) -> bool:
    """Top N%: fewer than N% of the values are higher. Bottom N%: fewer than N% of the values are lower."""
    if condition["end"] == "top":
        return at_or_below > 100 - condition["percent"]
    return below < condition["percent"]


def is_condition_true(condition: Mapping[str, Any], candidate: Candidate, percentiles: tuple[float, float]) -> bool:
    value = candidate.values[name_indicator(condition["indicator"])]
    if condition["kind"] == "compare":
        return COMPARISONS[condition["operator"]](value, float(condition["value"]))
    if condition["kind"] == "close_versus_line":
        close = float(candidate.last_close)
        return close > value if condition["side"] == "above" else close < value
    return is_in_rank(condition, *percentiles)


def find_daily_bars_date(summaries: list[DailyBarSummary]) -> date | None:
    """The date of the newest last daily bar of the start instruments."""
    return max((summary.last_day_start_utc.date() for summary in summaries), default=None)


def apply_filters(
    filters: Sequence[Mapping[str, Any]], summaries: dict[Instrument, DailyBarSummary], daily_bars_date: date | None
) -> tuple[list[DailyBarSummary], list[ScreenExclusion]]:
    """Step 1. The kept summaries in the order of the start instruments, and the excluded instruments."""
    kept: list[DailyBarSummary] = []
    exclusions: list[ScreenExclusion] = []
    for instrument, summary in summaries.items():
        reason = find_filter_reason(filters, summary, daily_bars_date) if daily_bars_date else NO_DAILY_BARS
        if reason is None:
            kept.append(summary)
        else:
            exclusions.append(ScreenExclusion(instrument, reason))
    return kept, exclusions


async def calculate_candidates(
    kept: list[DailyBarSummary], columns: list[IndicatorColumn], before_utc: datetime, read_daily_bars: DailyBarsReader
) -> tuple[list[Candidate], list[ScreenExclusion]]:
    """Step 2, first part: one read of the daily bars of all kept instruments, then the indicator values."""
    if not kept:
        return [], []
    bar_count = max(column.look_back_bars for column in columns)
    bars_by_instrument = await read_daily_bars([summary.instrument for summary in kept], before_utc, bar_count)
    candidates: list[Candidate] = []
    exclusions: list[ScreenExclusion] = []
    for summary in kept:
        bars = bars_by_instrument.get(summary.instrument, [])
        values = {column.name: calculate_value(column, bars) for column in columns}
        missing = next((name for name, value in values.items() if value is None), None)
        if missing is not None or not bars:
            exclusions.append(ScreenExclusion(summary.instrument, f"No value: {missing}"))
            continue
        candidates.append(Candidate(summary, bars[-1].close, cast("dict[str, float]", values)))
    return candidates, exclusions


def apply_conditions(
    conditions: Sequence[Mapping[str, Any]], candidates: list[Candidate]
) -> tuple[list[tuple[Candidate, dict[str, float]]], list[ScreenExclusion]]:
    """Step 2, second part. The rank percentiles use all candidates, so the order of the conditions does not change
    the result. Returns the passing candidates with their percentiles, and the excluded instruments."""
    percentiles_by_name: dict[str, tuple[list[float], list[float]]] = {}
    for condition in conditions:
        if condition["kind"] == "rank":
            name = name_indicator(condition["indicator"])
            percentiles_by_name[name] = calculate_percentiles([candidate.values[name] for candidate in candidates])
    passing: list[tuple[Candidate, dict[str, float]]] = []
    exclusions: list[ScreenExclusion] = []
    for position, candidate in enumerate(candidates):
        percentiles = {name: shares[0][position] for name, shares in percentiles_by_name.items()}
        failed = next(
            (
                f"indicator_conditions[{index}]: {describe_condition(condition)}"
                for index, condition in enumerate(conditions)
                if not is_condition_true(condition, candidate, find_shares(condition, percentiles_by_name, position))
            ),
            None,
        )
        if failed is None:
            passing.append((candidate, percentiles))
        else:
            exclusions.append(ScreenExclusion(candidate.summary.instrument, failed))
    return passing, exclusions


def find_shares(
    condition: Mapping[str, Any], percentiles_by_name: dict[str, tuple[list[float], list[float]]], position: int
) -> tuple[float, float]:
    if condition["kind"] != "rank":
        return (0.0, 0.0)
    at_or_below, below = percentiles_by_name[name_indicator(condition["indicator"])]
    return at_or_below[position], below[position]


def sort_rows(order: Mapping[str, Any], passing: list[tuple[Candidate, dict[str, float]]]) -> list[ScreenRow]:
    """Sorts by the order indicator, then by symbol, and keeps the first `keep_first` (at most 500)."""
    name = name_indicator(order["indicator"])
    sign = -1.0 if order["direction"] == "descending" else 1.0
    ordered = sorted(passing, key=lambda item: (sign * item[0].values[name], item[0].summary.instrument.symbol))
    keep_count = min(cast("int", order.get("keep_first", MAX_RESULT_ROWS)), MAX_RESULT_ROWS)
    return [
        ScreenRow(
            instrument=candidate.summary.instrument,
            last_price=candidate.summary.last_close,
            average_trading_value_20=candidate.summary.average_trading_value_20,
            indicator_values=candidate.values,
            percentiles=percentiles,
        )
        for candidate, percentiles in ordered[:keep_count]
    ]


async def run_screen_steps(
    *,
    definition: Definition,
    start_instruments: list[Instrument],
    summaries: list[DailyBarSummary],
    read_daily_bars: DailyBarsReader,
) -> ScreenOutcome:
    """Runs a checked definition on the summaries of the start instruments. `read_daily_bars` is called once."""
    instruments = list(dict.fromkeys(start_instruments))
    summary_by_instrument = {summary.instrument: summary for summary in summaries}
    start_summaries = {
        instrument: summary_by_instrument[instrument]
        for instrument in instruments
        if instrument in summary_by_instrument
    }
    daily_bars_date = find_daily_bars_date(list(start_summaries.values()))
    kept, filter_exclusions = apply_filters(definition["filters"], start_summaries, daily_bars_date)
    before_utc = datetime.combine(daily_bars_date or date.min, time(), tzinfo=UTC) + timedelta(days=1)
    candidates, value_exclusions = await calculate_candidates(
        kept, list_columns(definition), before_utc, read_daily_bars
    )
    passing, condition_exclusions = apply_conditions(definition["indicator_conditions"], candidates)
    excluded = {
        exclusion.instrument: exclusion for exclusion in [*filter_exclusions, *value_exclusions, *condition_exclusions]
    }
    no_daily_bars = {instrument: ScreenExclusion(instrument, NO_DAILY_BARS) for instrument in instruments}
    return ScreenOutcome(
        daily_bars_date=daily_bars_date,
        start_count=len(instruments),
        after_filters_count=len(kept),
        after_indicator_conditions_count=len(passing),
        rows=sort_rows(definition["order"], passing),
        exclusions=[
            excluded.get(instrument, no_daily_bars[instrument])
            for instrument in instruments
            if instrument in excluded or instrument not in start_summaries
        ],
    )
