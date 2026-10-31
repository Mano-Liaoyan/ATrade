"""Evidence A of a stock split: each read of bars from IBKR also reads the daily bar of 1 stored day again
(docs/architecture/market_data.md sections 8.11 and 8.13.2).

IBKR adjusts its TRADES bars for stock splits, so the stored close divided by the new IBKR close of the same day is the
split ratio. A candidate is a `stock_split` row with the source `ibkr_evidence` and no confirmation: the stock split
check reads it and confirms it (forward_test.md section 12.22).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import LiteralString

import psycopg

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection, GatewayRequestError
from atrade.market_data.daily_bar_summary import select_last_daily_bars
from atrade.market_data.stock_split_detection import RATIO_STEP_TOLERANCE, find_split_ratio, to_decimal

logger = logging.getLogger(__name__)

ONE_DAY = timedelta(days=1)

INSERT_CANDIDATE: LiteralString = """
    INSERT INTO stock_split (
        symbol, exchange, currency, ex_date_utc, split_ratio, source, confirmation, recorded_at_utc
    )
    VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(ex_date_utc)s, %(split_ratio)s, 'ibkr_evidence', NULL,
        %(recorded_at_utc)s)
    ON CONFLICT (symbol, exchange, currency, ex_date_utc) DO NOTHING
"""
SELECT_CANDIDATES: LiteralString = """
    SELECT id, symbol, exchange, currency, ex_date_utc, split_ratio FROM stock_split
    WHERE source = 'ibkr_evidence' AND confirmation IS NULL
    ORDER BY symbol, exchange, currency, ex_date_utc
"""
# The stock splits of all sources that wait for a confirmation: the stored bars before their ex-dates are in the old
# form. A Databento import split waits for the import check (section 8.13.2).
SELECT_WAITING_SPLITS: LiteralString = """
    SELECT ex_date_utc, split_ratio FROM stock_split
    WHERE confirmation IS NULL
        AND symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
