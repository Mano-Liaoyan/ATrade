"""Bar and instrument fields that the bars route, the indicator series route, and the live bar socket share."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from atrade.foundation.bar import Bar, BarPeriod

MAX_INSTRUMENT_FIELD_LENGTH = 32
# The query must have at least one character that is not a space.
NOT_ONLY_SPACES_PATTERN = r"\S"


class BarResponse(BaseModel):
    """`time` is the bar start as UNIX seconds (UTC). The chart uses UNIX timestamps, not date strings."""

    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def to_bar_response(bar: Bar) -> BarResponse:
    return BarResponse(
        time=int(bar.start_utc.timestamp()),
        open=float(bar.open),
        high=float(bar.high),
        low=float(bar.low),
        close=float(bar.close),
        volume=float(bar.volume),
    )


InstrumentField = Annotated[
    str, Field(min_length=1, max_length=MAX_INSTRUMENT_FIELD_LENGTH, pattern=NOT_ONLY_SPACES_PATTERN)
]


# One answer has at most this many bars, for example 13 days of 1 minute bars. This keeps IBKR requests few.
MAX_BARS_PER_REQUEST = 20_000


def find_range_problem(bar_period: BarPeriod, start_utc: datetime, end_utc: datetime) -> str | None:
    """The `422` text of a bar range that the bars route and the indicator series route refuse, or None."""
    if start_utc >= end_utc:
        return "start_utc must be before end_utc."
    if (end_utc - start_utc) / bar_period.length > MAX_BARS_PER_REQUEST:
        return f"The range has more than {MAX_BARS_PER_REQUEST} bars of {bar_period.value}. Use a shorter range."
    return None
