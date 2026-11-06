"""The 2 steps of a screen run (docs/architecture/screen.md sections 24.3 and 24.5), on daily bars in memory.

Each instrument has daily bars with one constant close, so SMA(n) is the close when the instrument has n bars.
"""

import asyncio
import time
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from nautilus_trader.model import Bar as NautilusBar

from atrade.foundation.bar import Bar
from atrade.foundation.instrument import Instrument
from atrade.indicator import make_nautilus_bar
from atrade.market_data import DailyBarSummary
from atrade.market_data.daily_bar_summary import calculate_daily_bar_summary
from atrade.screen.screen_run import ScreenOutcome, calculate_values, make_column, run_screen_steps

LAST_DAY = datetime(2026, 1, 2, tzinfo=UTC)
TEN_MILLION = 10_000_000.0


def stock(symbol: str) -> Instrument:
    return Instrument(symbol=symbol, exchange="NASDAQ", currency="USD")


def make_bars(close: str, count: int, last_day: datetime = LAST_DAY) -> list[Bar]:
    price = Decimal(close)
    return [
        Bar(
            start_utc=last_day - timedelta(days=count - 1 - index),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=Decimal(1000),
        )
        for index in range(count)
    ]


def make_summary(
    instrument: Instrument, bars: list[Bar], average_trading_value: float | None = TEN_MILLION
) -> DailyBarSummary:
    return DailyBarSummary(
        instrument=instrument,
        last_day_start_utc=bars[-1].start_utc,
        last_close=bars[-1].close,
        average_trading_value_20=average_trading_value,
    )


class DailyBarsReader:
    """Counts the reads, like the database read of `read_last_daily_bars`."""

    def __init__(self, bars_by_instrument: dict[Instrument, list[Bar]]) -> None:
        self.bars_by_instrument = bars_by_instrument
        self.reads: list[tuple[list[Instrument], datetime, int]] = []

    async def __call__(
        self, instruments: list[Instrument], before_utc: datetime, bar_count: int
    ) -> dict[Instrument, list[Bar]]:
        self.reads.append((instruments, before_utc, bar_count))
        return {
            instrument: [bar for bar in self.bars_by_instrument.get(instrument, []) if bar.start_utc < before_utc][
                -bar_count:
            ]
            for instrument in instruments
        }


def sma(period: int) -> dict[str, Any]:
    return {"indicator": "sma", "parameters": {"period": period}, "output": "value"}


def make_definition(
    *,
    filters: list[dict[str, Any]] | None = None,
    conditions: list[dict[str, Any]] | None = None,
    order: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "start": "watchlist",
        "filters": filters or [],
        "indicator_conditions": conditions or [],
        "order": order or {"indicator": sma(3), "direction": "descending"},
    }


async def run(definition: dict[str, Any], bars_by_instrument: dict[Instrument, list[Bar]]) -> ScreenOutcome:
    summaries = [make_summary(instrument, bars) for instrument, bars in bars_by_instrument.items() if bars]
    return await run_screen_steps(
        definition=definition,
        start_instruments=list(bars_by_instrument),
        summaries=summaries,
        read_daily_bars=DailyBarsReader(bars_by_instrument),
    )


def symbols(outcome: ScreenOutcome) -> list[str]:
    return [row.instrument.symbol for row in outcome.rows]


def reasons(outcome: ScreenOutcome) -> dict[str, str]:
    return {exclusion.instrument.symbol: exclusion.reason for exclusion in outcome.exclusions}


@pytest.mark.anyio
async def test_the_rank_percentile_counts_only_the_instruments_that_step_1_keeps_and_that_have_a_value() -> None:
    bars = {
        stock("A"): make_bars("10", 5),
        stock("B"): make_bars("20", 5),
        stock("C"): make_bars("30", 5),
        stock("D"): make_bars("40", 5),
        # Step 1 removes E, and F has no SMA(3) value. Both have higher closes than D.
        Instrument(symbol="E", exchange="NYSE", currency="USD"): make_bars("50", 5),
        stock("F"): make_bars("60", 2),
    }
    definition = make_definition(
        filters=[{"field": "exchange", "values": ["NASDAQ"]}],
        conditions=[{"kind": "rank", "indicator": sma(3), "end": "top", "percent": 50}],
    )

    outcome = await run(definition, bars)

    assert symbols(outcome) == ["D", "C"]
    assert [row.percentiles for row in outcome.rows] == [{"SMA(3)": 100.0}, {"SMA(3)": 75.0}]
    assert reasons(outcome) == {
        "A": "indicator_conditions[0]: SMA(3) top 50%",
        "B": "indicator_conditions[0]: SMA(3) top 50%",
        "E": "filters[0]: Exchange in NASDAQ",
        "F": "No value: SMA(3)",
    }
    assert (outcome.start_count, outcome.after_filters_count) == (6, 5)
    assert (outcome.after_indicator_conditions_count, outcome.result_count) == (2, 2)
    assert outcome.daily_bars_date == date(2026, 1, 2)


