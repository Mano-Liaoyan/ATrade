"""The point-in-time run of a screen for a backtest universe (docs/architecture/screen.md section 24.9): it uses only
the daily bars that close at or before the date, and its filter values are the daily bar summary of that date."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarRequest, read_daily_bar_summaries, save_received_bars
from atrade.screen import run_screen_at
from tests.screen.test_screen_run_routes import add_to_watchlist, make_definition

AAA = Instrument(symbol="AAA", exchange="NASDAQ", currency="USD")
FIRST_DAY = datetime(2025, 11, 1, tzinfo=UTC)


def at_day(index: int) -> datetime:
    return FIRST_DAY + timedelta(days=index)


async def save_rising_bars(database_url: str, first_index: int, end_index: int) -> None:
    """One daily bar on each day from `first_index` to `end_index` (not included). The close of day i is i + 1, the
    volume 1000 × (i + 1), so the average trading value changes each day."""
    bars = [
        Bar(
            start_utc=at_day(index),
            open=Decimal(index + 1),
            high=Decimal(index + 1),
            low=Decimal(index + 1),
            close=Decimal(index + 1),
            volume=Decimal(1000 * (index + 1)),
        )
        for index in range(first_index, end_index)
    ]
    bar_request = BarRequest(AAA, BarPeriod.ONE_DAY, TimeRange(at_day(first_index), at_day(end_index)))
    await save_received_bars(database_url=database_url, bar_request=bar_request, bars=bars)


@pytest.mark.anyio
@pytest.mark.parametrize(("as_of_index", "passes"), [(30, False), (31, True)])
async def test_a_point_in_time_run_uses_only_the_daily_bars_before_the_date(
    database_url: str, as_of_index: int, passes: bool
) -> None:
    # Bars up to day 59. A run on day 30 sees the bars of days 0 to 29: the last close is 30.
    await save_rising_bars(database_url, 0, 60)
    add_to_watchlist(database_url, AAA)
    definition = make_definition(filters=[{"field": "last_price", "operator": ">", "value": "30"}])

    outcome = await run_screen_at(
        database_url=database_url, market="US", definition=definition, as_of_utc=at_day(as_of_index)
    )

    assert [row.instrument for row in outcome.rows] == ([AAA] if passes else [])
    assert outcome.daily_bars_date == at_day(as_of_index - 1).date()
    if passes:
        # SMA(3) of the closes 29, 30, and 31.
        assert outcome.rows[0].indicator_values == {"SMA(3)": 30.0}


@pytest.mark.anyio
async def test_the_filter_values_of_a_point_in_time_run_are_the_daily_bar_summary_of_that_date(
    database_url: str,
) -> None:
    await save_rising_bars(database_url, 0, 40)
    [summary_at_day_40] = await read_daily_bar_summaries(database_url=database_url, instruments=[AAA])
    # Later bars change the summary. The run on day 40 must give the old values.
    await save_rising_bars(database_url, 40, 60)
    add_to_watchlist(database_url, AAA)

    outcome = await run_screen_at(
        database_url=database_url,
        market="US",
        definition=make_definition(),
        as_of_utc=at_day(40),
    )

    [row] = outcome.rows
    assert row.last_price == summary_at_day_40.last_close == Decimal(40)
    assert row.average_trading_value_20 == summary_at_day_40.average_trading_value_20
    assert row.average_trading_value_20 is not None