"""


@dataclass(frozen=True)
class StockSplitCandidate:
    """A stock split that evidence A found and that is not confirmed yet."""

    id: int
    instrument: Instrument
    ex_date_utc: datetime
    split_ratio: Decimal


def find_evidence_ratio(stored_close: Decimal, ibkr_close: Decimal) -> Decimal | None:
    """The split ratio of the 2 closes of 1 day, or None when the ratio is 1. The IBKR close and the official close of
    the Databento import can differ by about 1%, so a ratio within `RATIO_STEP_TOLERANCE` of 1 is 1."""
    if stored_close <= 0 or ibkr_close <= 0:
        return None
    raw_ratio = stored_close / ibkr_close
    if abs(raw_ratio - 1) <= RATIO_STEP_TOLERANCE:
        return None
    return to_decimal(find_split_ratio(raw_ratio))


async def check_evidence_a(
    connection: psycopg.AsyncConnection,
    gateway_connection: GatewayConnection,
    instrument: Instrument,
    recorded_at_utc: datetime,
) -> None:
    """Reads the last stored daily bar of the instrument from IBKR again, and records a candidate when the closes show a
    stock split. The stored bars end on the evidence day, so the ex-date is the next day: the bars of later days come
    from IBKR in the new form. Call it before the new bars are saved."""
    stored_bars = (await select_last_daily_bars(connection, [instrument], None, 1))[instrument]
    if not stored_bars:
        return
    stored_bar = stored_bars[-1]
    try:
        ibkr_bars = await gateway_connection.read_historical_bars(
            instrument, BarPeriod.ONE_DAY, TimeRange(stored_bar.start_utc, stored_bar.start_utc + ONE_DAY)
        )
    except GatewayRequestError:
        # The read of the missing bars continues without evidence A.
        logger.exception("The bars route did not read the stored day of %s again from IBKR.", instrument)
        return
    await record_evidence(connection, instrument, stored_bar, ibkr_bars, recorded_at_utc)


async def record_evidence(
    connection: psycopg.AsyncConnection,
    instrument: Instrument,
    stored_bar: Bar,
    ibkr_bars: list[Bar],
    recorded_at_utc: datetime,
) -> None:
    """Records a candidate when `ibkr_bars` holds the bar of the stored day and the 2 closes show a stock split. A
    stock split that waits with an ex-date after the stored day already explains the difference, so it gives no second
    candidate: 2 confirmations would divide the bars 2 times."""
    ibkr_bar = next((bar for bar in ibkr_bars if bar.start_utc == stored_bar.start_utc), None)
    if ibkr_bar is None:
        return
    split_ratio = find_evidence_ratio(stored_bar.close, ibkr_bar.close)
    if split_ratio is None:
        return
    waiting_splits = await select_waiting_splits(connection, instrument)
    if any(ex_date_utc > stored_bar.start_utc for ex_date_utc, _ in waiting_splits):
        return
    await connection.execute(
        INSERT_CANDIDATE,
        {
            "symbol": instrument.symbol,
            "exchange": instrument.exchange,
            "currency": instrument.currency,
            "ex_date_utc": stored_bar.start_utc + ONE_DAY,
            "split_ratio": split_ratio,
            "recorded_at_utc": recorded_at_utc,
        },
    )


async def select_waiting_splits(
    connection: psycopg.AsyncConnection, instrument: Instrument
) -> list[tuple[datetime, Decimal]]:
    async with connection.cursor() as cursor:
        await cursor.execute(
            SELECT_WAITING_SPLITS,
            {"symbol": instrument.symbol, "exchange": instrument.exchange, "currency": instrument.currency},
        )
        return [(row[0], row[1]) for row in await cursor.fetchall()]


async def to_stored_form(connection: psycopg.AsyncConnection, instrument: Instrument, bars: list[Bar]) -> list[Bar]:
    """IBKR bars that start before the ex-date of a waiting stock split (a candidate, or a Databento import split)
    get the old prices of the stored bars: the prices are multiplied by the split ratio and the volume is divided by it.
    Thus all stored bars before the ex-date have one form, and the change of the stored bars (section 8.13.3) divides
    each of them 1 time."""
    waiting_splits = await select_waiting_splits(connection, instrument)
    return [convert_bar(bar, waiting_splits) for bar in bars]


def convert_bar(bar: Bar, candidates: list[tuple[datetime, Decimal]]) -> Bar:
    for ex_date_utc, split_ratio in candidates:
        if bar.start_utc < ex_date_utc:
            bar = Bar(
                start_utc=bar.start_utc,
                open=bar.open * split_ratio,
                high=bar.high * split_ratio,
                low=bar.low * split_ratio,
                close=bar.close * split_ratio,
                volume=bar.volume / split_ratio,
            )
    return bar


async def read_stock_split_candidates(*, database_url: str) -> list[StockSplitCandidate]:
    """The stock splits that evidence A found and that are not confirmed, for the stock split check. No IBKR call."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection, connection.cursor() as cursor:
        await cursor.execute(SELECT_CANDIDATES)
        rows = await cursor.fetchall()
    return [
        StockSplitCandidate(
            id=int(row[0]),
            instrument=Instrument(symbol=str(row[1]), exchange=str(row[2]), currency=str(row[3])),
            ex_date_utc=row[4],
            split_ratio=row[5],
        )
        for row in rows
    ]


async def record_stock_split_evidence(
    *,
    database_url: str,
    gateway_connection: GatewayConnection,
    instruments: list[Instrument],
    recorded_at_utc: datetime,
) -> None:
    """Evidence A for the stock split check (forward_test.md section 12.22): reads the last stored daily bar of each
    instrument from IBKR again and records a candidate when the closes show a stock split. A failed read is logged.
    Raises GatewayRequestError only when the connection is lost."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        for instrument in instruments:
            await check_evidence_a(connection, gateway_connection, instrument, recorded_at_utc)
            await connection.commit()
            if not gateway_connection.is_connected():
                message = "The connection to IB Gateway was lost during the stock split evidence read."
                raise GatewayRequestError(message)
