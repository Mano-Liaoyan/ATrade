"""Quarterly US universe: the 500 common stocks with the highest average daily trading value in the 63 trading days
before the quarter start (docs/architecture/market_data.md section 8.9).

Real PostgreSQL with hand-made daily bars in databento_bar.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from atrade.foundation.instrument import Instrument
from atrade.market_data import (
    UsUniverseCalculationError,
    UsUniverseMember,
    calculate_us_universe_history,
    find_first_trading_day_of_quarter,
    find_previous_trading_day,
    read_us_universe_members,
    save_us_universe,
)
from tests.us_universe_bars import create_bar_rows, insert_bar_rows, insert_daily_bars, nasdaq, nyse, utc_day, weekdays

QUARTER_START = date(2025, 1, 2)
QUARTER_START_UTC = datetime(2025, 1, 2, tzinfo=UTC)
LAST_RANKING_DAY = date(2024, 12, 31)


def ranked_symbols(members: list[UsUniverseMember]) -> list[tuple[int, str]]:
    return [(member.rank, member.instrument.symbol) for member in members]


@pytest.mark.parametrize(
    ("day", "first_trading_day"),
    [
        (date(2018, 10, 15), date(2018, 10, 1)),
        # New Year's Day is a holiday.
        (date(2025, 2, 10), date(2025, 1, 2)),
        # 2023-01-01 is a Sunday: the exchanges close on Monday 2023-01-02.
        (date(2023, 3, 31), date(2023, 1, 3)),
        # 2022-01-01 is a Saturday: the exchanges do not close on Friday 2021-12-31.
        (date(2022, 1, 1), date(2022, 1, 3)),
        (date(2024, 5, 1), date(2024, 4, 1)),
    ],
)
def test_the_first_trading_day_of_a_quarter_skips_weekends_and_new_years_day(
    day: date, first_trading_day: date
) -> None:
    assert find_first_trading_day_of_quarter(day) == first_trading_day


@pytest.mark.parametrize(
    ("day", "previous_trading_day"),
    [
        (date(2025, 1, 2), date(2024, 12, 31)),
        # Good Friday 2024-03-29 is a holiday.
        (date(2024, 4, 1), date(2024, 3, 28)),
        (date(2018, 10, 1), date(2018, 9, 28)),
        (date(2023, 1, 3), date(2022, 12, 30)),
    ],
)
def test_the_previous_trading_day_skips_weekends_and_good_friday(day: date, previous_trading_day: date) -> None:
    assert find_previous_trading_day(day) == previous_trading_day


@pytest.mark.anyio
async def test_the_members_are_the_highest_average_trading_values_of_the_last_63_trading_days(
    database_url: str,
) -> None:
    window = weekdays(date(2024, 10, 1), LAST_RANKING_DAY)[-63:]
    # Close x volume: AAPL 200 x 1000, MSFT 100 x 1500, IBM 10 x 500.
    insert_daily_bars(database_url, nasdaq("AAPL"), window, "200", 1000)
    insert_daily_bars(database_url, nasdaq("MSFT"), window, "100", 1500)
    insert_daily_bars(database_url, nyse("IBM"), window, "10", 500)
    # A huge bar before the window and a huge bar on the quarter start do not count.
    insert_daily_bars(database_url, nyse("IBM"), [window[0] - timedelta(days=1), QUARTER_START], "10", 10**9)

    save_us_universe(database_url=database_url, quarter_start_utc=QUARTER_START_UTC, last_ranking_day=LAST_RANKING_DAY)

    members = await read_us_universe_members(database_url=database_url, quarter_start_utc=QUARTER_START_UTC, top_n=500)
    assert ranked_symbols(members) == [(1, "AAPL"), (2, "MSFT"), (3, "IBM")]
    assert members[0] == UsUniverseMember(
        quarter_start_utc=QUARTER_START_UTC,
        rank=1,
        instrument=nasdaq("AAPL"),
        average_trading_value=Decimal(200000),
        last_ranking_day_utc=utc_day(LAST_RANKING_DAY),
    )


@pytest.mark.anyio
async def test_a_day_without_a_bar_counts_as_zero_trading_value(database_url: str) -> None:
    window = weekdays(date(2024, 10, 1), LAST_RANKING_DAY)[-63:]
    insert_daily_bars(database_url, nasdaq("AAPL"), window, "10", 63)
    # A new listing with bars on the last 3 days only: 3 x 100 x 63 / 63 = 300 < 630.
    insert_daily_bars(database_url, nyse("NEW"), window[-3:], "100", 63)

    save_us_universe(database_url=database_url, quarter_start_utc=QUARTER_START_UTC, last_ranking_day=LAST_RANKING_DAY)

    members = await read_us_universe_members(database_url=database_url, quarter_start_utc=QUARTER_START_UTC, top_n=2)
    assert [(member.instrument.symbol, member.average_trading_value) for member in members] == [
        ("AAPL", Decimal(630)),
        ("NEW", Decimal(300)),
    ]


@pytest.mark.anyio
async def test_etfs_are_not_members_and_the_top_n_read_gives_the_first_n_ranks(database_url: str) -> None:
    window = weekdays(date(2024, 10, 1), LAST_RANKING_DAY)[-63:]
    insert_daily_bars(database_url, Instrument(symbol="SPY", exchange="ARCA", currency="USD"), window, "500", 10**6)
    insert_daily_bars(database_url, nasdaq("AAPL"), window, "200", 1000)
    insert_daily_bars(database_url, nasdaq("MSFT"), window, "100", 1500)

    save_us_universe(database_url=database_url, quarter_start_utc=QUARTER_START_UTC, last_ranking_day=LAST_RANKING_DAY)

    members = await read_us_universe_members(database_url=database_url, quarter_start_utc=QUARTER_START_UTC, top_n=1)
    assert ranked_symbols(members) == [(1, "AAPL")]


@pytest.mark.anyio
async def test_the_calculation_reads_databento_bars_only(database_url: str) -> None:
    window = weekdays(date(2024, 10, 1), LAST_RANKING_DAY)[-63:]
    insert_daily_bars(database_url, nasdaq("AAPL"), window, "200", 1000)
    insert_bar_rows(database_url, "ibkr_bar", create_bar_rows(nasdaq("MSFT"), window, "100", 10**6))

    save_us_universe(database_url=database_url, quarter_start_utc=QUARTER_START_UTC, last_ranking_day=LAST_RANKING_DAY)

    members = await read_us_universe_members(database_url=database_url, quarter_start_utc=QUARTER_START_UTC, top_n=500)
    assert ranked_symbols(members) == [(1, "AAPL")]


def test_the_calculation_refuses_a_window_with_less_than_63_trading_days(database_url: str) -> None:
    insert_daily_bars(database_url, nasdaq("AAPL"), weekdays(date(2024, 10, 1), LAST_RANKING_DAY)[-62:], "1", 1)

    with pytest.raises(UsUniverseCalculationError, match="62 trading days"):
        save_us_universe(
            database_url=database_url, quarter_start_utc=QUARTER_START_UTC, last_ranking_day=LAST_RANKING_DAY
        )


def test_the_calculation_refuses_a_window_with_a_gap_in_the_databento_bars(database_url: str) -> None:
    # 62 days at the end of the quarter and 1 old day: 63 days, but the window starts more than 100 days earlier.
    days = [date(2024, 6, 3), *weekdays(date(2024, 10, 1), LAST_RANKING_DAY)[-62:]]
    insert_daily_bars(database_url, nasdaq("AAPL"), days, "1", 1)

    with pytest.raises(UsUniverseCalculationError, match="gap"):
        save_us_universe(
            database_url=database_url, quarter_start_utc=QUARTER_START_UTC, last_ranking_day=LAST_RANKING_DAY
        )


@pytest.mark.anyio
async def test_the_history_keeps_an_instrument_that_stopped_trading_later_in_its_quarter(database_url: str) -> None:
    days = weekdays(date(2018, 5, 1), date(2019, 3, 29))
    insert_daily_bars(database_url, nasdaq("AAPL"), days, "10", 100)
    # GONE has the highest value until 2018-12-31 and no bar after it.
    insert_daily_bars(database_url, nyse("GONE"), [day for day in days if day <= date(2018, 12, 31)], "50", 100)

    quarter_count = calculate_us_universe_history(database_url=database_url)

    # The quarters of 2018-10-01, 2019-01-02, and 2019-04-01. 2019-07-01 needs a bar on 2019-06-28.
    assert quarter_count == 3
    first_quarter = await read_us_universe_members(
        database_url=database_url, quarter_start_utc=datetime(2018, 10, 1, tzinfo=UTC), top_n=500
    )
    assert ranked_symbols(first_quarter) == [(1, "GONE"), (2, "AAPL")]
    assert first_quarter[0].last_ranking_day_utc == datetime(2018, 9, 28, tzinfo=UTC)
    second_quarter = await read_us_universe_members(
        database_url=database_url, quarter_start_utc=datetime(2019, 1, 2, tzinfo=UTC), top_n=500
    )
    assert ranked_symbols(second_quarter) == [(1, "GONE"), (2, "AAPL")]
    third_quarter = await read_us_universe_members(
        database_url=database_url, quarter_start_utc=datetime(2019, 4, 1, tzinfo=UTC), top_n=500
    )
    assert ranked_symbols(third_quarter) == [(1, "AAPL")]


@pytest.mark.anyio
async def test_the_history_does_not_change_a_saved_quarter(database_url: str) -> None:
    days = weekdays(date(2018, 5, 1), date(2018, 9, 28))
    insert_daily_bars(database_url, nasdaq("AAPL"), days, "10", 100)
    first_quarter_utc = datetime(2018, 10, 1, tzinfo=UTC)
    # The quarterly update used the window that ends 1 trading day earlier.
    save_us_universe(database_url=database_url, quarter_start_utc=first_quarter_utc, last_ranking_day=date(2018, 9, 27))

    assert calculate_us_universe_history(database_url=database_url) == 0

    members = await read_us_universe_members(database_url=database_url, quarter_start_utc=first_quarter_utc, top_n=1)
    assert members[0].last_ranking_day_utc == datetime(2018, 9, 27, tzinfo=UTC)
