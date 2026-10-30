"""The 7 indicator classes that wrap NautilusTrader indicators (docs/architecture/indicator.md sections 23.2, 23.3,
and 23.5, #161).
"""

import itertools
import json
import math
import random
import statistics
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Protocol

import pytest

from atrade.backtest.backtest_store import BacktestRequest
from atrade.backtest.strategy_engine_run import StrategyRun, run_strategy_on_bars
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.indicator import ATR, EMA, MACD, RSI, SMA, BollingerBands, DonchianChannel

RECORD_STRATEGY_FILE = Path(__file__).parent / "strategies" / "record_indicator_outputs.py"
FIRST_BAR_UTC = datetime(2026, 1, 1, tzinfo=UTC)
BAR_COUNT = 80

type Outputs = list[float | None]


class ScreenIndicator(Protocol):
    @property
    def initialized(self) -> bool: ...

    def update(self, bar: Bar) -> None: ...

    def reset(self) -> None: ...


type IndicatorWithOutputs = tuple[ScreenIndicator, Callable[[], Outputs]]


def with_value(indicator: SMA | EMA | ATR | RSI) -> IndicatorWithOutputs:
    return indicator, lambda: [indicator.value]


def with_macd_lines(indicator: MACD) -> IndicatorWithOutputs:
    return indicator, lambda: [indicator.value, indicator.signal, indicator.histogram]


def with_channel_lines(indicator: BollingerBands | DonchianChannel) -> IndicatorWithOutputs:
    return indicator, lambda: [indicator.upper, indicator.middle, indicator.lower]


@dataclass(frozen=True)
class IndicatorCase:
    # The constructor call in the test strategy code, for example "SMA(period=5)".
    constructor_code: str
    output_names: list[str]
    # The number of bars that give the first value.
    warm_up_bars: int
    create: Callable[[], IndicatorWithOutputs]


CASES = [
    IndicatorCase("SMA()", ["value"], 50, lambda: with_value(SMA())),
    IndicatorCase("SMA(period=5)", ["value"], 5, lambda: with_value(SMA(period=5))),
    IndicatorCase("EMA()", ["value"], 20, lambda: with_value(EMA())),
    IndicatorCase("ATR()", ["value"], 14, lambda: with_value(ATR())),
    # 14 close changes need 15 closes.
    IndicatorCase("RSI()", ["value"], 15, lambda: with_value(RSI())),
    # The slow EMA (26 bars) and then the signal EMA (9 values): 26 + 9 - 1.
    IndicatorCase("MACD()", ["value", "signal", "histogram"], 34, lambda: with_macd_lines(MACD())),
    IndicatorCase("BollingerBands()", ["upper", "middle", "lower"], 20, lambda: with_channel_lines(BollingerBands())),
    IndicatorCase("DonchianChannel()", ["upper", "middle", "lower"], 20, lambda: with_channel_lines(DonchianChannel())),
]
CASE_IDS = [case.constructor_code for case in CASES]


def make_test_bars() -> list[Bar]:
    """Fixed random daily bars with 2-decimal prices: each close is the previous close times exp(N(0, 0.02))."""
    generator = random.Random(161)
    bars: list[Bar] = []
    previous_close = Decimal("100.00")
    for index in range(BAR_COUNT):
        close = Decimal(str(round(float(previous_close) * math.exp(generator.gauss(0, 0.02)), 2)))
        high = max(previous_close, close) + Decimal(str(round(generator.uniform(0, 1), 2)))
        low = min(previous_close, close) - Decimal(str(round(generator.uniform(0, 1), 2)))
        bars.append(
            Bar(
                start_utc=FIRST_BAR_UTC + timedelta(days=index),
                open=previous_close,
                high=high,
                low=low,
                close=close,
                volume=Decimal(generator.randint(1000, 5000)),
            )
        )
        previous_close = close
    return bars


def read_screen_path_outputs(indicator_with_outputs: IndicatorWithOutputs, bars: list[Bar]) -> list[Outputs]:
    indicator, read_outputs = indicator_with_outputs
    outputs: list[Outputs] = []
    for bar in bars:
        indicator.update(bar)
        outputs.append(read_outputs())
    return outputs


