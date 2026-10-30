"""Helpers of the multi-instrument backtest tests: daily bars of several instruments, the quarterly US universe, and
the start request of a universe backtest (docs/architecture/backtest.md section 10.10)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import psycopg

from atrade.foundation.instrument import Instrument
from tests.saved_ranges import save_ibkr_saved_range

AAA = Instrument(symbol="AAA", exchange="NASDAQ", currency="USD")
BBB = Instrument(symbol="BBB", exchange="NYSE", currency="USD")
CCC = Instrument(symbol="CCC", exchange="ARCA", currency="USD")
FIRST_QUARTER_START_UTC = datetime(2026, 1, 2, tzinfo=UTC)
SECOND_QUARTER_START_UTC = datetime(2026, 4, 1, tzinfo=UTC)
RANGE_START_UTC = datetime(2026, 2, 2, tzinfo=UTC)
RANGE_END_UTC = datetime(2026, 5, 1, tzinfo=UTC)
# The first quarter has AAA and BBB, the second quarter BBB and CCC.
QUARTER_MEMBERS = {FIRST_QUARTER_START_UTC: [AAA, BBB], SECOND_QUARTER_START_UTC: [BBB, CCC]}


def save_daily_bars(database_url: str, instrument: Instrument, start_utc: datetime, end_utc: datetime) -> None:
    """Saves one daily bar on each day from `start_utc` to `end_utc` (not included). The close goes up by 1 each day."""
    day_count = (end_utc - start_utc).days
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.cursor().executemany(
            """
            INSERT INTO ibkr_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES (%(symbol)s, %(exchange)s, %(currency)s, '1-DAY', %(start_utc)s, %(price)s, %(price)s, %(price)s,
                %(price)s, 1000000)
            """,
            [
                {
                    "symbol": instrument.symbol,
                    "exchange": instrument.exchange,
                    "currency": instrument.currency,
                    "start_utc": start_utc + timedelta(days=index),
                    "price": Decimal(100 + index),
                }
                for index in range(day_count)
            ],
        )
        save_ibkr_saved_range(connection, instrument, "1-DAY")


def save_us_universe_quarters(database_url: str, quarter_members: dict[datetime, list[Instrument]]) -> None:
    """Saves the members of each quarter in us_universe_member, ranked in the list order."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.cursor().executemany(
            """
            INSERT INTO us_universe_member (quarter_start_utc, rank, symbol, exchange, currency,
                average_trading_value, last_ranking_day_utc)
            VALUES (%(quarter_start_utc)s, %(rank)s, %(symbol)s, %(exchange)s, %(currency)s, 1000000,
                %(quarter_start_utc)s)
            """,
            [
                {
                    "quarter_start_utc": quarter_start_utc,
                    "rank": rank,
                    "symbol": instrument.symbol,
                    "exchange": instrument.exchange,
                    "currency": instrument.currency,
                }
                for quarter_start_utc, members in quarter_members.items()
                for rank, instrument in enumerate(members, start=1)
            ],
        )


def save_universe_test_data(database_url: str) -> None:
    """The 2 quarters of QUARTER_MEMBERS, and daily bars of all 3 instruments for a year before the range and the
    range."""
    save_us_universe_quarters(database_url, QUARTER_MEMBERS)
    for instrument in (AAA, BBB, CCC):
        save_daily_bars(database_url, instrument, RANGE_START_UTC - timedelta(days=400), RANGE_END_UTC)


def make_universe_request(strategy_version_id: int, **universe: object) -> dict[str, object]:
    return {
        "strategy_version_id": strategy_version_id,
        "bar_period": "1-DAY",
        "start_utc": RANGE_START_UTC.isoformat(),
        "end_utc": RANGE_END_UTC.isoformat(),
        "paper_capital_usd": "100000",
        **universe,
    }


def to_instrument_body(instrument: Instrument) -> dict[str, str]:
    return {"symbol": instrument.symbol, "exchange": instrument.exchange, "currency": instrument.currency}
