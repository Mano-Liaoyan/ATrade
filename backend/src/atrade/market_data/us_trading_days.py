"""The US trading days at the start and the end of a quarter (docs/architecture/market_data.md section 8.9).

The only US exchange holidays within 3 days of a quarter start are New Year's Day and Good Friday. Thus this small
calendar is correct for "the first trading day of the quarter" and "the previous trading day" before it. It is not a
full trading calendar: the 63-day window counts the days with Databento daily bars.
"""

from datetime import date, timedelta

QUARTER_FIRST_MONTHS = (1, 4, 7, 10)
SATURDAY = 5
SUNDAY = 6


def find_easter_sunday(year: int) -> date:
    """The Gregorian Easter Sunday (the anonymous Gregorian algorithm)."""
    golden = year % 19
    century, year_of_century = divmod(year, 100)
    leap_century, century_remainder = divmod(century, 4)
    correction = (century + 8) // 25
    moon_correction = (century - correction + 1) // 3
    epact = (19 * golden + century - leap_century - moon_correction + 15) % 30
    leap_year, year_remainder = divmod(year_of_century, 4)
    weekday_offset = (32 + 2 * century_remainder + 2 * leap_year - epact - year_remainder) % 7
    month_offset = (golden + 11 * epact + 22 * weekday_offset) // 451
    month, day = divmod(epact + weekday_offset - 7 * month_offset + 114, 31)
    return date(year, month, day + 1)


def is_quarter_edge_holiday(day: date) -> bool:
    """New Year's Day (Monday 2 January when 1 January is a Sunday) or Good Friday. A Saturday New Year's Day has
    no holiday on Friday 31 December."""
    new_years_day = date(day.year, 1, 1)
    observed_new_years_day = new_years_day + timedelta(days=1) if new_years_day.weekday() == SUNDAY else new_years_day
    good_friday = find_easter_sunday(day.year) - timedelta(days=2)
    return day in {observed_new_years_day, good_friday}


def is_trading_day(day: date) -> bool:
    return day.weekday() < SATURDAY and not is_quarter_edge_holiday(day)


def find_quarter_first_day(day: date) -> date:
    """The first calendar day of the quarter of `day`."""
    return date(day.year, QUARTER_FIRST_MONTHS[(day.month - 1) // 3], 1)


def find_previous_quarter_first_day(day: date) -> date:
    return find_quarter_first_day(find_quarter_first_day(day) - timedelta(days=1))


def find_first_trading_day_of_quarter(day: date) -> date:
    """The first trading day of the quarter of `day`."""
    first_trading_day = find_quarter_first_day(day)
    while not is_trading_day(first_trading_day):
        first_trading_day += timedelta(days=1)
    return first_trading_day


def find_previous_trading_day(day: date) -> date:
    """The trading day before `day`. Correct only near a quarter edge."""
    previous_day = day - timedelta(days=1)
    while not is_trading_day(previous_day):
        previous_day -= timedelta(days=1)
    return previous_day
