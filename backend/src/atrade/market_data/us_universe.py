"""Quarterly US universe: the 500 common stocks with the highest average daily trading value in the 63 trading days
before the first trading day of the quarter (docs/architecture/market_data.md section 8.9).

The calculation reads databento_bar only. The source order does not apply to it. A day of the window is a day with
Databento daily bars. Trading value = close × volume. The average divides the sum by 63, so a day without a bar of
the instrument counts as 0.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import LiteralString

import psycopg

from atrade.foundation.instrument import Instrument
from atrade.market_data.us_etf_symbols import US_ETF_SYMBOLS
from atrade.market_data.us_trading_days import (
    find_first_trading_day_of_quarter,
    find_previous_trading_day,
    find_quarter_first_day,
)

WINDOW_TRADING_DAYS = 63
MEMBER_COUNT = 500
# The first quarter with a full 63-day window after the Databento start 2018-05-01 (section 8.14).
FIRST_QUARTER_DAY = date(2018, 10, 1)
QUARTER_MONTHS = 3

SELECT_WINDOW_DAYS: LiteralString = """
    SELECT DISTINCT start_utc FROM databento_bar
    WHERE currency = 'USD' AND bar_period = '1-DAY' AND start_utc <= %(last_ranking_day_utc)s
    ORDER BY start_utc DESC
    LIMIT %(day_count)s
"""

INSERT_MEMBERS: LiteralString = """
    INSERT INTO us_universe_member (
        quarter_start_utc, rank, symbol, exchange, currency, average_trading_value, last_ranking_day_utc
    )
    SELECT %(quarter_start_utc)s, row_number() OVER (ORDER BY average_trading_value DESC, symbol, exchange),
        symbol, exchange, currency, average_trading_value, %(last_day_utc)s
    FROM (
        SELECT symbol, exchange, currency, sum(close * volume) / %(day_count)s AS average_trading_value
        FROM databento_bar
        WHERE currency = 'USD' AND bar_period = '1-DAY'
            AND start_utc >= %(first_day_utc)s AND start_utc <= %(last_day_utc)s
            AND NOT symbol = ANY(%(etf_symbols)s)
        GROUP BY symbol, exchange, currency
        ORDER BY average_trading_value DESC, symbol, exchange
        LIMIT %(member_count)s
    ) AS ranked
"""

SELECT_MEMBERS: LiteralString = """
    SELECT quarter_start_utc, rank, symbol, exchange, currency, average_trading_value, last_ranking_day_utc
    FROM us_universe_member
    WHERE quarter_start_utc = %(quarter_start_utc)s AND rank <= %(top_n)s
    ORDER BY rank
"""

HAS_MEMBERS: LiteralString = "SELECT EXISTS (SELECT 1 FROM us_universe_member WHERE quarter_start_utc = %s)"

SELECT_LAST_BAR_DAY: LiteralString = """
    SELECT max(start_utc) FROM databento_bar WHERE currency = 'USD' AND bar_period = '1-DAY'
"""


class UsUniverseCalculationError(Exception):
    """The calculation saves nothing, for example because the window has less than 63 trading days."""


@dataclass(frozen=True)
class UsUniverseMember:
    quarter_start_utc: datetime
    rank: int
    instrument: Instrument
    average_trading_value: Decimal
    last_ranking_day_utc: datetime


def to_utc_day(day: date) -> datetime:
    return datetime.combine(day, time(), tzinfo=UTC)


def has_us_universe(connection: psycopg.Connection, quarter_start_utc: datetime) -> bool:
    row = connection.execute(HAS_MEMBERS, (quarter_start_utc,)).fetchone()
    return row is not None and bool(row[0])


def insert_members(connection: psycopg.Connection, quarter_start_utc: datetime, last_ranking_day: date) -> None:
    rows = connection.execute(
        SELECT_WINDOW_DAYS, {"last_ranking_day_utc": to_utc_day(last_ranking_day), "day_count": WINDOW_TRADING_DAYS}
    ).fetchall()
    window_days: list[datetime] = [row[0] for row in rows]
    if len(window_days) < WINDOW_TRADING_DAYS:
        message = (
            f"The universe of {quarter_start_utc:%Y-%m-%d} needs {WINDOW_TRADING_DAYS} trading days of Databento"
            f" daily bars up to {last_ranking_day}. databento_bar has {len(window_days)} trading days."
        )
        raise UsUniverseCalculationError(message)
    connection.execute(
        INSERT_MEMBERS,
        {
            "quarter_start_utc": quarter_start_utc,
            # The actual last day: the last day with bars, which can be earlier than `last_ranking_day`.
            "last_day_utc": window_days[0],
            "first_day_utc": window_days[-1],
            "day_count": WINDOW_TRADING_DAYS,
            "etf_symbols": sorted(US_ETF_SYMBOLS),
            "member_count": MEMBER_COUNT,
        },
    )


def save_us_universe(*, database_url: str, quarter_start_utc: datetime, last_ranking_day: date) -> None:
    """Calculates the members of the quarter from the 63 trading days that end on `last_ranking_day` or before it,
    and saves them in one transaction. The new members replace saved members of the quarter."""
    with psycopg.connect(database_url) as connection, connection.transaction():
        connection.execute("DELETE FROM us_universe_member WHERE quarter_start_utc = %s", (quarter_start_utc,))
        insert_members(connection, quarter_start_utc, last_ranking_day)


def find_next_quarter_day(day: date) -> date:
    month = day.month + QUARTER_MONTHS
    return date(day.year + (month - 1) // 12, (month - 1) % 12 + 1, 1)


def calculate_us_universe_history(*, database_url: str) -> int:
    """Calculates each quarter from 2018-10-01 that has no members yet and a Databento bar on its previous trading
    day. A saved quarter does not change: the quarterly update can have used an earlier window. Returns the number
    of calculated quarters."""
    calculated_count = 0
    with psycopg.connect(database_url) as connection, connection.transaction():
        row = connection.execute(SELECT_LAST_BAR_DAY).fetchone()
        last_bar_utc: datetime | None = None if row is None else row[0]
        quarter_day = FIRST_QUARTER_DAY
        while last_bar_utc is not None:
            first_trading_day = find_first_trading_day_of_quarter(find_quarter_first_day(quarter_day))
            last_ranking_day = find_previous_trading_day(first_trading_day)
            if to_utc_day(last_ranking_day) > last_bar_utc:
                break
            quarter_start_utc = to_utc_day(first_trading_day)
            if not has_us_universe(connection, quarter_start_utc):
                insert_members(connection, quarter_start_utc, last_ranking_day)
                calculated_count += 1
            quarter_day = find_next_quarter_day(quarter_day)
    return calculated_count


async def read_us_universe_members(
    *, database_url: str, quarter_start_utc: datetime, top_n: int
) -> list[UsUniverseMember]:
    """The members with `rank` ≤ `top_n` of the quarter that starts at `quarter_start_utc`, by rank."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        cursor = await connection.execute(SELECT_MEMBERS, {"quarter_start_utc": quarter_start_utc, "top_n": top_n})
        rows = await cursor.fetchall()
    return [
        UsUniverseMember(
            quarter_start_utc=row[0],
            rank=row[1],
            instrument=Instrument(symbol=row[2], exchange=row[3], currency=row[4]),
            average_trading_value=row[5],
            last_ranking_day_utc=row[6],
        )
        for row in rows
    ]
