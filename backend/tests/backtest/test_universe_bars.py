"""The bars that the child reads for a multi-instrument backtest: each member only in its universe periods, plus the
look-back bars before each range of periods (docs/architecture/backtest.md section 10.10.1)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import psycopg
import pytest

from atrade.backtest.backtest_store import BacktestRequest, BacktestUniverse, UniversePeriod
from atrade.backtest.backtest_universe import ONE_DAY_UNIVERSE_LOOK_BACK, find_member_ranges, read_universe_bars
from atrade.backtest.universe_engine_run import UniverseRun, make_universe_updates
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarSource
from tests.backtest.universe_data import (
    AAA,
    BBB,
    CCC,
    FIRST_QUARTER_START_UTC,
    RANGE_END_UTC,
    RANGE_START_UTC,
    SECOND_QUARTER_START_UTC,
    save_daily_bars,
)

PERIODS = [
    UniversePeriod(start_utc=RANGE_START_UTC, members=[AAA, BBB]),
    UniversePeriod(start_utc=SECOND_QUARTER_START_UTC, members=[BBB, CCC]),
]
REQUEST = BacktestRequest(
    strategy_version_id=1,
    instrument=None,
    bar_period=BarPeriod.ONE_DAY,
    time_range=TimeRange(start_utc=RANGE_START_UTC, end_utc=RANGE_END_UTC),
    paper_capital_usd=Decimal(100000),
    universe=BacktestUniverse(kind="rule", currency="USD", top_n=2),
)


def test_periods_that_follow_each_other_make_one_member_range() -> None:
    assert find_member_ranges(PERIODS, RANGE_END_UTC) == {
        AAA: [TimeRange(RANGE_START_UTC, SECOND_QUARTER_START_UTC)],
        BBB: [TimeRange(RANGE_START_UTC, RANGE_END_UTC)],
        CCC: [TimeRange(SECOND_QUARTER_START_UTC, RANGE_END_UTC)],
    }


def test_a_member_that_comes_back_has_2_ranges() -> None:
    third_start_utc = datetime(2026, 4, 15, tzinfo=UTC)
    periods = [*PERIODS, UniversePeriod(start_utc=third_start_utc, members=[AAA])]

    assert find_member_ranges(periods, RANGE_END_UTC)[AAA] == [
        TimeRange(RANGE_START_UTC, SECOND_QUARTER_START_UTC),
        TimeRange(third_start_utc, RANGE_END_UTC),
    ]


@pytest.mark.anyio
async def test_reads_each_member_only_in_its_periods_plus_1_year_of_look_back_bars(database_url: str) -> None:
    for instrument in (AAA, BBB, CCC):
        save_daily_bars(database_url, instrument, FIRST_QUARTER_START_UTC - timedelta(days=800), RANGE_END_UTC)

    universe_bars = await read_universe_bars(
        database_url=database_url,
        request=REQUEST,
        periods=PERIODS,
        source_order=[BarSource.IBKR, BarSource.DATABENTO],
        look_back_length=ONE_DAY_UNIVERSE_LOOK_BACK,
    )

    spans = {
        member.instrument.symbol: (
            member.bars[0].start_utc,
            member.bars[-1].start_utc,
            member.look_back_bars[0].start_utc,
            member.look_back_bars[-1].start_utc,
        )
        for member in universe_bars.members
    }
    last_day = timedelta(days=1)
    assert spans == {
        "AAA": (
            RANGE_START_UTC,
            SECOND_QUARTER_START_UTC - last_day,
            RANGE_START_UTC - timedelta(days=365),
            RANGE_START_UTC - last_day,
        ),
        "BBB": (
            RANGE_START_UTC,
            RANGE_END_UTC - last_day,
            RANGE_START_UTC - timedelta(days=365),
            RANGE_START_UTC - last_day,
        ),
        "CCC": (
            SECOND_QUARTER_START_UTC,
            RANGE_END_UTC - last_day,
            SECOND_QUARTER_START_UTC - timedelta(days=365),
            SECOND_QUARTER_START_UTC - last_day,
        ),
    }
    # The bar counts are the bars of the periods, without the look-back bars.
    # AAA 58 days (2026-02-02 to 2026-04-01), BBB 88 days, CCC 30 days.
    assert universe_bars.bar_count_by_source == {BarSource.IBKR: 58 + 88 + 30, BarSource.DATABENTO: 0}


HON_NYSE = Instrument(symbol="HON", exchange="NYSE", currency="USD")
HON_NASDAQ = Instrument(symbol="HON", exchange="NASDAQ", currency="USD")


@pytest.mark.anyio
async def test_a_listing_move_inside_the_range_gives_one_member_with_all_bars_on_the_last_exchange(
    database_url: str,
) -> None:
    move_utc = RANGE_START_UTC + timedelta(days=30)
    look_back_start_utc = RANGE_START_UTC - timedelta(days=10)
    save_daily_bars(database_url, HON_NYSE, look_back_start_utc, move_utc)
    save_daily_bars(database_url, HON_NASDAQ, move_utc, RANGE_END_UTC)

    universe_bars = await read_universe_bars(
        database_url=database_url,
        request=REQUEST,
        periods=[UniversePeriod(start_utc=RANGE_START_UTC, members=[HON_NYSE, HON_NASDAQ])],
        source_order=[BarSource.IBKR],
        look_back_length=ONE_DAY_UNIVERSE_LOOK_BACK,
    )

    member = universe_bars.members[0]
    assert [item.instrument for item in universe_bars.members] == [HON_NASDAQ]
    assert member.bars[0].start_utc == RANGE_START_UTC
    assert member.bars[-1].start_utc == RANGE_END_UTC - timedelta(days=1)
    assert len(member.bars) == (RANGE_END_UTC - RANGE_START_UTC).days
    assert member.open_bars == member.bars
    assert len(member.look_back_bars) == 10


def test_a_universe_update_names_a_symbol_of_2_listings_one_time(monkeypatch: pytest.MonkeyPatch) -> None:
    names: list[list[str]] = []
    monkeypatch.setattr(
        "atrade.backtest.universe_engine_run.make_universe_update",
        lambda _start_utc, bar_types: names.append(bar_types),  # pyright: ignore[reportUnknownLambdaType, reportUnknownArgumentType, reportUnknownMemberType] readability-exception: a test double.
    )

    make_universe_updates(
        UniverseRun(
            code="",
            bar_period=BarPeriod.ONE_DAY,
            currency="USD",
            starting_cash=Decimal(1),
            members=[],
            periods=[UniversePeriod(start_utc=RANGE_START_UTC, members=[HON_NYSE, HON_NASDAQ, AAA])],
        )
    )

    assert [[name.split(".")[0] for name in period_names] for period_names in names] == [["HON", "AAA"]]


@pytest.mark.anyio
async def test_reads_all_members_with_one_connection(database_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression: 2 connections for each range of each member made a universe of 500 members open 1000 connections.
    connect = psycopg.AsyncConnection.connect
    connect_count = 0

    async def count_connect(*args: Any, **kwargs: Any) -> psycopg.AsyncConnection[Any]:
        nonlocal connect_count
        connect_count += 1
        return await connect(*args, **kwargs)

    monkeypatch.setattr(psycopg.AsyncConnection, "connect", count_connect)

    universe_bars = await read_universe_bars(
        database_url=database_url,
        request=REQUEST,
        periods=PERIODS,
        source_order=[BarSource.IBKR, BarSource.DATABENTO],
        look_back_length=ONE_DAY_UNIVERSE_LOOK_BACK,
    )

    assert [member.instrument for member in universe_bars.members] == [AAA, BBB, CCC]
    assert connect_count == 1