def compare(reference: dict[str, Any], operation: str, value: str) -> dict[str, Any]:
    return {"kind": "compare", "indicator": reference, "operator": operation, "value": value}


@pytest.mark.anyio
async def test_a_change_of_the_condition_order_does_not_change_the_result() -> None:
    bars = {stock(f"S{close}"): make_bars(str(close), 5) for close in range(10, 110, 10)}
    conditions = [
        {"kind": "rank", "indicator": sma(3), "end": "top", "percent": 60},
        compare(sma(2), "<", "95"),
        compare(sma(4), ">=", "20"),
        {"kind": "rank", "indicator": sma(2), "end": "bottom", "percent": 80},
    ]

    first = await run(make_definition(conditions=conditions), bars)
    second = await run(make_definition(conditions=conditions[::-1]), bars)

    assert symbols(first) == ["S80", "S70", "S60", "S50"]
    assert first.rows == second.rows
    assert first.after_indicator_conditions_count == second.after_indicator_conditions_count == 4


@pytest.mark.anyio
async def test_an_instrument_without_a_value_of_a_condition_or_of_the_order_is_excluded_with_the_indicator() -> None:
    bars = {stock("LONG"): make_bars("10", 30), stock("SHORT"): make_bars("10", 10), stock("TINY"): make_bars("10", 3)}
    definition = make_definition(
        conditions=[compare(sma(5), ">", "1")], order={"indicator": sma(20), "direction": "ascending"}
    )

    outcome = await run(definition, bars)

    assert symbols(outcome) == ["LONG"]
    assert reasons(outcome) == {"SHORT": "No value: SMA(20)", "TINY": "No value: SMA(5)"}
    assert outcome.rows[0].indicator_values == {"SMA(5)": 10.0, "SMA(20)": 10.0}


@pytest.mark.anyio
async def test_adr_percent_works_as_a_condition_and_as_the_order() -> None:
    def make_wide_bars(high: str) -> list[Bar]:
        return [replace(bar, high=Decimal(high)) for bar in make_bars("10", 5)]

    adr_percent = {"indicator": "adr_percent", "parameters": {"period": 3}, "output": "value"}
    bars = {
        stock("NARROW"): make_wide_bars("10.1"),
        stock("MIDDLE"): make_wide_bars("10.5"),
        stock("WIDE"): make_wide_bars("11"),
    }
    definition = make_definition(
        conditions=[compare(adr_percent, ">", "3")], order={"indicator": adr_percent, "direction": "descending"}
    )

    outcome = await run(definition, bars)

    assert symbols(outcome) == ["WIDE", "MIDDLE"]
    assert outcome.rows[0].indicator_values == {"ADR%(3)": pytest.approx(10.0, rel=1e-9)}


@pytest.mark.anyio
async def test_an_instrument_with_a_false_condition_is_excluded_with_the_location_of_the_condition() -> None:
    bars = {
        stock("LOW"): make_bars("10", 5),
        stock("HIGH"): make_bars("50", 5),
        stock("RISE"): [*make_bars("20", 4, LAST_DAY - timedelta(days=1)), *make_bars("40", 1)],
    }
    definition = make_definition(
        conditions=[
            compare(sma(3), ">=", "20"),
            {"kind": "close_versus_line", "indicator": sma(3), "side": "above"},
        ]
    )

    outcome = await run(definition, bars)

    assert symbols(outcome) == ["RISE"]
    assert reasons(outcome) == {
        "LOW": "indicator_conditions[0]: SMA(3) >= 20",
        "HIGH": "indicator_conditions[1]: Close above SMA(3)",
    }


