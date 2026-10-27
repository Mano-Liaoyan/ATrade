"""IBKR historical data: splits a time range into reqHistoricalData requests and turns BarData into bars.

IBKR limits the duration of one request for each bar size. ATrade uses the step sizes of the IBKR historical
data limitations page, in whole days, so each request has a known length:
https://interactivebrokers.github.io/tws-api/historical_limitations.html
"""

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ib_async import BarData

from atrade.foundation.bar import SECONDS_PER_DAY, Bar, BarPeriod, TimeRange

BAR_SIZE_SETTINGS = {
    BarPeriod.ONE_MINUTE: "1 min",
    BarPeriod.FIVE_MINUTES: "5 mins",
    BarPeriod.FIFTEEN_MINUTES: "15 mins",
    BarPeriod.THIRTY_MINUTES: "30 mins",
    BarPeriod.ONE_HOUR: "1 hour",
    BarPeriod.ONE_DAY: "1 day",
}
MAX_REQUEST_DAYS = {
    BarPeriod.ONE_MINUTE: 1,
    BarPeriod.FIVE_MINUTES: 7,
    BarPeriod.FIFTEEN_MINUTES: 14,
    BarPeriod.THIRTY_MINUTES: 28,
    BarPeriod.ONE_HOUR: 28,
    BarPeriod.ONE_DAY: 364,
}


@dataclass(frozen=True)
class HistoricalDataRequest:
    """One reqHistoricalData call. It reads `duration` back from `chunk.end_utc`. Only bars in `chunk` are kept."""

    chunk: TimeRange
    duration: str


def plan_historical_data_requests(time_range: TimeRange, bar_period: BarPeriod) -> list[HistoricalDataRequest]:
    """Splits the range into requests of at most the IBKR step size, oldest first.

    The duration is rounded up to whole days, so IBKR can return bars before the chunk. The caller drops them.
    """
    max_chunk_length = timedelta(days=MAX_REQUEST_DAYS[bar_period])
    requests: list[HistoricalDataRequest] = []
    chunk_end_utc = time_range.end_utc
    while chunk_end_utc > time_range.start_utc:
        chunk_start_utc = max(time_range.start_utc, chunk_end_utc - max_chunk_length)
        duration_days = math.ceil((chunk_end_utc - chunk_start_utc).total_seconds() / SECONDS_PER_DAY)
        requests.append(HistoricalDataRequest(TimeRange(chunk_start_utc, chunk_end_utc), f"{duration_days} D"))
        chunk_end_utc = chunk_start_utc
    requests.reverse()
    return requests


def read_bar_start_utc(bar_data: BarData) -> datetime:
    """With formatDate=2, intraday bars have a UTC datetime. Daily bars have a date: the bar starts 00:00 UTC."""
    bar_date = bar_data.date
    if isinstance(bar_date, datetime):
        return bar_date.astimezone(UTC)
    return datetime.combine(date(bar_date.year, bar_date.month, bar_date.day), datetime.min.time(), tzinfo=UTC)


def to_bar(bar_data: BarData) -> Bar:
    # str() keeps the decimal digits that IBKR sent. Decimal(float) would add binary noise.
    return Bar(
        start_utc=read_bar_start_utc(bar_data),
        open=Decimal(str(bar_data.open)),
        high=Decimal(str(bar_data.high)),
        low=Decimal(str(bar_data.low)),
        close=Decimal(str(bar_data.close)),
        volume=Decimal(str(bar_data.volume)),
    )


def keep_bars_in_chunk(bars_data: list[BarData], chunk: TimeRange) -> list[Bar]:
    bars = [to_bar(bar_data) for bar_data in bars_data]
    return [bar for bar in bars if chunk.start_utc <= bar.start_utc < chunk.end_utc]
