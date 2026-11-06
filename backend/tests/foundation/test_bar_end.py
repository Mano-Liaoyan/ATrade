from datetime import UTC, datetime

import pytest

from atrade.foundation.bar import BarPeriod, find_bar_end


@pytest.mark.parametrize("bar_period", list(BarPeriod))
def test_a_bar_at_a_bar_period_start_ends_one_period_later(bar_period: BarPeriod) -> None:
    start_utc = datetime(2026, 3, 3, tzinfo=UTC)

    assert find_bar_end(start_utc, bar_period) == start_utc + bar_period.length


def test_the_first_hourly_bar_of_a_day_ends_at_the_start_of_the_next_bar() -> None:
    start_utc = datetime(2026, 3, 3, 14, 30, tzinfo=UTC)

    assert find_bar_end(start_utc, BarPeriod.ONE_HOUR) == datetime(2026, 3, 3, 15, tzinfo=UTC)
