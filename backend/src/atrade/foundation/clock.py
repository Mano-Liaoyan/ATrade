"""The clock boundary. Code reads the current time through a Clock, so tests can pass a fixed time."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def read_now_utc(self) -> datetime: ...


class SystemClock:
    def read_now_utc(self) -> datetime:
        return datetime.now(UTC)
