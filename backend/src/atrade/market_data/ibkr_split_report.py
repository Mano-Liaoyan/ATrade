"""The report step of the IBKR stock split check (docs/architecture/market_data.md section 8.8.3.1). It tests the
stock split rule on the stored IBKR closes and changes nothing, so a change of the rule needs no new IBKR read.

The stock splits that the import check confirmed (`import_check`, `user_apply`, `both_evidences`) are the known
stock splits. The report removes all applied stock splits from the stored Databento closes, finds the stock splits
in these closes with `find_splits_from_ibkr_closes`, and compares them with the known stock splits.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import LiteralString

import psycopg

from atrade.foundation.bar import TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data.ibkr_split_check import (
    DATABENTO_HISTORY_START_UTC,
    create_key_parameters,
    read_stored_ibkr_closes,
    read_stored_prices,
)
from atrade.market_data.stock_split_detection import (
    DailyPrices,
    FoundSplit,
    find_splits_from_ibkr_closes,
)

# A found stock split is a known stock split when its ex-date is this near and its split ratio is this near, the same
# as STEP_SPLIT_RATIO_TOLERANCE.
MATCH_DAYS = timedelta(days=5)
MATCH_RATIO_TOLERANCE = Decimal("0.04")
KNOWN_CONFIRMATIONS = ("import_check", "user_apply", "both_evidences")

SELECT_READ_INSTRUMENTS: LiteralString = """
    SELECT symbol, exchange, currency, check_end_utc, has_ibkr_closes FROM ibkr_split_check
    WHERE read_end_utc IS NOT NULL
    ORDER BY symbol, exchange, currency
"""
# The stock splits that changed the stored Databento bars (databento_import_sql.py).
SELECT_APPLIED_SPLITS: LiteralString = """
    SELECT ex_date_utc, split_ratio, confirmation FROM stock_split
    WHERE symbol = %(symbol)s AND exchange = %(exchange)s AND currency = %(currency)s
        AND confirmation IN ('both_evidences', 'bar_evidence', 'user_apply', 'import_check')
"""


@dataclass(frozen=True)
class ReportedSplit:
    instrument: Instrument
    ex_date: date
    split_ratio: Decimal


@dataclass
class SplitRuleReport:
    read_instrument_count: int = 0
    without_closes_count: int = 0
    # The known stock splits in the days that have both closes. The rule must find them.
    known_split_count: int = 0
    found_known_count: int = 0
    missed_splits: list[ReportedSplit] = field(default_factory=list)
    # The found stock splits that are not known. The apply step applies them.
    other_splits: list[ReportedSplit] = field(default_factory=list)

    def count_other_ratios(self) -> list[tuple[Decimal, int]]:
        return Counter(round(split.split_ratio, 4) for split in self.other_splits).most_common()

    def count_other_symbols(self) -> list[tuple[str, int]]:
        return Counter(split.instrument.symbol for split in self.other_splits).most_common()


def remove_applied_splits(prices: list[DailyPrices], applied_splits: list[tuple[date, Decimal]]) -> list[DailyPrices]:
    """The prices before the stock split adjustment: an applied stock split divided the prices before its ex-date by
    its split ratio and multiplied the volume."""
    raw_prices: list[DailyPrices] = []
    for prices_of_day in prices:
        factor = Decimal(1)
        for ex_date, split_ratio in applied_splits:
            if prices_of_day.day < ex_date:
                factor *= split_ratio
        raw_prices.append(
            DailyPrices(
                day=prices_of_day.day,
                open=prices_of_day.open * factor,
                close=prices_of_day.close * factor,
                volume=prices_of_day.volume / factor,
            )
        )
    return raw_prices


def is_same_split(found: FoundSplit, ex_date: date, split_ratio: Decimal) -> bool:
    return (
        abs(found.ex_date - ex_date) <= MATCH_DAYS and abs(found.split_ratio / split_ratio - 1) <= MATCH_RATIO_TOLERANCE
    )


def compare_splits(
    report: SplitRuleReport,
    instrument: Instrument,
    found_splits: list[FoundSplit],
    known_splits: list[tuple[date, Decimal]],
    overlap_days: list[date],
) -> None:
    """A known stock split counts when it has days with both closes before and from its ex-date."""
    unmatched = list(found_splits)
    for ex_date, split_ratio in known_splits:
        if not overlap_days or not overlap_days[0] < ex_date <= overlap_days[-1]:
            continue
        report.known_split_count += 1
        match = next((found for found in unmatched if is_same_split(found, ex_date, split_ratio)), None)
        if match is None:
            report.missed_splits.append(ReportedSplit(instrument, ex_date, split_ratio))
        else:
            report.found_known_count += 1
            unmatched.remove(match)
    report.other_splits.extend(ReportedSplit(instrument, found.ex_date, found.split_ratio) for found in unmatched)


async def report_instrument(
    connection: psycopg.AsyncConnection, instrument: Instrument, check_end_utc: datetime, report: SplitRuleReport
) -> None:
    prices = await read_stored_prices(connection, instrument, TimeRange(DATABENTO_HISTORY_START_UTC, check_end_utc))
    if not prices:
        return
    cursor = await connection.execute(SELECT_APPLIED_SPLITS, create_key_parameters(instrument))
    applied_rows = await cursor.fetchall()
    applied_splits = [(row[0].date(), row[1]) for row in applied_rows]
    known_splits = [(row[0].date(), row[1]) for row in applied_rows if row[2] in KNOWN_CONFIRMATIONS]
    ibkr_closes = await read_stored_ibkr_closes(connection, instrument, prices[0].day)
    raw_prices = remove_applied_splits(prices, applied_splits)
    overlap_days = [prices_of_day.day for prices_of_day in raw_prices if prices_of_day.day in ibkr_closes]
    found_splits = find_splits_from_ibkr_closes(raw_prices, ibkr_closes)
    compare_splits(report, instrument, found_splits, known_splits, overlap_days)


async def report_ibkr_split_check(*, database_url: str) -> SplitRuleReport:
    """The report step: tests the stock split rule on all read instruments. It sends no IBKR request and changes no
    row."""
    report = SplitRuleReport()
    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as connection:
        cursor = await connection.execute(SELECT_READ_INSTRUMENTS)
        for row in await cursor.fetchall():
            report.read_instrument_count += 1
            if not row[4]:
                report.without_closes_count += 1
                continue
            instrument = Instrument(symbol=str(row[0]), exchange=str(row[1]), currency=str(row[2]))
            await report_instrument(connection, instrument, row[3], report)
    return report
