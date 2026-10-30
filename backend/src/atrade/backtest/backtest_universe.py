"""The universe of a multi-instrument backtest: the universe periods and their members, the saved-bar check, and the
bars of each member (docs/architecture/backtest.md section 10.10)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from atrade.backtest.backtest_store import BacktestRequest, UniversePeriod
from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import (
    BarRequest,
    BarSource,
    has_saved_bars,
    read_saved_bars,
    read_us_universe_members,
    read_us_universe_quarter_starts,
)

MAX_UNIVERSE_SIZE: Final = 500
UNIVERSE_BAR_PERIODS: Final = (BarPeriod.ONE_DAY, BarPeriod.ONE_HOUR)
# Section 10.10.1: a multi-instrument backtest on 1-day bars reads 1 year of look-back bars (#146).
ONE_DAY_UNIVERSE_LOOK_BACK: Final = timedelta(days=365)


def check_universe(request: BacktestRequest) -> str | None:
    """Returns why the universe of a multi-instrument backtest cannot run, or None (section 10.10.6)."""
    if request.universe is None:
        return None
    if request.bar_period not in UNIVERSE_BAR_PERIODS:
        return "A multi-instrument backtest needs 1 day or 1 hour bars."
    return None


def check_list_members(members: list[Instrument]) -> str | None:
    if not members:
        return "The list has no instrument."
    if len(members) > MAX_UNIVERSE_SIZE:
        return f"The list has {len(members)} instruments. A list can have {MAX_UNIVERSE_SIZE} instruments at most."
    exchanges_by_symbol: dict[str, set[str]] = {}
    for member in members:
        exchanges_by_symbol.setdefault(member.symbol, set()).add(member.exchange)
    repeated = sorted(symbol for symbol, exchanges in exchanges_by_symbol.items() if len(exchanges) > 1)
    if repeated:
        # The simulated venue has one instrument for each symbol (ADR 0003).
        return f"A symbol can be in the list on one exchange only. The list has {', '.join(repeated)} 2 times."
    currencies = sorted({member.currency for member in members})
    if len(currencies) > 1:
        return f"All instruments of the list must have one currency. The list has {', '.join(currencies)}."
    return None


def make_list_periods(time_range: TimeRange, members: list[Instrument]) -> list[UniversePeriod]:
    """A `list` universe has one period: the full range."""
    return [UniversePeriod(start_utc=time_range.start_utc, members=list(dict.fromkeys(members)))]


async def find_rule_periods(*, database_url: str, top_n: int, time_range: TimeRange) -> list[UniversePeriod]:
    """The quarters of the US universe in the range, with their top N members. The first period starts at the range
    start, in the last quarter that starts at or before it. Empty when no quarter covers the range."""
    quarter_starts = await read_us_universe_quarter_starts(database_url=database_url, end_utc=time_range.end_utc)
    covered = [start_utc for start_utc in quarter_starts if start_utc <= time_range.start_utc]
    if not covered:
        return []
    periods: list[UniversePeriod] = []
    for quarter_start_utc in [covered[-1], *(start for start in quarter_starts if start > time_range.start_utc)]:
        members = await read_us_universe_members(
            database_url=database_url, quarter_start_utc=quarter_start_utc, top_n=top_n
        )
        periods.append(
            UniversePeriod(
                start_utc=max(quarter_start_utc, time_range.start_utc),
                members=[member.instrument for member in members],
            )
        )
    return periods


def describe_missing_universe(time_range: TimeRange) -> str:
    return (
        f"No US universe data covers the range from {time_range.start_utc:%Y-%m-%d}. The US universe starts at the"
        " first quarter with saved members (us_universe_member)."
    )


def find_member_ranges(periods: list[UniversePeriod], end_utc: datetime) -> dict[Instrument, list[TimeRange]]:
    """The time ranges in which each instrument is a member. Periods that follow each other make one range."""
    member_ranges: dict[Instrument, list[TimeRange]] = {}
    for index, period in enumerate(periods):
        period_end_utc = periods[index + 1].start_utc if index + 1 < len(periods) else end_utc
        for member in period.members:
            ranges = member_ranges.setdefault(member, [])
            if ranges and ranges[-1].end_utc == period.start_utc:
                ranges[-1] = TimeRange(start_utc=ranges[-1].start_utc, end_utc=period_end_utc)
            else:
                ranges.append(TimeRange(start_utc=period.start_utc, end_utc=period_end_utc))
    return member_ranges


def describe_missing_universe_bars(request: BacktestRequest) -> str:
    time_range = request.time_range
    return (
        f"There are no saved {request.bar_period.label} bars of a universe member from"
        f" {time_range.start_utc:%Y-%m-%d %H:%M} UTC to {time_range.end_utc:%Y-%m-%d %H:%M} UTC."
        " A multi-instrument backtest needs at least one saved bar of one member in its universe periods."
    )


async def check_universe_bars(
    *, database_url: str, request: BacktestRequest, periods: list[UniversePeriod], source_order: list[BarSource]
) -> str | None:
    """None when one member has one saved bar in a period in which it is a member (section 10.10.8)."""
    for member, ranges in find_member_ranges(periods, request.time_range.end_utc).items():
        for time_range in ranges:
            bar_request = BarRequest(instrument=member, bar_period=request.bar_period, time_range=time_range)
            if await has_saved_bars(database_url=database_url, bar_request=bar_request, source_order=source_order):
                return None
    return describe_missing_universe_bars(request)


def find_universe_look_back_length(bar_period: BarPeriod, single_look_back: timedelta) -> timedelta:
    """At least 1 year for 1-day bars. 1-hour bars use the look-back of a single-instrument backtest (section
    10.10.8). A longer look-back of the strategy version (#164) also applies."""
    if bar_period == BarPeriod.ONE_DAY:
        return max(ONE_DAY_UNIVERSE_LOOK_BACK, single_look_back)
    return single_look_back


@dataclass(frozen=True)
class MemberBars:
    """The bars of one member in its universe periods, and its look-back bars before the start of each range."""

    instrument: Instrument
    bars: list[Bar]
    look_back_bars: list[Bar]


@dataclass(frozen=True)
class UniverseBars:
    members: list[MemberBars]
    bar_count_by_source: dict[BarSource, int]


async def read_universe_bars(
    *,
    database_url: str,
    request: BacktestRequest,
    periods: list[UniversePeriod],
    source_order: list[BarSource],
    look_back_length: timedelta,
) -> UniverseBars:
    """Reads the bars of each member only for the periods in which it is a member, plus the look-back bars before
    each range of periods (section 10.10.1)."""
    bar_count_by_source = dict.fromkeys(source_order, 0)
    members: list[MemberBars] = []
    for member, ranges in find_member_ranges(periods, request.time_range.end_utc).items():
        bars: list[Bar] = []
        look_back_by_start: dict[datetime, Bar] = {}
        for time_range in ranges:
            saved = await read_saved_bars(
                database_url=database_url,
                bar_request=BarRequest(instrument=member, bar_period=request.bar_period, time_range=time_range),
                source_order=source_order,
            )
            bars.extend(saved.bars)
            for bar_source, count in saved.bar_counts.items():
                bar_count_by_source[bar_source] = bar_count_by_source.get(bar_source, 0) + count
            look_back = await read_saved_bars(
                database_url=database_url,
                bar_request=BarRequest(
                    instrument=member,
                    bar_period=request.bar_period,
                    time_range=TimeRange(
                        start_utc=time_range.start_utc - look_back_length, end_utc=time_range.start_utc
                    ),
                ),
                source_order=source_order,
            )
            look_back_by_start.update((bar.start_utc, bar) for bar in look_back.bars)
        members.append(
            MemberBars(
                instrument=member,
                bars=bars,
                look_back_bars=[look_back_by_start[start_utc] for start_utc in sorted(look_back_by_start)],
            )
        )
    return UniverseBars(members=members, bar_count_by_source=bar_count_by_source)