@pytest.mark.anyio
async def test_a_screen_result_has_at_most_500_rows_and_keep_first_keeps_the_first_of_the_order() -> None:
    bars = {stock(f"S{number:03}"): make_bars(str(number), 3) for number in range(1, 602)}

    without_keep_first = await run(make_definition(), bars)
    with_keep_first = await run(
        make_definition(order={"indicator": sma(3), "direction": "ascending", "keep_first": 3}), bars
    )

    assert without_keep_first.result_count == 500
    assert without_keep_first.after_indicator_conditions_count == 601
    assert symbols(without_keep_first)[:2] == ["S601", "S600"]
    assert symbols(without_keep_first)[-1] == "S102"
    assert symbols(with_keep_first) == ["S001", "S002", "S003"]
    assert without_keep_first.exclusions == with_keep_first.exclusions == []


@pytest.mark.anyio
async def test_step_2_reads_the_daily_bars_of_all_instruments_in_one_read_of_the_longest_look_back() -> None:
    bars = {stock(f"S{number}"): make_bars(str(number), 40) for number in range(1, 30)}
    reader = DailyBarsReader(bars)
    definition = make_definition(
        filters=[{"field": "last_price", "operator": ">=", "value": "2"}],
        conditions=[compare({"indicator": "rsi", "parameters": {"period": 3}, "output": "value"}, ">", "-1")],
        order={"indicator": sma(10), "direction": "descending"},
    )

    await run_screen_steps(
        definition=definition,
        start_instruments=list(bars),
        summaries=[make_summary(instrument, instrument_bars) for instrument, instrument_bars in bars.items()],
        read_daily_bars=reader,
    )

    assert len(reader.reads) == 1
    instruments, before_utc, bar_count = reader.reads[0]
    assert [instrument.symbol for instrument in instruments] == [f"S{number}" for number in range(2, 30)]
    assert before_utc == LAST_DAY + timedelta(days=1)
    # RSI is a recursive average: 8 x its period (indicator.md section 23.4).
    assert bar_count == 24


@pytest.mark.anyio
async def test_still_trading_keeps_the_instruments_with_a_daily_bar_in_the_last_7_days() -> None:
    bars = {
        stock("NOW"): make_bars("10", 5),
        stock("WEEK"): make_bars("20", 5, LAST_DAY - timedelta(days=7)),
        stock("GONE"): make_bars("30", 5, LAST_DAY - timedelta(days=8)),
        stock("NONE"): [],
    }

    outcome = await run(make_definition(filters=[{"field": "still_trading"}]), bars)

    assert symbols(outcome) == ["WEEK", "NOW"]
    assert reasons(outcome) == {"GONE": "filters[0]: Still trading", "NONE": "No daily bars"}


def custom(expression: str, name: str = "Custom") -> dict[str, Any]:
    formula = {"name": name, "expression": expression, "chart_placement": "own"}
    return {"indicator": "custom_1", "parameters": {}, "output": "value", "formula": formula}


@pytest.mark.anyio
async def test_a_custom_indicator_runs_from_the_expression_of_the_reference_and_a_no_value_excludes_one_instrument() -> (
    None
):
    reference = custom("1 / (close - 10) + mean(close, 3) - mean(close, 3)")
    good, zero = stock("GOOD"), stock("ZERO")
    definition = make_definition(
        conditions=[compare(reference, ">", "0")], order={"indicator": reference, "direction": "descending"}
    )

    outcome = await run(definition, {good: make_bars("11", 3), zero: make_bars("10", 3)})

    assert symbols(outcome) == ["GOOD"]
    assert outcome.rows[0].indicator_values == {"Custom": 1.0}
    assert reasons(outcome) == {"ZERO": "No value: Custom"}


@pytest.mark.anyio
async def test_a_custom_indicator_reads_the_bars_of_its_look_back() -> None:
    reference = custom("lag(mean(close, 4), 2)")
    too_short, long_enough = stock("SHORT"), stock("LONG")
    definition = make_definition(order={"indicator": reference, "direction": "descending"})

    outcome = await run(definition, {too_short: make_bars("5", 5), long_enough: make_bars("5", 6)})

    assert symbols(outcome) == ["LONG"]
    assert reasons(outcome) == {"SHORT": "No value: Custom"}


