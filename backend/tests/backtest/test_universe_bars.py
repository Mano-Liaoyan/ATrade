"""The bars that the child reads for a multi-instrument backtest: each member only in its universe periods, plus the
look-back bars before each range of periods (docs/architecture/backtest.md section 10.10.1)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from atrade.backtest.backtest_store import BacktestRequest, BacktestUniverse, UniversePeriod
from atrade.backtest.backtest_universe import ONE_DAY_UNIVERSE_LOOK_BACK, find_member_ranges, read_universe_bars
from atrade.foundation.bar import BarPeriod, TimeRange
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
