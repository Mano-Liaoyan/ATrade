"""A strategy error ends the engine run with its traceback, also when the log writer is late."""

from pathlib import Path

import pytest

from atrade.backtest import strategy_engine_run
from atrade.backtest.strategy_engine_run import StrategyFailedError, StrategyRun, run_strategy_on_bars
from tests.backtest.real_runner import TEST_STRATEGY_FILE
from tests.backtest.test_strategy_template_backtest import (
    BAR_COUNT,
    FIRST_BAR_UTC,
    PAPER_CAPITAL_USD,
    make_request,
    make_wave_bars,
)


def test_an_error_in_on_bar_fails_the_run_when_the_error_log_is_still_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # logger_flush() only asks the log writer thread to write. On a slow machine the file can still be empty.
    def read_empty_error_log(_work_directory: Path) -> str:
        return ""

    monkeypatch.setattr(strategy_engine_run, "read_error_log", read_empty_error_log)
    failing_code = TEST_STRATEGY_FILE.read_text().replace(
        "        self.bar_count += 1\n", "        self.bar_count += 1\n        raise ValueError('no trade today')\n"
    )
    run = StrategyRun(
        code=failing_code,
        request=make_request(FIRST_BAR_UTC, BAR_COUNT),
        starting_cash=PAPER_CAPITAL_USD,
        bars=make_wave_bars(),
        look_back_bars=[],
    )

    with pytest.raises(StrategyFailedError) as error:
        run_strategy_on_bars(run, tmp_path)

    assert "ValueError: no trade today" in str(error.value)
    assert "in on_bar" in str(error.value)