def test_the_bars_of_an_instrument_convert_one_time_for_all_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    conversions = 0

    def count_conversion(bar: Bar) -> NautilusBar:
        nonlocal conversions
        conversions += 1
        return make_nautilus_bar(bar)

    monkeypatch.setattr("atrade.screen.screen_run.make_nautilus_bar", count_conversion)
    columns = [make_column(sma(2)), make_column(sma(3))]

    values = calculate_values(columns, make_bars("5", 3))

    assert values == {"SMA(2)": 5.0, "SMA(3)": 5.0}
    assert conversions == 3


@pytest.mark.anyio
async def test_the_event_loop_keeps_running_while_a_screen_run_calculates(monkeypatch: pytest.MonkeyPatch) -> None:
    def calculate_slowly(_column: object, _bars: object) -> float:
        time.sleep(0.05)
        return 1.0

    monkeypatch.setattr("atrade.screen.screen_run.calculate_value", calculate_slowly)
    instruments = [stock(f"S{index}") for index in range(3)]
    definition = make_definition(order={"indicator": sma(2), "direction": "descending"})
    ticks = 0

    async def count_ticks() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.001)
            ticks += 1

    counter = asyncio.create_task(count_ticks())
    outcome = await run(definition, {instrument: make_bars("5", 2) for instrument in instruments})
    counter.cancel()

    assert symbols(outcome) == ["S0", "S1", "S2"]
    assert ticks >= 10


def average_trading_value(period: int | None = 20) -> dict[str, Any]:
    parameters = {} if period is None else {"period": period}
    return {"indicator": "average_trading_value", "parameters": parameters, "output": "value"}


async def run_with_summaries_of_the_bars(
    definition: dict[str, Any], bars_by_instrument: dict[Instrument, list[Bar]], *, prefilter: bool
) -> tuple[ScreenOutcome, list[str]]:
    """The outcome and the symbols of the daily bar read. The summaries are the real summaries of the bars."""
    reader = DailyBarsReader(bars_by_instrument)
    outcome = await run_screen_steps(
        definition=definition,
        start_instruments=list(bars_by_instrument),
        summaries=[calculate_daily_bar_summary(instrument, bars) for instrument, bars in bars_by_instrument.items()],
        read_daily_bars=reader,
        prefilter=prefilter,
    )
    return outcome, [instrument.symbol for reads in reader.reads for instrument in reads[0]]


# 20 daily bars with a volume of 1000 give an average trading value of 1000 x the close. 19 daily bars give no value.
BARS_FOR_PREFILTER = {
    stock("LOW"): make_bars("10", 20),
    stock("EQUAL"): make_bars("20", 20),
    stock("HIGH"): make_bars("30", 20),
    stock("SHORT"): make_bars("40", 19),
}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operator", "kept_symbols"),
    [
        (">=", ["EQUAL", "HIGH", "SHORT"]),
        (">", ["HIGH", "SHORT"]),
        ("<=", ["LOW", "EQUAL", "SHORT"]),
        ("<", ["LOW", "SHORT"]),
    ],
)
async def test_the_prefilter_reads_fewer_instruments_and_gives_the_same_rows(
    operator: str, kept_symbols: list[str]
) -> None:
    definition = make_definition(conditions=[compare(average_trading_value(), operator, "20000")])

    plain, plain_read = await run_with_summaries_of_the_bars(definition, BARS_FOR_PREFILTER, prefilter=False)
    filtered, filtered_read = await run_with_summaries_of_the_bars(definition, BARS_FOR_PREFILTER, prefilter=True)

    assert plain_read == ["LOW", "EQUAL", "HIGH", "SHORT"]
    assert filtered_read == kept_symbols
    assert filtered.rows == plain.rows
    assert filtered.rows
    assert filtered.after_filters_count == plain.after_filters_count == 4
    assert filtered.after_prefilter_count == len(kept_symbols)
    assert plain.after_prefilter_count == 4
    assert filtered.after_indicator_conditions_count == plain.after_indicator_conditions_count
    # The instrument without a summary value stays out, with the reason of step 2.
    assert reasons(filtered)["SHORT"] == reasons(plain)["SHORT"] == "No value: Average trading value(20)"


