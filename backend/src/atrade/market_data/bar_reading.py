"""Reads bars from PostgreSQL and asks IBKR only for the time ranges that are not saved yet."""

import asyncio
from dataclasses import dataclass

import psycopg

from atrade.foundation.bar import Bar, BarPeriod, TimeRange, ceil_to_bar_start, floor_to_bar_start
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection
from atrade.market_data import bar_store
from atrade.market_data.bar_store import SavedBarCoverage


class GatewayNotConnectedError(Exception):
    """Some bars are not saved and the Web process is not connected to IB Gateway."""


@dataclass(frozen=True)
class BarRequest:
    instrument: Instrument
    bar_period: BarPeriod
    time_range: TimeRange


def find_missing_ranges(time_range: TimeRange, saved_ranges: list[TimeRange]) -> list[TimeRange]:
    """Returns the parts of `time_range` that no saved range covers. `saved_ranges` must be ordered by start."""
    missing_ranges: list[TimeRange] = []
    cursor_utc = time_range.start_utc
    for saved_range in saved_ranges:
        if saved_range.start_utc > cursor_utc:
            missing_ranges.append(TimeRange(cursor_utc, min(saved_range.start_utc, time_range.end_utc)))
        cursor_utc = max(cursor_utc, saved_range.end_utc)
        if cursor_utc >= time_range.end_utc:
            return missing_ranges
    missing_ranges.append(TimeRange(cursor_utc, time_range.end_utc))
    return missing_ranges


def limit_to_complete_bars(time_range: TimeRange, bar_period: BarPeriod, clock: Clock) -> TimeRange | None:
    """Widens the range to whole bar periods and cuts it at the start of the current bar, which is not complete.

    A bar that is not complete would change later, so ATrade does not save it. Returns None for an empty range.
    """
    start_utc = floor_to_bar_start(time_range.start_utc, bar_period)
    end_utc = min(
        ceil_to_bar_start(time_range.end_utc, bar_period), floor_to_bar_start(clock.read_now_utc(), bar_period)
    )
    if start_utc >= end_utc:
        return None
    return TimeRange(start_utc, end_utc)


class BarReader:
    def __init__(self, *, database_url: str, clock: Clock, gateway_connection: GatewayConnection) -> None:
        self.database_url = database_url
        self.clock = clock
        self.gateway_connection = gateway_connection
        # One fill of missing ranges at a time: two equal chart requests then cause one IBKR request, not two.
        self.fill_lock = asyncio.Lock()

    async def read_bars(self, bar_request: BarRequest) -> list[Bar]:
        """Raises GatewayNotConnectedError, or GatewayRequestError of `ibkr`, when missing bars cannot be read."""
        complete_range = limit_to_complete_bars(bar_request.time_range, bar_request.bar_period, self.clock)
        if complete_range is None:
            return []
        instrument = bar_request.instrument
        bar_period = bar_request.bar_period
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            async with self.fill_lock:
                saved_ranges = await bar_store.select_saved_ranges(connection, instrument, bar_period, complete_range)
                missing_ranges = find_missing_ranges(complete_range, saved_ranges)
                if missing_ranges and not self.gateway_connection.is_connected():
                    raise GatewayNotConnectedError
                for missing_range in missing_ranges:
                    bars = await self.gateway_connection.read_historical_bars(instrument, bar_period, missing_range)
                    await bar_store.save_bars_of_range(connection, instrument, bar_period, missing_range, bars)
            return await bar_store.select_bars(connection, instrument, bar_period, complete_range)


async def read_saved_bars(*, database_url: str, bar_request: BarRequest) -> list[Bar]:
    """Reads only the bars that PostgreSQL holds. It never calls IBKR, so backtests do not depend on IB Gateway."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await bar_store.select_bars(
            connection, bar_request.instrument, bar_request.bar_period, bar_request.time_range
        )


async def has_saved_bars(*, database_url: str, bar_request: BarRequest) -> bool:
    """True when PostgreSQL holds at least one bar that `read_saved_bars` would return. It never calls IBKR."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await bar_store.has_bars(
            connection, bar_request.instrument, bar_request.bar_period, bar_request.time_range
        )


async def read_saved_bar_coverage(*, database_url: str, instruments: list[Instrument]) -> list[list[SavedBarCoverage]]:
    """For each instrument, the bar periods with saved bars and the first and the last saved bar. One query, no IBKR
    call."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await bar_store.select_saved_bar_coverage(connection, instruments)
