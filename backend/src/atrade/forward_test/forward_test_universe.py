"""The quarters and members of a multi-instrument forward test (docs/architecture/forward_test.md sections 12.17 and
12.21): the current quarter, the members that the strategy gets in it, and the members for the bar fetcher.

The start route records the members of the first quarter. The child records each later quarter at its start, also
after an interruption: a restart gives the strategy the members of the current quarter.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg

from atrade.forward_test import forward_test_store
from atrade.forward_test.forward_test_store import ForwardTestRow
from atrade.foundation.instrument import Instrument
from atrade.market_data import read_us_universe_members, read_us_universe_quarter_starts


@dataclass(frozen=True)
class UniverseQuarter:
    quarter_start_utc: datetime
    members: tuple[Instrument, ...]


@dataclass(frozen=True)
class UniverseNodeInput:
    """What the LiveNode of a multi-instrument forward test needs besides LiveNodeInput (section 12.17)."""

    row: ForwardTestRow
    quarter: UniverseQuarter
    # The members of all recorded quarters. A restored position of an earlier member belongs to the strategy.
    known_instruments: tuple[Instrument, ...]


def find_calendar_quarter_start_utc(now_utc: datetime) -> datetime:
    """The start of the calendar quarter that contains `now_utc`."""
    first_month_of_quarter = 3 * ((now_utc.month - 1) // 3) + 1
    return datetime(now_utc.year, first_month_of_quarter, 1, tzinfo=UTC)


async def find_current_us_universe_quarter(*, database_url: str, now_utc: datetime) -> datetime | None:
    """The last stored quarter start on or after the start of the calendar quarter of `now_utc`. The stored start is
    the first trading day of the quarter (market_data.md section 8.9). None before the update of the quarter ran."""
    calendar_quarter_start_utc = find_calendar_quarter_start_utc(now_utc)
    quarter_starts = await read_us_universe_quarter_starts(database_url=database_url, end_utc=now_utc)
    current = [start_utc for start_utc in quarter_starts if start_utc >= calendar_quarter_start_utc]
    return current[-1] if current else None


async def read_us_universe_instruments(
    *, database_url: str, quarter_start_utc: datetime, top_n: int
) -> list[Instrument]:
    members = await read_us_universe_members(
        database_url=database_url, quarter_start_utc=quarter_start_utc, top_n=top_n
    )
    return [member.instrument for member in members]


async def read_running_member_lists(database_url: str) -> dict[int, list[Instrument]]:
    """The members of the last recorded quarter of each running multi-instrument forward test (section 12.20)."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await forward_test_store.select_running_member_lists(connection)


async def update_current_quarter(*, database_url: str, row: ForwardTestRow, now_utc: datetime) -> UniverseQuarter:
    """Returns the members of the current quarter, and records them when the quarter is new (section 12.17).

    `rule`: the first N ranks of the stored US universe of the current quarter. Until the quarterly update stored
    it, the last recorded quarter stays. `list`: the watchlist members at the start stay. A new calendar quarter
    records them again, so the Instruments tab counts the quarters (section 12.24).
    """
    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as connection:
        recorded = await forward_test_store.select_universe_members(connection, row.id)
        last_start_utc = max(recorded)
        last_quarter = UniverseQuarter(last_start_utc, tuple(recorded[last_start_utc]))
        if row.universe_kind == "rule" and row.universe_top_n is not None:
            quarter_start_utc = await find_current_us_universe_quarter(database_url=database_url, now_utc=now_utc)
            if quarter_start_utc is None or quarter_start_utc <= last_start_utc:
                return last_quarter
            members = await read_us_universe_instruments(
                database_url=database_url, quarter_start_utc=quarter_start_utc, top_n=row.universe_top_n
            )
        else:
            quarter_start_utc = find_calendar_quarter_start_utc(now_utc)
            if quarter_start_utc <= last_start_utc:
                return last_quarter
            members = list(last_quarter.members)
        await forward_test_store.insert_universe_members(
            connection, forward_test_id=row.id, quarter_start_utc=quarter_start_utc, members=members
        )
    return UniverseQuarter(quarter_start_utc, tuple(members))


async def read_universe_node_input(*, database_url: str, row: ForwardTestRow, now_utc: datetime) -> UniverseNodeInput:
    """The current quarter (recorded when it is new) and all members that the forward test ever had."""
    quarter = await update_current_quarter(database_url=database_url, row=row, now_utc=now_utc)
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        recorded = await forward_test_store.select_universe_members(connection, row.id)
    known = dict.fromkeys(member for members in recorded.values() for member in members)
    return UniverseNodeInput(row=row, quarter=quarter, known_instruments=tuple(known))
