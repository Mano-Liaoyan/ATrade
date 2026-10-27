"""Bar and instrument fields that the bars route and the live bar socket share."""

from typing import Annotated

from pydantic import BaseModel, Field

from atrade.foundation.bar import Bar

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
