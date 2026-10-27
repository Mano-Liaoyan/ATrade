"""Clock fake: always returns the time it was given."""

from datetime import datetime


class FixedClock:
    def __init__(self, now_utc: datetime) -> None:
        self.now_utc = now_utc

    def read_now_utc(self) -> datetime:
        return self.now_utc
