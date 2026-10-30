"""Reads bars from PostgreSQL through the source order and asks IBKR only for the time ranges that no bar source saved
yet."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from itertools import chain

import psycopg

from atrade.foundation.bar import Bar, BarPeriod, TimeRange, ceil_to_bar_start, floor_to_bar_start
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection
from atrade.market_data import bar_store
from atrade.market_data.bar_source import BarSource, select_source_order
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


@dataclass(frozen=True)
class SourceRange:
    """A part of a requested range and the bar source that gives all bars of the part."""

    bar_source: BarSource
    time_range: TimeRange


@dataclass(frozen=True)
class SavedBars:
    """The merged bars, oldest first, and the bar count of each bar source in the source order."""

    bars: list[Bar]
    bar_counts: dict[BarSource, int]


def assign_source_ranges(
    time_range: TimeRange, saved_ranges_by_source: list[tuple[BarSource, list[TimeRange]]]
) -> list[SourceRange]:
    """The merge rule: each part of `time_range` goes to the first bar source in the source order that saved it.

    A part that the first bar source saved without bars (a holiday) stays with it: the next bar source does not fill
    it. The saved ranges of each bar source must be ordered by start.
    """
    source_ranges: list[SourceRange] = []
    covered_ranges: list[TimeRange] = []
    for bar_source, saved_ranges in saved_ranges_by_source:
        for saved_range in saved_ranges:
            start_utc = max(saved_range.start_utc, time_range.start_utc)
            end_utc = min(saved_range.end_utc, time_range.end_utc)
            if start_utc >= end_utc:
                continue
            new_ranges = find_missing_ranges(TimeRange(start_utc, end_utc), covered_ranges)
            source_ranges.extend(SourceRange(bar_source, new_range) for new_range in new_ranges)
            # Also ranges of one bar source that overlap give each bar once.
            covered_ranges = sorted([*covered_ranges, *new_ranges], key=lambda covered_range: covered_range.start_utc)
    return source_ranges


async def select_source_ranges(
    connection: psycopg.AsyncConnection, source_order: list[BarSource], bar_request: BarRequest
) -> list[SourceRange]:
    saved_ranges_by_source = [
        (
            bar_source,
            await bar_store.select_saved_ranges(
                connection, bar_source, bar_request.instrument, bar_request.bar_period, bar_request.time_range
            ),
        )
        for bar_source in source_order
    ]
    return assign_source_ranges(bar_request.time_range, saved_ranges_by_source)


async def select_merged_bars(
    connection: psycopg.AsyncConnection, source_order: list[BarSource], bar_request: BarRequest
) -> SavedBars:
    source_ranges = await select_source_ranges(connection, source_order, bar_request)
    bar_counts = dict.fromkeys(source_order, 0)
    bar_lists: list[list[Bar]] = []
    for source_range in source_ranges:
        bars = await bar_store.select_bars(
            connection, source_range.bar_source, bar_request.instrument, bar_request.bar_period, source_range.time_range
        )
        bar_counts[source_range.bar_source] += len(bars)
        bar_lists.append(bars)
    merged_bars = sorted(chain.from_iterable(bar_lists), key=lambda bar: bar.start_utc)
    return SavedBars(bars=merged_bars, bar_counts=bar_counts)


class BarReader:
    def __init__(self, *, database_url: str, clock: Clock, gateway_connection: GatewayConnection) -> None:
        self.database_url = database_url
        self.clock = clock
        self.gateway_connection = gateway_connection
        # One fill of missing ranges at a time for each instrument and bar period: two equal chart requests then cause
        # one IBKR request, not two. A slow fill of one instrument does not hold the bars of other instruments.
        self.fill_locks: defaultdict[tuple[Instrument, BarPeriod], asyncio.Lock] = defaultdict(asyncio.Lock)

    async def read_bars(self, bar_request: BarRequest) -> list[Bar]:
        """Reads through the global source order. A part is missing only when no bar source saved it; the missing
        parts come from IBKR and go to ibkr_bar.

        Raises GatewayNotConnectedError, or GatewayRequestError of `ibkr`, when missing bars cannot be read.
        """
        complete_range = limit_to_complete_bars(bar_request.time_range, bar_request.bar_period, self.clock)
        if complete_range is None:
            return []
        instrument = bar_request.instrument
        bar_period = bar_request.bar_period
        complete_request = BarRequest(instrument=instrument, bar_period=bar_period, time_range=complete_range)
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            source_order = await select_source_order(connection)
            async with self.fill_locks[instrument, bar_period]:
                source_ranges = await select_source_ranges(connection, source_order, complete_request)
                saved_ranges = sorted(
                    (source_range.time_range for source_range in source_ranges), key=lambda saved: saved.start_utc
                )
                missing_ranges = find_missing_ranges(complete_range, saved_ranges)
                if missing_ranges and not self.gateway_connection.is_connected():
                    raise GatewayNotConnectedError
                for missing_range in missing_ranges:
                    bars = await self.gateway_connection.read_historical_bars(instrument, bar_period, missing_range)
                    await bar_store.save_bars_of_range(connection, instrument, bar_period, missing_range, bars)
            return (await select_merged_bars(connection, source_order, complete_request)).bars


async def read_saved_bars(*, database_url: str, bar_request: BarRequest, source_order: list[BarSource]) -> SavedBars:
    """Reads only the bars that PostgreSQL holds, through the source order. It never calls IBKR, so backtests do not
    depend on IB Gateway."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await select_merged_bars(connection, source_order, bar_request)


async def save_received_bars(*, database_url: str, bar_request: BarRequest, bars: list[Bar]) -> None:
    """Saves complete bars that a caller received from IBKR for `bar_request.time_range` in ibkr_bar, and records the
    range as saved. A forward test saves its warm-up bars with it, so a backtest of the same period finds them.

    A bar that is already saved gets the new values: a second save of the same bars adds no row.
    """
    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as connection:
        await bar_store.save_bars_of_range(
            connection, bar_request.instrument, bar_request.bar_period, bar_request.time_range, bars
        )


def save_received_bars_blocking(*, database_url: str, bar_request: BarRequest, bars: list[Bar]) -> None:
    """`save_received_bars` for synchronous callers: the forward test DataActor saves each live bar in `on_bar`."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        bar_store.save_bars_of_range_blocking(
            connection, bar_request.instrument, bar_request.bar_period, bar_request.time_range, bars
        )


async def has_saved_bars(*, database_url: str, bar_request: BarRequest, source_order: list[BarSource]) -> bool:
    """True when `read_saved_bars` with the same source order would return at least one bar. It never calls IBKR."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        source_ranges = await select_source_ranges(connection, source_order, bar_request)
        for source_range in source_ranges:
            if await bar_store.has_bars(
                connection,
                source_range.bar_source,
                bar_request.instrument,
                bar_request.bar_period,
                source_range.time_range,
            ):
                return True
    return False


async def read_saved_bar_coverage(*, database_url: str, instruments: list[Instrument]) -> list[list[SavedBarCoverage]]:
    """For each instrument, the bar sources and bar periods with saved bars, and the first and the last saved bar: in
    the order of the bar periods, then in the global source order. No IBKR call."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        source_order = await select_source_order(connection)
        return await bar_store.select_saved_bar_coverage(connection, source_order, instruments)
