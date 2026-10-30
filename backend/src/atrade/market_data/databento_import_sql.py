"""SQL of the Databento import (docs/architecture/market_data.md section 8.8.2).

The temporary tables hold the records of the DBN files. They are dropped at the end of the import transaction.
"""

from typing import LiteralString

CREATE_TEMPORARY_TABLES: LiteralString = """
    CREATE TEMPORARY TABLE databento_daily_record (
        dataset text NOT NULL, symbol text NOT NULL, trading_day date NOT NULL,
        open numeric NOT NULL, high numeric NOT NULL, low numeric NOT NULL, close numeric NOT NULL,
        volume numeric NOT NULL
    ) ON COMMIT DROP;
    CREATE TEMPORARY TABLE databento_statistic (
        dataset text NOT NULL, symbol text NOT NULL, trading_day date NOT NULL, stat_type integer NOT NULL,
        price numeric NOT NULL, ts_recv bigint NOT NULL
    ) ON COMMIT DROP;
"""

COPY_DAILY_RECORDS: LiteralString = """
    COPY databento_daily_record (dataset, symbol, trading_day, open, high, low, close, volume) FROM STDIN
"""

COPY_STATISTICS: LiteralString = """
    COPY databento_statistic (dataset, symbol, trading_day, stat_type, price, ts_recv) FROM STDIN
"""

UPSERT_BARS: LiteralString = """
    ON CONFLICT (symbol, exchange, currency, bar_period, start_utc) DO UPDATE SET
        open = excluded.open, high = excluded.high, low = excluded.low,
        close = excluded.close, volume = excluded.volume
"""

# Before 2024-07-01. Open and close: the latest official open (stat_type 1) and close (stat_type 11) of the listing
# exchange, the exchange whose statistics have the prices. High, low, and volume: both exchanges together.
INSERT_HISTORY_BARS: LiteralString = (
    """
    WITH official_price AS (
        SELECT DISTINCT ON (dataset, symbol, trading_day, stat_type) dataset, symbol, trading_day, stat_type, price
        FROM databento_statistic
        ORDER BY dataset, symbol, trading_day, stat_type, ts_recv DESC
    ), listing AS (
        SELECT DISTINCT ON (official_close.symbol, official_close.trading_day)
            official_close.dataset, official_close.symbol, official_close.trading_day,
            official_open.price AS open, official_close.price AS close
        FROM official_price AS official_close
            JOIN official_price AS official_open ON official_open.dataset = official_close.dataset
                AND official_open.symbol = official_close.symbol
                AND official_open.trading_day = official_close.trading_day AND official_open.stat_type = 1
        WHERE official_close.stat_type = 11
        ORDER BY official_close.symbol, official_close.trading_day, official_close.dataset
    ), both_exchanges AS (
        SELECT symbol, trading_day, max(high) AS high, min(low) AS low, sum(volume) AS volume
        FROM databento_daily_record
        WHERE dataset IN ('XNAS.ITCH', 'XNYS.PILLAR')
        GROUP BY symbol, trading_day
    )
    INSERT INTO databento_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
    SELECT listing.symbol, CASE listing.dataset WHEN 'XNAS.ITCH' THEN 'NASDAQ' ELSE 'NYSE' END, 'USD', '1-DAY',
        listing.trading_day::timestamp AT TIME ZONE 'UTC',
        listing.open, both_exchanges.high, both_exchanges.low, listing.close, both_exchanges.volume
    FROM listing JOIN both_exchanges USING (symbol, trading_day)
    WHERE listing.trading_day::timestamp AT TIME ZONE 'UTC' >= %(start_utc)s
        AND listing.trading_day::timestamp AT TIME ZONE 'UTC' < %(end_utc)s
    """
    + UPSERT_BARS
)

SELECT_SYMBOLS_WITHOUT_OFFICIAL_CLOSE: LiteralString = """
    SELECT DISTINCT symbol FROM databento_daily_record
    WHERE dataset IN ('XNAS.ITCH', 'XNYS.PILLAR')
        AND trading_day::timestamp AT TIME ZONE 'UTC' >= %(start_utc)s
        AND trading_day::timestamp AT TIME ZONE 'UTC' < %(end_utc)s
    EXCEPT
    SELECT symbol FROM databento_statistic WHERE stat_type = 11
    ORDER BY symbol
"""

# The listing exchange of a symbol from 2024-07-01 is the exchange of its latest Databento daily bar before the
# EQUS.SUMMARY range. The purchase has no statistics from that day (docs/architecture.md section 22).
SUMMARY_LISTING: LiteralString = """
    WITH summary_listing AS (
        SELECT DISTINCT ON (symbol) symbol, exchange
        FROM databento_bar
        WHERE currency = 'USD' AND bar_period = '1-DAY' AND start_utc < %(start_utc)s
        ORDER BY symbol, start_utc DESC
    )
"""

INSERT_SUMMARY_BARS: LiteralString = (
    SUMMARY_LISTING
    + """
    INSERT INTO databento_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
    SELECT summary.symbol, summary_listing.exchange, 'USD', '1-DAY', summary.trading_day::timestamp AT TIME ZONE 'UTC',
        summary.open, summary.high, summary.low, summary.close, summary.volume
    FROM databento_daily_record AS summary JOIN summary_listing USING (symbol)
    WHERE summary.dataset = 'EQUS.SUMMARY'
        AND summary.trading_day::timestamp AT TIME ZONE 'UTC' >= %(start_utc)s
        AND summary.trading_day::timestamp AT TIME ZONE 'UTC' < %(end_utc)s
    """
    + UPSERT_BARS
)

SELECT_SYMBOLS_WITHOUT_LISTING_EXCHANGE: LiteralString = (
    SUMMARY_LISTING
    + """
    SELECT DISTINCT summary.symbol FROM databento_daily_record AS summary
    WHERE summary.dataset = 'EQUS.SUMMARY'
        AND summary.trading_day::timestamp AT TIME ZONE 'UTC' >= %(start_utc)s
        AND summary.trading_day::timestamp AT TIME ZONE 'UTC' < %(end_utc)s
        AND summary.symbol NOT IN (SELECT symbol FROM summary_listing)
    ORDER BY summary.symbol
    """
)

SELECT_INSTRUMENTS: LiteralString = """
    SELECT DISTINCT symbol, exchange, currency FROM databento_bar
    WHERE bar_period = '1-DAY' AND start_utc >= %(start_utc)s AND start_utc < %(end_utc)s
    ORDER BY symbol, exchange, currency
"""
