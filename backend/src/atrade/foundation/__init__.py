"""Shared building blocks with no business rules. Each module here is a public entry: clock, instrument, settings."""

from atrade.foundation.database_time import read_timestamptz_in_utc

read_timestamptz_in_utc()
