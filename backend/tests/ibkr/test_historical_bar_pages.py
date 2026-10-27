"""IBKR historical data paging. An internal test: the split has real complexity (docs/architecture.md section 17)."""

from datetime import UTC, date, datetime

from ib_async import BarData

from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.ibkr.historical_bars import HistoricalDataRequest, keep_bars_in_chunk, plan_historical_data_requests


def utc(month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=UTC)


def test_sends_one_request_when_the_range_fits_in_one_step() -> None:
    requests = plan_historical_data_requests(TimeRange(utc(1, 5, 14), utc(1, 5, 21)), BarPeriod.ONE_MINUTE)

    assert requests == [HistoricalDataRequest(TimeRange(utc(1, 5, 14), utc(1, 5, 21)), "1 D")]


def test_splits_a_long_range_into_steps_oldest_first() -> None:
    requests = plan_historical_data_requests(TimeRange(utc(1, 5, 12), utc(1, 7, 18)), BarPeriod.ONE_MINUTE)

    assert requests == [
        HistoricalDataRequest(TimeRange(utc(1, 5, 12), utc(1, 5, 18)), "1 D"),
        HistoricalDataRequest(TimeRange(utc(1, 5, 18), utc(1, 6, 18)), "1 D"),
        HistoricalDataRequest(TimeRange(utc(1, 6, 18), utc(1, 7, 18)), "1 D"),
    ]


def test_splits_a_7_day_warm_up_of_1_minute_bars_into_7_requests_of_1_day() -> None:
    """The forward test warm-up (docs/architecture/forward_test.md section 12.15). IBKR refuses "7 D" plus a rest in
    seconds for 1-minute bars (error 321). Each request here is 1 whole day."""
    requests = plan_historical_data_requests(TimeRange(utc(1, 1, 3, 10), utc(1, 8, 3, 10)), BarPeriod.ONE_MINUTE)

    assert [request.duration for request in requests] == ["1 D"] * 7
    assert requests[0].chunk.start_utc == utc(1, 1, 3, 10)
    assert requests[-1].chunk.end_utc == utc(1, 8, 3, 10)


def test_uses_the_ibkr_step_size_of_each_bar_period() -> None:
    year_range = TimeRange(utc(1, 1), datetime(2027, 1, 1, tzinfo=UTC))

    five_minute_requests = plan_historical_data_requests(TimeRange(utc(1, 1), utc(1, 15)), BarPeriod.FIVE_MINUTES)
    daily_requests = plan_historical_data_requests(year_range, BarPeriod.ONE_DAY)

    assert [request.duration for request in five_minute_requests] == ["7 D", "7 D"]
    assert daily_requests == [
        HistoricalDataRequest(TimeRange(utc(1, 1), utc(1, 2)), "1 D"),
        HistoricalDataRequest(TimeRange(utc(1, 2), datetime(2027, 1, 1, tzinfo=UTC)), "364 D"),
    ]


def test_rounds_a_part_of_a_day_up_to_a_whole_day() -> None:
    requests = plan_historical_data_requests(TimeRange(utc(1, 1, 6), utc(1, 3)), BarPeriod.ONE_HOUR)

    assert requests == [HistoricalDataRequest(TimeRange(utc(1, 1, 6), utc(1, 3)), "2 D")]


def test_keeps_only_the_bars_that_start_in_the_chunk() -> None:
    bars_data = [
        BarData(date=utc(1, 5, 13, 59), open=1.5, high=2.25, low=1.0, close=2.0, volume=300.0),
        BarData(date=utc(1, 5, 14), open=189.53, high=190.1, low=189.2, close=189.9, volume=1200.0),
        BarData(date=utc(1, 5, 15), open=1.5, high=2.25, low=1.0, close=2.0, volume=300.0),
    ]

    bars = keep_bars_in_chunk(bars_data, TimeRange(utc(1, 5, 14), utc(1, 5, 15)))

    assert [(bar.start_utc, str(bar.open), str(bar.high)) for bar in bars] == [(utc(1, 5, 14), "189.53", "190.1")]


def test_starts_a_daily_bar_at_midnight_utc_of_its_trading_date() -> None:
    bars_data = [BarData(date=date(2026, 1, 5), open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)]

    bars = keep_bars_in_chunk(bars_data, TimeRange(utc(1, 5), utc(1, 6)))

    assert [bar.start_utc for bar in bars] == [utc(1, 5)]
