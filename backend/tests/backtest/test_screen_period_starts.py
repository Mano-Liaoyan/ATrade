"""The period starts of a `screen` universe and the time of each screen run (docs/architecture/backtest.md section
10.10.2)."""

from datetime import UTC, datetime

from atrade.backtest.backtest_universe import find_screen_period_starts, find_screen_run_time
from atrade.foundation.bar import TimeRange

RANGE = TimeRange(start_utc=datetime(2026, 2, 10, 14, tzinfo=UTC), end_utc=datetime(2026, 5, 15, tzinfo=UTC))


def test_a_quarterly_screen_universe_starts_at_the_range_start_then_at_each_quarter_start() -> None:
    assert find_screen_period_starts(RANGE, "quarter") == [RANGE.start_utc, datetime(2026, 4, 1, tzinfo=UTC)]


def test_a_monthly_screen_universe_starts_at_the_range_start_then_at_each_month_start() -> None:
    assert find_screen_period_starts(RANGE, "month") == [
        RANGE.start_utc,
        datetime(2026, 3, 1, tzinfo=UTC),
        datetime(2026, 4, 1, tzinfo=UTC),
        datetime(2026, 5, 1, tzinfo=UTC),
    ]


def test_a_range_start_in_the_day_runs_the_screen_without_the_bar_of_that_day() -> None:
    # The daily bar of 2026-02-10 starts at 00:00 UTC and closes after 14:00 UTC.
    assert find_screen_run_time(RANGE.start_utc) == datetime(2026, 2, 10, tzinfo=UTC)
    assert find_screen_run_time(datetime(2026, 4, 1, tzinfo=UTC)) == datetime(2026, 4, 1, tzinfo=UTC)
