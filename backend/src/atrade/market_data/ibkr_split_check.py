"""The IBKR stock split check of the Databento instruments that still trade (docs/architecture/market_data.md section
8.8.3). The import records the instruments. A one-time program compares their stored Databento daily closes with the
IBKR daily closes, one instrument at a time, and adjusts the stored Databento bars for each stock split that it finds.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import LiteralString

import psycopg

from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection, GatewayRequestError
from atrade.market_data.daily_bar_summary import update_daily_bar_summaries
from atrade.market_data.stock_split_detection import (
    DailyPrices,
    FoundSplit,
    find_splits_by_detection_rule,
    find_splits_from_ibkr_closes,
)

logger = logging.getLogger(__name__)

# The Databento import and the check both change databento_bar and stock_split. The import holds this lock for its
# whole transaction, the check for the check of 1 instrument. Thus a hourly import that runs at the same time cannot
# adjust a bar 2 times or miss a stock split.
DATABENTO_BAR_LOCK_KEY = 8_008_003
LOCK_DATABENTO_BARS: LiteralString = "SELECT pg_advisory_xact_lock(%(lock_key)s)"

# Databento US data starts on 2018-05-01, so no stored Databento bar starts earlier.
DATABENTO_HISTORY_START_UTC = datetime(2018, 5, 1, tzinfo=UTC)
# A check of new days also reads some checked days, so the close ratio has a day before the first new day. 10
# calendar days hold at least 1 trading day, also after a long holiday.
CHECKED_DAYS_READ_AGAIN = timedelta(days=10)
# The confirmation of a stock split that the IBKR closes show. The detection rule gives no confirmation: the stock
# split waits for the user check of the import (section 8.13.1).
BAR_EVIDENCE = "bar_evidence"

# IBKR limits the historical data requests (https://interactivebrokers.github.io/tws-api/historical_limitations.html).
# The check sends 1 request at a time and waits this time after each instrument.
REQUEST_INTERVAL_SECONDS = 0.5
# After a pacing violation, the check waits, and doubles the wait after each further violation, up to the maximum.
FIRST_PACING_WAIT_SECONDS = 60.0
MAX_PACING_WAIT_SECONDS = 1800.0
PACING_VIOLATION_TEXT = "pacing violation"
# Without a connection to IB Gateway or to IBKR, the check tries again after this time.
CONNECTION_WAIT_SECONDS = 60.0
PROGRESS_LOG_INSTRUMENT_COUNT = 100

UPSERT_SPLIT_CHECK: LiteralString = """
    INSERT INTO ibkr_split_check (symbol, exchange, currency, check_end_utc)
    VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(check_end_utc)s)
    ON CONFLICT (symbol, exchange, currency) DO UPDATE
    SET check_end_utc = greatest(ibkr_split_check.check_end_utc, excluded.check_end_utc)
"""
SELECT_NEXT_INSTRUMENT: LiteralString = """
    SELECT symbol, exchange, currency FROM ibkr_split_check
    WHERE checked_end_utc IS NULL OR checked_end_utc < check_end_utc
    ORDER BY symbol, exchange, currency
    LIMIT 1
"""
COUNT_WAITING_INSTRUMENTS: LiteralString = """
    SELECT count(*) FROM ibkr_split_check WHERE checked_end_utc IS NULL OR checked_end_utc < check_end_utc
"""
SELECT_CHECK_FOR_UPDATE: LiteralString = """
    SELECT check_end_utc, checked_end_utc FROM ibkr_split_check
    WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
    FOR UPDATE
"""
SELECT_STORED_DAILY_PRICES: LiteralString = """
    SELECT start_utc, open, close, volume FROM databento_bar
    WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s AND bar_period = '1-DAY'
        AND start_utc >= %(start_utc)s AND start_utc < %(end_utc)s
    ORDER BY start_utc
"""
INSERT_SPLIT: LiteralString = """
    INSERT INTO stock_split (symbol, exchange, currency, ex_date_utc, split_ratio, source, confirmation, recorded_at_utc)
    VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(ex_date_utc)s, %(split_ratio)s, 'databento_import',
        %(confirmation)s, %(recorded_at_utc)s)
    ON CONFLICT (symbol, exchange, currency, ex_date_utc) DO NOTHING
    RETURNING id
"""
# Only the Databento bars change. The IBKR bars of the instrument are in the IBKR TRADES form already.
ADJUST_STORED_DATABENTO_BARS: LiteralString = """
    UPDATE databento_bar
    SET open = open / %(split_ratio)s, high = high / %(split_ratio)s, low = low / %(split_ratio)s,
        close = close / %(split_ratio)s, volume = volume * %(split_ratio)s
    WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s AND start_utc < %(ex_date_utc)s
"""
SET_CHECKED: LiteralString = """
    UPDATE ibkr_split_check SET checked_end_utc = %(checked_end_utc)s, checked_at_utc = %(checked_at_utc)s
    WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
