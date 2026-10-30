"""The daily bar update of the `web` process (docs/architecture/market_data.md section 8.11).

At 18:00 ET of each US trading day, the update reads the daily bars of the current quarter's US universe, the HK
instrument list, and the watchlist from IBKR into ibkr_bar, and updates the daily bar summary. 18:00 ET is after the
US close and after the Hong Kong close of the same day. When IB Gateway is not reachable, the update does not run
that day.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import psycopg

from atrade.foundation.bar import BarPeriod, TimeRange, floor_to_bar_start
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection, GatewayRequestError
from atrade.market_data import bar_store, hk_instrument_list_store
from atrade.market_data.bar_source import BarSource
from atrade.market_data.daily_bar_summary import update_daily_bar_summaries
from atrade.market_data.us_trading_days import find_first_trading_day_of_quarter, is_trading_day
from atrade.market_data.us_universe import MEMBER_COUNT, read_us_universe_members, to_utc_day

logger = logging.getLogger(__name__)
NEW_YORK = ZoneInfo("America/New_York")
UPDATE_TIME_ET = time(18, 0)
CHECK_INTERVAL_SECONDS = 60.0
# An instrument without IBKR daily bars gets the daily bars of 1 year, the warm-up of section 8.12.
FIRST_READ_LENGTH = timedelta(days=366)


class DailyBarUpdate:
    def __init__(
        self,
        *,
        database_url: str,
        clock: Clock,
        gateway_connection: GatewayConnection,
        read_watchlist_instruments: Callable[[], Awaitable[list[Instrument]]],
    ) -> None:
        """`read_watchlist_instruments`: market_data does not import watchlist (docs/architecture.md section 6.2),
        so app/ gives the watchlist read."""
        self.database_url = database_url
        self.clock = clock
        self.gateway_connection = gateway_connection
        self.read_watchlist_instruments = read_watchlist_instruments
        self.last_update_day: date | None = None

    async def keep_updating(self) -> None:
        """Runs until the caller cancels it. An error is logged, and the update runs again on the next trading day."""
        while True:
            try:
                await self.update_if_due()
            except Exception:
                logger.exception("The daily bar update failed.")
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    def find_due_day(self, now_utc: datetime) -> date | None:
        """The New York date of the update that is due now, or None."""
        now_et = now_utc.astimezone(NEW_YORK)
        if not is_trading_day(now_et.date()) or now_et.time() < UPDATE_TIME_ET:
            return None
        return None if now_et.date() == self.last_update_day else now_et.date()

    async def update_if_due(self) -> bool:
        """Returns True when the update ran."""
        due_day = self.find_due_day(self.clock.read_now_utc())
        if due_day is None:
            return False
        self.last_update_day = due_day
        if not self.gateway_connection.is_connected():
            logger.warning("IB Gateway is not reachable. The daily bar update of %s does not run.", due_day)
            return False
        await self.update(due_day)
        return True

    async def read_update_instruments(self, connection: psycopg.AsyncConnection, day: date) -> list[Instrument]:
        quarter_start_utc = to_utc_day(find_first_trading_day_of_quarter(day))
        members = await read_us_universe_members(
            database_url=self.database_url, quarter_start_utc=quarter_start_utc, top_n=MEMBER_COUNT
        )
        hk_members = await hk_instrument_list_store.select_members(connection)
        watchlist = await self.read_watchlist_instruments()
        instruments = [
            *(member.instrument for member in members),
            *(
                Instrument(symbol=member.symbol, exchange=member.exchange, currency=member.currency)
                for member in hk_members
            ),
            *watchlist,
        ]
        return list(dict.fromkeys(instruments))

    async def find_read_range(self, connection: psycopg.AsyncConnection, instrument: Instrument) -> TimeRange | None:
        """From the last saved IBKR daily bar, which is read again (stock split evidence, section 8.13), to the start
        of the current day. None when no complete day is missing."""
        end_utc = floor_to_bar_start(self.clock.read_now_utc(), BarPeriod.ONE_DAY)
        coverage = await bar_store.select_saved_bar_coverage(connection, [BarSource.IBKR], [instrument])
        daily_coverage = [item for item in coverage[0] if item.bar_period == BarPeriod.ONE_DAY]
        start_utc = daily_coverage[0].last_start_utc if daily_coverage else end_utc - FIRST_READ_LENGTH
        return TimeRange(start_utc, end_utc) if start_utc < end_utc else None

    async def update(self, day: date) -> None:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            instruments = await self.read_update_instruments(connection, day)
            updated_instruments: list[Instrument] = []
            for instrument in instruments:
                time_range = await self.find_read_range(connection, instrument)
                if time_range is None:
                    continue
                try:
                    bars = await self.gateway_connection.read_historical_bars(instrument, BarPeriod.ONE_DAY, time_range)
                except GatewayRequestError:
                    logger.exception("The daily bar update did not read the daily bars of %s.", instrument)
                    continue
                await bar_store.save_bars_of_range(connection, instrument, BarPeriod.ONE_DAY, time_range, bars)
                updated_instruments.append(instrument)
            await update_daily_bar_summaries(connection, updated_instruments)
        logger.info("The daily bar update of %s saved the daily bars of %d instruments.", day, len(updated_instruments))