def read_strategy_path_outputs(case: IndicatorCase, bars: list[Bar], tmp_path: Path) -> list[Outputs]:
    record_file = tmp_path / "records.txt"
    code = RECORD_STRATEGY_FILE.read_text()
    output_code = ", ".join(f"self.indicator.{name}" for name in case.output_names)
    settings = {
        'RECORD_FILE = "/tmp/indicator_records.txt"': f"RECORD_FILE = {str(record_file)!r}",
        "self.indicator = atrade.indicator.SMA()": f"self.indicator = atrade.indicator.{case.constructor_code}",
        "outputs = [self.indicator.value]": f"outputs = [{output_code}]",
    }
    for default_line, test_line in settings.items():
        assert default_line in code
        code = code.replace(default_line, test_line)
    request = BacktestRequest(
        strategy_version_id=1,
        instrument=Instrument(symbol="INDIC", exchange="ARCA", currency="USD"),
        bar_period=BarPeriod.ONE_DAY,
        time_range=TimeRange(start_utc=bars[0].start_utc, end_utc=bars[-1].start_utc + timedelta(days=1)),
        paper_capital_usd=Decimal(10000),
    )
    work_directory = tmp_path / "work"
    work_directory.mkdir()
    run_strategy_on_bars(
        StrategyRun(code=code, request=request, starting_cash=Decimal(10000), bars=bars, look_back_bars=[]),
        work_directory,
    )
    return [json.loads(line) for line in record_file.read_text().splitlines()]


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_the_screen_path_and_the_strategy_path_give_the_same_outputs(case: IndicatorCase, tmp_path: Path) -> None:
    bars = make_test_bars()

    screen_outputs = read_screen_path_outputs(case.create(), bars)
    strategy_outputs = read_strategy_path_outputs(case, bars, tmp_path)

    assert len(strategy_outputs) == BAR_COUNT
    assert screen_outputs == strategy_outputs
    # Both paths have "no value" first and values after the warm-up.
    assert screen_outputs[0] == [None] * len(case.output_names)
    assert None not in screen_outputs[-1]


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_the_outputs_are_no_value_before_the_warm_up_end_not_zero(case: IndicatorCase) -> None:
    indicator, read_outputs = case.create()

    outputs = read_screen_path_outputs((indicator, read_outputs), make_test_bars())

    no_value = [None] * len(case.output_names)
    assert outputs[: case.warm_up_bars - 1] == [no_value] * (case.warm_up_bars - 1)
    assert None not in outputs[case.warm_up_bars - 1]
    assert 0.0 not in outputs[case.warm_up_bars - 1]
    # `reset` removes all received bars.
    assert indicator.initialized
    indicator.reset()
    assert not indicator.initialized
    assert read_outputs() == no_value


def calculate_wilder_averages(values: list[float], period: int) -> list[float]:
    """Wilder: the first average is the mean of the first `period` values. Each next average is
    (previous average x (period - 1) + value) / period.
    """
    averages = [sum(values[:period]) / period]
    for value in values[period:]:
        averages.append((averages[-1] * (period - 1) + value) / period)
    return averages


def test_rsi_uses_the_wilder_average_of_the_gains_and_the_losses() -> None:
    bars = make_test_bars()
    closes = [float(bar.close) for bar in bars]
    changes = [close - previous_close for previous_close, close in itertools.pairwise(closes)]
    average_gains = calculate_wilder_averages([max(change, 0.0) for change in changes], 14)
    average_losses = calculate_wilder_averages([max(-change, 0.0) for change in changes], 14)
    expected = [100 - 100 / (1 + gain / loss) for gain, loss in zip(average_gains, average_losses, strict=True)]

    values = [outputs[0] for outputs in read_screen_path_outputs(with_value(RSI()), bars)]

    # The first value is at bar 15, after 14 close changes.
    assert values[14:] == pytest.approx(expected, rel=1e-12)


def test_atr_uses_the_wilder_average_of_the_true_range() -> None:
    bars = make_test_bars()
    true_ranges = [float(bars[0].high - bars[0].low)] + [
        float(max(bar.high - bar.low, abs(bar.high - previous.close), abs(bar.low - previous.close)))
        for previous, bar in itertools.pairwise(bars)
    ]
    expected = calculate_wilder_averages(true_ranges, 14)

    values = [outputs[0] for outputs in read_screen_path_outputs(with_value(ATR()), bars)]

    assert values[13:] == pytest.approx(expected, rel=1e-12)


def give_all_test_bars[IndicatorT: ScreenIndicator](indicator: IndicatorT) -> IndicatorT:
    for bar in make_test_bars():
        indicator.update(bar)
    return indicator


def test_the_donchian_channel_lines_are_upper_middle_and_lower() -> None:
    last_bars = make_test_bars()[-20:]
    highest_high = float(max(bar.high for bar in last_bars))
    lowest_low = float(min(bar.low for bar in last_bars))

    channel = give_all_test_bars(DonchianChannel())

    lines = {"upper": channel.upper, "middle": channel.middle, "lower": channel.lower}
    assert lines == pytest.approx(
        {"upper": highest_high, "middle": (highest_high + lowest_low) / 2, "lower": lowest_low}, rel=1e-12
    )


def test_the_bollinger_bands_lines_are_upper_middle_and_lower() -> None:
    last_closes = [float(bar.close) for bar in make_test_bars()[-20:]]
    mean = statistics.fmean(last_closes)
    deviation = statistics.pstdev(last_closes)

    bands = give_all_test_bars(BollingerBands(period=20, k=2.0))

    lines = {"upper": bands.upper, "middle": bands.middle, "lower": bands.lower}
    assert lines == pytest.approx(
        {"upper": mean + 2 * deviation, "middle": mean, "lower": mean - 2 * deviation}, rel=1e-12
    )


def test_the_macd_lines_are_value_signal_and_histogram() -> None:
    fast = give_all_test_bars(EMA(period=12)).value
    slow = give_all_test_bars(EMA(period=26)).value
    assert fast is not None
    assert slow is not None

    macd = give_all_test_bars(MACD())

    assert macd.value == pytest.approx(fast - slow, rel=1e-12)
    assert macd.signal is not None
    assert macd.histogram == pytest.approx(fast - slow - macd.signal, rel=1e-12)


def test_an_indicator_reads_a_split_adjusted_bar_with_many_decimals() -> None:
    """A 3-for-2 split divides 100 by 1.5. NautilusTrader accepts at most 18 decimals."""
    price = Decimal(100) / Decimal("1.5")
    indicator = SMA(period=1)

    indicator.update(Bar(FIRST_BAR_UTC, price, price, price, price, Decimal(1000) / Decimal(3)))

    assert indicator.value == pytest.approx(66.666666667)
