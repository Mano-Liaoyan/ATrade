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
    CREATE TEMPORARY TABLE databento_hourly_record (
        symbol text NOT NULL, start_utc timestamptz NOT NULL,
        open numeric NOT NULL, high numeric NOT NULL, low numeric NOT NULL, close numeric NOT NULL,
        volume numeric NOT NULL
    ) ON COMMIT DROP;
    -- The bars of this import before the symbol links and the stock split adjustment (sections 8.8.3 and 8.8.4).
    CREATE TEMPORARY TABLE databento_import_bar (LIKE databento_bar INCLUDING ALL) ON COMMIT DROP;
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
    INSERT INTO databento_import_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
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
        FROM (
            SELECT symbol, exchange, currency, bar_period, start_utc FROM databento_bar
            UNION ALL
            SELECT symbol, exchange, currency, bar_period, start_utc FROM databento_import_bar
        ) AS earlier_bar
        WHERE currency = 'USD' AND bar_period = '1-DAY' AND start_utc < %(start_utc)s
        ORDER BY symbol, start_utc DESC
    )
"""

INSERT_SUMMARY_BARS: LiteralString = (
    SUMMARY_LISTING
    + """
    INSERT INTO databento_import_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
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

SAVE_IMPORT_BARS: LiteralString = (
    """
    INSERT INTO databento_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
    SELECT symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume FROM databento_import_bar
    """
    + UPSERT_BARS
)

# Symbol change links (section 8.8.4): the last day of the old symbol and the first day of the new symbol are adjacent
# trading days, the last close and the first open differ by 1% or less, and the listing exchange is the same. A symbol
# with more than 1 candidate gets no link.
SELECT_SYMBOL_LINKS: LiteralString = """
    WITH trading_day AS (
        SELECT start_utc, lead(start_utc) OVER (ORDER BY start_utc) AS next_start_utc
        FROM (SELECT DISTINCT start_utc FROM databento_import_bar) AS day
    ), last_bar AS (
        SELECT DISTINCT ON (symbol, exchange) symbol, exchange, start_utc, close
        FROM databento_import_bar ORDER BY symbol, exchange, start_utc DESC
    ), first_bar AS (
        SELECT DISTINCT ON (symbol, exchange) symbol, exchange, start_utc, open
        FROM databento_import_bar ORDER BY symbol, exchange, start_utc
    ), candidate AS (
        SELECT last_bar.symbol AS old_symbol, first_bar.symbol AS new_symbol, last_bar.exchange,
            first_bar.start_utc AS change_start_utc
        FROM last_bar
            JOIN trading_day ON trading_day.start_utc = last_bar.start_utc
            JOIN first_bar ON first_bar.start_utc = trading_day.next_start_utc
                AND first_bar.exchange = last_bar.exchange
        WHERE first_bar.symbol <> last_bar.symbol AND last_bar.close > 0
            AND abs(first_bar.open / last_bar.close - 1) <= 0.01
    )
    SELECT old_symbol, new_symbol, exchange, change_start_utc FROM candidate
    WHERE old_symbol NOT IN (SELECT old_symbol FROM candidate GROUP BY old_symbol HAVING count(*) > 1)
        AND new_symbol NOT IN (SELECT new_symbol FROM candidate GROUP BY new_symbol HAVING count(*) > 1)
    ORDER BY change_start_utc, old_symbol
"""

INSERT_SYMBOL_LINK: LiteralString = """
    INSERT INTO databento_symbol_link (old_symbol, new_symbol, exchange, change_day)
    VALUES (%(old_symbol)s, %(new_symbol)s, %(exchange)s, %(change_day)s)
    ON CONFLICT (old_symbol, new_symbol, exchange, change_day) DO NOTHING
"""

# The import saves all history of the old symbol under the new symbol, the same as IBKR does.
MOVE_TO_NEW_SYMBOL: LiteralString = """
    UPDATE databento_import_bar SET symbol = %(new_symbol)s
    WHERE symbol = %(old_symbol)s AND exchange = %(exchange)s AND start_utc < %(change_start_utc)s
"""

SELECT_LAST_IMPORT_DAY: LiteralString = "SELECT max(start_utc) FROM databento_import_bar"

SELECT_IMPORT_PRICES: LiteralString = """
    SELECT symbol, exchange, currency, start_utc, open, close, volume FROM databento_import_bar
    WHERE bar_period = '1-DAY'
    ORDER BY symbol, exchange, currency, start_utc
"""

INSERT_STOCK_SPLIT: LiteralString = """
    INSERT INTO stock_split (symbol, exchange, currency, ex_date_utc, split_ratio, source, confirmation, recorded_at_utc)
    VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(ex_date_utc)s, %(split_ratio)s, 'databento_import',
        %(confirmation)s, now())
    ON CONFLICT (symbol, exchange, currency, ex_date_utc) DO NOTHING
"""

# The confirmed stock splits change the bars. A stock split that waits for the user check, or that the user rejected,
# does not change them.
SELECT_APPLIED_SPLITS_OF_IMPORT: LiteralString = """
    SELECT symbol, exchange, currency, ex_date_utc, split_ratio FROM stock_split
    WHERE confirmation IN ('both_evidences', 'bar_evidence', 'user_apply', 'import_check')
        AND EXISTS (
            SELECT FROM databento_import_bar AS bar
            WHERE bar.symbol = stock_split.symbol AND bar.exchange = stock_split.exchange
                AND bar.currency = stock_split.currency
        )
    ORDER BY id
"""

ADJUST_IMPORT_BARS: LiteralString = """
    UPDATE databento_import_bar
    SET open = open / %(split_ratio)s, high = high / %(split_ratio)s, low = low / %(split_ratio)s,
        close = close / %(split_ratio)s, volume = volume * %(split_ratio)s
    WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
        AND start_utc < %(ex_date_utc)s
"""
