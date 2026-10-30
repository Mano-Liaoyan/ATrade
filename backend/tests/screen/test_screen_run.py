"""The 2 steps of a screen run (docs/architecture/screen.md sections 24.3 and 24.5), on daily bars in memory.

Each instrument has daily bars with one constant close, so SMA(n) is the close when the instrument has n bars.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from atrade.foundation.bar import Bar
from atrade.foundation.instrument import Instrument
from atrade.market_data import DailyBarSummary
from atrade.screen.screen_run import ScreenOutcome, run_screen_steps

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
