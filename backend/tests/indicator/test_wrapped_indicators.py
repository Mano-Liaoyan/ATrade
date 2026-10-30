"""The 7 indicator classes that wrap NautilusTrader indicators (docs/architecture/indicator.md sections 23.2, 23.3,
and 23.5, #161).
"""

import itertools
import json
import math
import random
import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

import atrade.indicator
from atrade.backtest.backtest_store import BacktestRequest
from atrade.backtest.strategy_engine_run import StrategyRun, run_strategy_on_bars
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument

RECORD_STRATEGY_FILE = Path(__file__).parent / "strategies" / "record_indicator_outputs.py"
FIRST_BAR_UTC = datetime(2026, 1, 1, tzinfo=UTC)
BAR_COUNT = 80


@dataclass(frozen=True)
class IndicatorCase:
    name: str
    outputs: list[str]
    # The number of bars that give the first value.
    warm_up_bars: int
    parameters: dict[str, object] = field(default_factory=dict[str, object])


CASES = [
    IndicatorCase("SMA", ["value"], 50),
    IndicatorCase("SMA", ["value"], 5, {"period": 5}),
    IndicatorCase("EMA", ["value"], 20),
    IndicatorCase("ATR", ["value"], 14),
    # 14 close changes need 15 closes.
    IndicatorCase("RSI", ["value"], 15),
    # The slow EMA (26 bars) and then the signal EMA (9 values): 26 + 9 - 1.
    IndicatorCase("MACD", ["value", "signal", "histogram"], 34),
    IndicatorCase("BollingerBands", ["upper", "middle", "lower"], 20),
    IndicatorCase("DonchianChannel", ["upper", "middle", "lower"], 20),
]


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


def read_screen_path_outputs(case: IndicatorCase, bars: list[Bar]) -> list[list[float | None]]:
    indicator = getattr(atrade.indicator, case.name)(**case.parameters)
    outputs: list[list[float | None]] = []
    for bar in bars:
        indicator.update(bar)
        outputs.append([getattr(indicator, name) for name in case.outputs])
    return outputs


def read_strategy_path_outputs(case: IndicatorCase, bars: list[Bar], tmp_path: Path) -> list[list[float | None]]:
    record_file = tmp_path / "records.txt"
    code = RECORD_STRATEGY_FILE.read_text()
    settings = {
        'RECORD_FILE = "/tmp/indicator_records.txt"': f"RECORD_FILE = {str(record_file)!r}",
        'INDICATOR_NAME = "SMA"': f"INDICATOR_NAME = {case.name!r}",
        "PARAMETERS: dict[str, object] = {}": f"PARAMETERS: dict[str, object] = {case.parameters!r}",
        'OUTPUT_NAMES = ["value"]': f"OUTPUT_NAMES = {case.outputs!r}",
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


@pytest.mark.parametrize("case", CASES, ids=[f"{case.name}{case.parameters}" for case in CASES])
def test_the_screen_path_and_the_strategy_path_give_the_same_outputs(case: IndicatorCase, tmp_path: Path) -> None:
    bars = make_test_bars()

    screen_outputs = read_screen_path_outputs(case, bars)
    strategy_outputs = read_strategy_path_outputs(case, bars, tmp_path)

    assert len(strategy_outputs) == BAR_COUNT
    assert screen_outputs == strategy_outputs
    # Both paths have "no value" first and values after the warm-up.
    assert screen_outputs[0] == [None] * len(case.outputs)
    assert None not in screen_outputs[-1]


@pytest.mark.parametrize("case", CASES, ids=[f"{case.name}{case.parameters}" for case in CASES])
def test_the_outputs_are_no_value_before_the_warm_up_end_not_zero(case: IndicatorCase) -> None:
    bars = make_test_bars()
    indicator = getattr(atrade.indicator, case.name)(**case.parameters)

    outputs = read_screen_path_outputs(case, bars)

    no_value = [None] * len(case.outputs)
    assert outputs[: case.warm_up_bars - 1] == [no_value] * (case.warm_up_bars - 1)
    assert None not in outputs[case.warm_up_bars - 1]
    assert 0.0 not in outputs[case.warm_up_bars - 1]
    # `reset` removes all received bars.
    for bar in bars:
        indicator.update(bar)
    assert indicator.initialized
    indicator.reset()
    assert not indicator.initialized
    assert [getattr(indicator, name) for name in case.outputs] == no_value


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

    values = [output[0] for output in read_screen_path_outputs(IndicatorCase("RSI", ["value"], 15), bars)]

    # The first value is at bar 15, after 14 close changes.
    assert values[14:] == pytest.approx(expected, rel=1e-12)


def test_atr_uses_the_wilder_average_of_the_true_range() -> None:
    bars = make_test_bars()
    true_ranges = [float(bars[0].high - bars[0].low)] + [
        float(max(bar.high - bar.low, abs(bar.high - previous.close), abs(bar.low - previous.close)))
        for previous, bar in itertools.pairwise(bars)
    ]
    expected = calculate_wilder_averages(true_ranges, 14)

    values = [output[0] for output in read_screen_path_outputs(IndicatorCase("ATR", ["value"], 14), bars)]

    assert values[13:] == pytest.approx(expected, rel=1e-12)


def read_last_outputs(name: str, outputs: list[str], parameters: dict[str, object]) -> dict[str, float | None]:
    indicator = getattr(atrade.indicator, name)(**parameters)
    for bar in make_test_bars():
        indicator.update(bar)
    return {output: getattr(indicator, output) for output in outputs}


def test_the_donchian_channel_lines_are_upper_middle_and_lower() -> None:
    last_bars = make_test_bars()[-20:]
    highest_high = float(max(bar.high for bar in last_bars))
    lowest_low = float(min(bar.low for bar in last_bars))

    lines = read_last_outputs("DonchianChannel", ["upper", "middle", "lower"], {})

    assert lines == pytest.approx(
        {"upper": highest_high, "middle": (highest_high + lowest_low) / 2, "lower": lowest_low}, rel=1e-12
    )


def test_the_bollinger_bands_lines_are_upper_middle_and_lower() -> None:
    last_closes = [float(bar.close) for bar in make_test_bars()[-20:]]
    mean = statistics.fmean(last_closes)
    deviation = statistics.pstdev(last_closes)

    lines = read_last_outputs("BollingerBands", ["upper", "middle", "lower"], {"period": 20, "k": 2.0})

    assert lines == pytest.approx(
        {"upper": mean + 2 * deviation, "middle": mean, "lower": mean - 2 * deviation}, rel=1e-12
    )


def test_the_macd_lines_are_value_signal_and_histogram() -> None:
    fast = read_last_outputs("EMA", ["value"], {"period": 12})["value"]
    slow = read_last_outputs("EMA", ["value"], {"period": 26})["value"]
    assert fast is not None
    assert slow is not None

    lines = read_last_outputs("MACD", ["value", "signal", "histogram"], {})

    assert lines["value"] == pytest.approx(fast - slow, rel=1e-12)
    assert lines["signal"] is not None
    assert lines["histogram"] == pytest.approx(fast - slow - lines["signal"], rel=1e-12)
