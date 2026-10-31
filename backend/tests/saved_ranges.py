"""Test helper: records a saved range in ibkr_bar_saved_range for bars that a test inserts directly in ibkr_bar.

Saved bars are read through the saved ranges of the source order (docs/architecture/market_data.md section 8.7.2).
"""

from datetime import UTC, datetime

import psycopg

from atrade.foundation.instrument import Instrument

# Wide enough for all test bars. The bars route does not ask the IBKR fake for a part of this range.
TEST_SAVED_RANGE_START_UTC = datetime(2000, 1, 1, tzinfo=UTC)
TEST_SAVED_RANGE_END_UTC = datetime(2030, 1, 1, tzinfo=UTC)


def save_ibkr_saved_range(
    connection: psycopg.Connection,
    instrument: Instrument,
    bar_period: str,
    start_utc: datetime = TEST_SAVED_RANGE_START_UTC,
    end_utc: datetime = TEST_SAVED_RANGE_END_UTC,
) -> None:
    connection.execute(
        """
        INSERT INTO ibkr_bar_saved_range (symbol, exchange, currency, bar_period, start_utc, end_utc)
        VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, %(start_utc)s, %(end_utc)s)
        """,
        {
            "symbol": instrument.symbol,
            "exchange": instrument.exchange,
            "currency": instrument.currency,
            "bar_period": bar_period,
            "start_utc": start_utc,
            "end_utc": end_utc,
        },
    )
