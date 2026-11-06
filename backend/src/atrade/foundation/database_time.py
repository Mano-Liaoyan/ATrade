"""Each `timestamptz` that psycopg reads is in UTC.

psycopg gives a `timestamptz` in the time zone of the database session. Then `.date()`, `.year`, and the JSON of a time
change with the PostgreSQL setting. ATrade stores and calculates in UTC, so the loaders change each read to UTC. The
registration is on the global adapters, so it applies to all connections of the process.
"""

from datetime import UTC, datetime

import psycopg
from psycopg.types.datetime import TimestamptzBinaryLoader, TimestamptzLoader


class UtcTextLoader(TimestamptzLoader):
    def load(self, data: bytes) -> datetime:
        return super().load(data).astimezone(UTC)


class UtcBinaryLoader(TimestamptzBinaryLoader):
    def load(self, data: bytes) -> datetime:
        return super().load(data).astimezone(UTC)


def read_timestamptz_in_utc() -> None:
    psycopg.adapters.register_loader("timestamptz", UtcTextLoader)
    psycopg.adapters.register_loader("timestamptz", UtcBinaryLoader)