"""
HAS_WAITING_INSTRUMENT: LiteralString = """
    SELECT EXISTS (
        SELECT FROM ibkr_split_check WHERE currency = %(currency)s
            AND (checked_end_utc IS NULL OR checked_end_utc < check_end_utc)
    )
"""
IS_INSTRUMENT_WAITING: LiteralString = """
    SELECT EXISTS (
        SELECT FROM ibkr_split_check
        WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
            AND (checked_end_utc IS NULL OR checked_end_utc < check_end_utc)
    )
"""

type Wait = Callable[[float], Awaitable[None]]


@dataclass
class IbkrSplitCheckReport:
    checked_instrument_count: int = 0
    # The stock splits of the IBKR closes. They changed the stored bars.
    applied_split_count: int = 0
    # The stock splits of the detection rule, for instruments without IBKR bars. They wait for the user check.
    waiting_split_count: int = 0


def create_key_parameters(instrument: Instrument) -> dict[str, object]:
    return {"symbol": instrument.symbol, "exchange": instrument.exchange, "currency": instrument.currency}


def to_utc_day(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def record_split_checks(connection: psycopg.Connection, instruments: list[Instrument], check_end_utc: datetime) -> None:
    """The import records the instruments that still trade. A second import of the same days changes nothing, so it
    needs no IBKR read again. An import of later days moves the check end, so the check reads only the new days."""
    with connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_SPLIT_CHECK,
            [{**create_key_parameters(instrument), "check_end_utc": check_end_utc} for instrument in instruments],
        )


def lock_databento_bars(connection: psycopg.Connection) -> None:
    connection.execute(LOCK_DATABENTO_BARS, {"lock_key": DATABENTO_BAR_LOCK_KEY})


async def has_pending_split_check(
    connection: psycopg.AsyncConnection, *, instrument: Instrument | None, currency: str
) -> bool:
    """True when the instrument waits for the IBKR stock split check. Without an instrument (a multi-instrument
    backtest): true when any instrument of the currency waits."""
    if instrument is None:
        cursor = await connection.execute(HAS_WAITING_INSTRUMENT, {"currency": currency})
    else:
        cursor = await connection.execute(IS_INSTRUMENT_WAITING, create_key_parameters(instrument))
    row = await cursor.fetchone()
    return row is not None and bool(row[0])


def is_pacing_violation(error: GatewayRequestError) -> bool:
    return PACING_VIOLATION_TEXT in str(error).lower()


def is_retry_needed(error: GatewayRequestError, gateway: GatewayConnection) -> bool:
    """A pacing violation and a lost connection end the check of the instrument, and the check tries it again later.
    Another API error, for example an unknown contract, means that IBKR has no bars of the instrument."""
    return is_pacing_violation(error) or gateway.read_status() != "connected"


async def read_ibkr_closes(
    gateway: GatewayConnection, instrument: Instrument, time_range: TimeRange
) -> dict[date, Decimal] | None:
    """The IBKR daily closes by day. None when IBKR has no bars of the instrument."""
    try:
        bars = await gateway.read_historical_bars(instrument, BarPeriod.ONE_DAY, time_range)
    except GatewayRequestError as error:
        if is_retry_needed(error, gateway):
            raise
        logger.warning("IBKR has no daily bars of %s: %s", instrument, error)
        return None
    if not bars:
        return None
    return {bar.start_utc.date(): bar.close for bar in bars}


async def save_found_splits(
    connection: psycopg.AsyncConnection,
    instrument: Instrument,
    splits: list[FoundSplit],
    *,
    confirmation: str | None,
    recorded_at_utc: datetime,
) -> int:
    """Returns the count of new stock splits. A new stock split with a confirmation changes the stored Databento bars
    before its ex-date. A stock split that is in `stock_split` already keeps its row and changes no bar."""
    new_split_count = 0
    for split in splits:
        parameters = {
            **create_key_parameters(instrument),
            "ex_date_utc": to_utc_day(split.ex_date),
            "split_ratio": split.split_ratio,
        }
        cursor = await connection.execute(
            INSERT_SPLIT, {**parameters, "confirmation": confirmation, "recorded_at_utc": recorded_at_utc}
        )
        if await cursor.fetchone() is None:
            continue
        new_split_count += 1
        if confirmation is not None:
            await connection.execute(ADJUST_STORED_DATABENTO_BARS, parameters)
    return new_split_count


async def read_stored_prices(
    connection: psycopg.AsyncConnection, instrument: Instrument, time_range: TimeRange
) -> list[DailyPrices]:
    cursor = await connection.execute(
        SELECT_STORED_DAILY_PRICES,
        {**create_key_parameters(instrument), "start_utc": time_range.start_utc, "end_utc": time_range.end_utc},
    )
    return [DailyPrices(day=row[0].date(), open=row[1], close=row[2], volume=row[3]) for row in await cursor.fetchall()]


async def check_instrument(
    connection: psycopg.AsyncConnection,
    gateway: GatewayConnection,
    instrument: Instrument,
    report: IbkrSplitCheckReport,
    checked_at_utc: datetime,
) -> None:
    """Checks 1 instrument in 1 transaction. A pacing violation or a lost connection raises GatewayRequestError and
    the transaction saves nothing."""
    async with connection.transaction():
        await connection.execute(LOCK_DATABENTO_BARS, {"lock_key": DATABENTO_BAR_LOCK_KEY})
        cursor = await connection.execute(SELECT_CHECK_FOR_UPDATE, create_key_parameters(instrument))
        row = await cursor.fetchone()
        if row is None:
            return
        check_end_utc: datetime = row[0]
        checked_end_utc: datetime | None = row[1]
        read_start_utc = (
            DATABENTO_HISTORY_START_UTC if checked_end_utc is None else checked_end_utc - CHECKED_DAYS_READ_AGAIN
        )
        prices = await read_stored_prices(connection, instrument, TimeRange(read_start_utc, check_end_utc))
        if prices:
            ibkr_time_range = TimeRange(to_utc_day(prices[0].day), check_end_utc)
            ibkr_closes = await read_ibkr_closes(gateway, instrument, ibkr_time_range)
            if ibkr_closes is None:
                found_splits = find_splits_by_detection_rule(prices)
                report.waiting_split_count += await save_found_splits(
                    connection, instrument, found_splits, confirmation=None, recorded_at_utc=checked_at_utc
                )
            else:
                found_splits = find_splits_from_ibkr_closes(prices, ibkr_closes)
                applied_count = await save_found_splits(
                    connection, instrument, found_splits, confirmation=BAR_EVIDENCE, recorded_at_utc=checked_at_utc
                )
                report.applied_split_count += applied_count
                if applied_count > 0:
                    await update_daily_bar_summaries(connection, [instrument])
        await connection.execute(
            SET_CHECKED,
            {**create_key_parameters(instrument), "checked_end_utc": check_end_utc, "checked_at_utc": checked_at_utc},
        )
    report.checked_instrument_count += 1


async def read_next_instrument(connection: psycopg.AsyncConnection) -> Instrument | None:
    cursor = await connection.execute(SELECT_NEXT_INSTRUMENT)
    row = await cursor.fetchone()
    if row is None:
        return None
    return Instrument(symbol=str(row[0]), exchange=str(row[1]), currency=str(row[2]))


async def count_waiting_instruments(connection: psycopg.AsyncConnection) -> int:
    cursor = await connection.execute(COUNT_WAITING_INSTRUMENTS)
    row = await cursor.fetchone()
    return 0 if row is None else int(row[0])


async def restore_connection(gateway: GatewayConnection) -> None:
    """Without the API connection, connects again. When only the IBKR link is lost, the next request tests it."""
    if gateway.read_status() != "unreachable":
        return
    gateway.disconnect()
    try:
        await gateway.connect()
    except GatewayRequestError as error:
        logger.warning("IB Gateway is not reachable: %s", error)


async def run_ibkr_split_check(
    *, database_url: str, gateway: GatewayConnection, clock: Clock, wait: Wait = asyncio.sleep
) -> IbkrSplitCheckReport:
    """Checks all waiting instruments, one at a time, and returns when none waits. Each instrument saves its result at
    once, so a new run after a stop checks only the instruments that still wait."""
    report = IbkrSplitCheckReport()
    pacing_wait_seconds = FIRST_PACING_WAIT_SECONDS
    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as connection:
        logger.info("%d instruments wait for the IBKR stock split check.", await count_waiting_instruments(connection))
        while (instrument := await read_next_instrument(connection)) is not None:
            try:
                await check_instrument(connection, gateway, instrument, report, clock.read_now_utc())
            except GatewayRequestError as error:
                if is_pacing_violation(error):
                    logger.warning("IBKR pacing violation: %s. Next try in %s seconds.", error, pacing_wait_seconds)
                    await wait(pacing_wait_seconds)
                    pacing_wait_seconds = min(pacing_wait_seconds * 2, MAX_PACING_WAIT_SECONDS)
                    continue
                logger.warning("No IBKR connection: %s. Next try in %s seconds.", error, CONNECTION_WAIT_SECONDS)
                await wait(CONNECTION_WAIT_SECONDS)
                await restore_connection(gateway)
                continue
            pacing_wait_seconds = FIRST_PACING_WAIT_SECONDS
            if report.checked_instrument_count % PROGRESS_LOG_INSTRUMENT_COUNT == 0:
                logger.info(
                    "Checked %d instruments. %d wait.",
                    report.checked_instrument_count,
                    await count_waiting_instruments(connection),
                )
            await wait(REQUEST_INTERVAL_SECONDS)
    return report
