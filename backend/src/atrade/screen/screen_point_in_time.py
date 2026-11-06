"""The point-in-time run of a screen for a `screen` backtest universe (docs/architecture/screen.md section 24.9).

The run uses only the daily bars that start before `as_of_utc`: the bars that close at or before that time. The
filters get the daily bar summary that these bars give, so a filter value equals the value that the summary had at
that time. The run saves no screen result.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Any

from atrade.foundation.bar import Bar
from atrade.foundation.instrument import Instrument
from atrade.market_data import (
    read_daily_bar_summaries_before,
    read_daily_bar_summaries_of_currency,
    read_hk_instrument_list,
    read_last_daily_bars,
    read_us_universe_members,
    read_us_universe_quarter_starts,
)
from atrade.screen.screen_run import ScreenOutcome, run_screen_steps
from atrade.screen.screen_running import MARKET_CURRENCIES, UNIVERSE_SIZE
from atrade.watchlist import read_watchlist_instruments

logger = logging.getLogger("atrade.screen")

# `read_us_universe_quarter_starts` gives the quarters that start before its end. 1 microsecond more keeps a quarter
# that starts exactly at `as_of_utc`.
SMALLEST_STEP = timedelta(microseconds=1)


async def read_start_instruments_at(
    database_url: str, *, market: str, start: str, as_of_utc: datetime
) -> list[Instrument]:
    """The start instruments of section 24.2 at `as_of_utc`. Only the US universe has a list for each quarter: the
    last quarter that starts at or before `as_of_utc`. The other lists are the lists of today."""
    currency = MARKET_CURRENCIES[market]
    if start == "quarter_universe":
        quarter_starts = await read_us_universe_quarter_starts(
            database_url=database_url, end_utc=as_of_utc + SMALLEST_STEP
        )
        if not quarter_starts:
            return []
        members = await read_us_universe_members(
            database_url=database_url, quarter_start_utc=quarter_starts[-1], top_n=UNIVERSE_SIZE
        )
        return [member.instrument for member in members]
    if start == "all_with_daily_bars":
        summaries = await read_daily_bar_summaries_of_currency(database_url=database_url, currency=currency)
        return [summary.instrument for summary in summaries]
    if start == "hk_instrument_list":
        return await read_hk_instrument_list(database_url=database_url)
    watchlist = await read_watchlist_instruments(database_url=database_url)
    return [instrument for instrument in watchlist if instrument.currency == currency]


async def run_screen_at(
    *, database_url: str, market: str, definition: dict[str, Any], as_of_utc: datetime
) -> ScreenOutcome:
    """Runs a checked screen definition on the daily bars that start before `as_of_utc`. Daily bars are read in the
    global source order, as for a run of the screen page (section 24.1). The prefilter of section 24.9 applies."""
    instruments = await read_start_instruments_at(
        database_url, market=market, start=definition["start"], as_of_utc=as_of_utc
    )
    summaries = await read_daily_bar_summaries_before(
        database_url=database_url, instruments=instruments, before_utc=as_of_utc
    )

    async def read_daily_bars(
        instruments: list[Instrument], before_utc: datetime, bar_count: int
    ) -> dict[Instrument, list[Bar]]:
        return await read_last_daily_bars(
            database_url=database_url,
            instruments=instruments,
            before_utc=min(before_utc, as_of_utc),
            bar_count=bar_count,
        )

    return await run_screen_steps(
        definition=definition,
        start_instruments=instruments,
        summaries=summaries,
        read_daily_bars=read_daily_bars,
        prefilter=True,
    )


def prepare_screen_period_process() -> None:
    """The initializer of a worker process. A new worker has no log configuration. Only standard output reaches the
    log of the web container (section 24.9)."""
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)


def run_screen_period(
    *, database_url: str, market: str, definition: dict[str, Any], as_of_utc: datetime
) -> list[Instrument]:
    """One period of a `screen` universe in a worker process. It sends back only the members: no bars and no rows go
    between the processes (section 24.9)."""
    run_start = time.monotonic()
    outcome = asyncio.run(
        run_screen_at(database_url=database_url, market=market, definition=definition, as_of_utc=as_of_utc)
    )
    logger.info(
        "Screen period %s: %d candidates, %.1f seconds.",
        f"{as_of_utc:%Y-%m-%d}",
        outcome.after_prefilter_count,
        time.monotonic() - run_start,
    )
    return [row.instrument for row in outcome.rows]