@pytest.mark.anyio
async def test_the_prefilter_gives_the_condition_as_the_reason() -> None:
    definition = make_definition(conditions=[compare(average_trading_value(), ">=", "20000")])

    outcome, _ = await run_with_summaries_of_the_bars(definition, BARS_FOR_PREFILTER, prefilter=True)

    assert reasons(outcome)["LOW"] == "indicator_conditions[0]: Average trading value(20) >= 20000"


@pytest.mark.anyio
async def test_the_prefilter_uses_the_default_period_of_a_reference_without_a_period() -> None:
    definition = make_definition(conditions=[compare(average_trading_value(None), ">=", "20000")])

    _, read = await run_with_summaries_of_the_bars(definition, BARS_FOR_PREFILTER, prefilter=True)

    assert read == ["EQUAL", "HIGH", "SHORT"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "condition",
    [
        compare(average_trading_value(19), ">=", "20000"),
        compare(sma(3), ">=", "20"),
        {"kind": "close_versus_line", "indicator": average_trading_value(), "side": "above"},
    ],
    ids=["other period", "other indicator", "not compare"],
)
async def test_the_prefilter_keeps_all_instruments_for_a_condition_that_the_summary_does_not_hold(
    condition: dict[str, Any],
) -> None:
    definition = make_definition(conditions=[condition])

    plain, _ = await run_with_summaries_of_the_bars(definition, BARS_FOR_PREFILTER, prefilter=False)
    filtered, read = await run_with_summaries_of_the_bars(definition, BARS_FOR_PREFILTER, prefilter=True)

    assert read == ["LOW", "EQUAL", "HIGH", "SHORT"]
    assert filtered == plain


@pytest.mark.anyio
async def test_the_prefilter_does_not_run_when_the_definition_has_a_rank_condition() -> None:
    # The top 50% of SMA(3) among all candidates. Without LOW, the percentiles would be different.
    rank = {"kind": "rank", "indicator": sma(3), "end": "top", "percent": 50}
    definition = make_definition(conditions=[compare(average_trading_value(), ">=", "20000"), rank])

    plain, _ = await run_with_summaries_of_the_bars(definition, BARS_FOR_PREFILTER, prefilter=False)
    filtered, read = await run_with_summaries_of_the_bars(definition, BARS_FOR_PREFILTER, prefilter=True)

    assert read == ["LOW", "EQUAL", "HIGH", "SHORT"]
    assert filtered == plain


@pytest.mark.anyio
async def test_the_prefilter_does_not_change_the_daily_bars_date_of_the_still_trading_filter() -> None:
    # Only LOW has the newest bar. The prefilter removes it, but OLD must stay 30 days behind the daily bars date.
    bars_by_instrument = {
        stock("LOW"): make_bars("10", 20),
        stock("OLD"): make_bars("30", 20, LAST_DAY - timedelta(days=30)),
    }
    definition = make_definition(
        filters=[{"field": "still_trading"}], conditions=[compare(average_trading_value(), ">=", "20000")]
    )

    plain, _ = await run_with_summaries_of_the_bars(definition, bars_by_instrument, prefilter=False)
    filtered, _ = await run_with_summaries_of_the_bars(definition, bars_by_instrument, prefilter=True)

    assert filtered.rows == plain.rows == []
    assert filtered.daily_bars_date == plain.daily_bars_date == LAST_DAY.date()


@pytest.mark.anyio
async def test_a_run_without_the_prefilter_reads_all_kept_instruments_and_gives_the_step_2_reasons() -> None:
    """The screen page run: it shows the exclusion reasons (section 24.5)."""
    bars_by_instrument = {stock("LOW"): make_bars("10", 20), stock("HIGH"): make_bars("30", 20)}
    reader = DailyBarsReader(bars_by_instrument)
    definition = make_definition(conditions=[compare(average_trading_value(), ">=", "20000")])

    outcome = await run_screen_steps(
        definition=definition,
        start_instruments=list(bars_by_instrument),
        summaries=[calculate_daily_bar_summary(instrument, bars) for instrument, bars in bars_by_instrument.items()],
        read_daily_bars=reader,
    )

    assert [instrument.symbol for instrument in reader.reads[0][0]] == ["LOW", "HIGH"]
    assert symbols(outcome) == ["HIGH"]
    assert reasons(outcome) == {"LOW": "indicator_conditions[0]: Average trading value(20) >= 20000"}
