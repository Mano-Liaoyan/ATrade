"""Bar: the open, high, low, close, and volume of one instrument in one bar period (GLOSSARY.md).

The data is always called a bar. "Candlestick" is only the chart drawing.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 60 * SECONDS_PER_MINUTE
SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR


class BarPeriod(StrEnum):
    """The bar periods that the chart offers. The values use the NautilusTrader bar specification format."""

    ONE_MINUTE = "1-MINUTE"
    FIVE_MINUTES = "5-MINUTE"
    FIFTEEN_MINUTES = "15-MINUTE"
    THIRTY_MINUTES = "30-MINUTE"
    ONE_HOUR = "1-HOUR"
    ONE_DAY = "1-DAY"

    @property
    def length(self) -> timedelta:
        return timedelta(seconds=BAR_PERIOD_SECONDS[self])

    @property
    def label(self) -> str:
        """The name in messages, for example "1 min". The frontend shows the same names."""
        return BAR_PERIOD_LABELS[self]


BAR_PERIOD_SECONDS = {
    BarPeriod.ONE_MINUTE: SECONDS_PER_MINUTE,
    BarPeriod.FIVE_MINUTES: 5 * SECONDS_PER_MINUTE,
    BarPeriod.FIFTEEN_MINUTES: 15 * SECONDS_PER_MINUTE,
    BarPeriod.THIRTY_MINUTES: 30 * SECONDS_PER_MINUTE,
    BarPeriod.ONE_HOUR: SECONDS_PER_HOUR,
    BarPeriod.ONE_DAY: SECONDS_PER_DAY,
}

BAR_PERIOD_LABELS = {
    BarPeriod.ONE_MINUTE: "1 min",
    BarPeriod.FIVE_MINUTES: "5 min",
    BarPeriod.FIFTEEN_MINUTES: "15 min",
    BarPeriod.THIRTY_MINUTES: "30 min",
    BarPeriod.ONE_HOUR: "1 hour",
    BarPeriod.ONE_DAY: "1 day",
}


@dataclass(frozen=True)
class Bar:
    """`start_utc` is the start of the bar period. A daily bar starts at 00:00 UTC of its trading date."""

    start_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class TimeRange:
    """From `start_utc` (included) to `end_utc` (not included)."""

    start_utc: datetime
    end_utc: datetime


def floor_to_bar_start(time_utc: datetime, bar_period: BarPeriod) -> datetime:
    """Returns the start of the bar period that contains `time_utc`. Periods are counted from the UNIX epoch in UTC."""
    period_seconds = BAR_PERIOD_SECONDS[bar_period]
    unix_seconds = int(time_utc.timestamp())
    return datetime.fromtimestamp(unix_seconds - unix_seconds % period_seconds, tz=UTC)


def ceil_to_bar_start(time_utc: datetime, bar_period: BarPeriod) -> datetime:
    floor_start = floor_to_bar_start(time_utc, bar_period)
    if floor_start == time_utc:
        return floor_start
    return floor_start + bar_period.length
