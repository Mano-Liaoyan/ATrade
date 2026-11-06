"""Quarterly update of the US universe in the `forward-test` worker (docs/architecture/market_data.md section 8.9).

From 06:00 ET on the first trading day of the quarter until the quarter has members, also on a later day, the update
downloads the EQUS.SUMMARY daily bars of the 100 calendar days to the last ranking day (63 trading days and more),
imports them into databento_bar, and saves the members. When the bar of the previous trading day is not available, it
tries again each 15 minutes. At 09:00 ET it uses the window that ends 1 trading day earlier. A try after a failed
import or save uses the downloaded file again, because a download costs money. When databento_bar already holds the
window, the update does not download it.
"""

import asyncio
import logging
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg

from atrade.foundation.clock import Clock
from atrade.market_data.databento_client import DatabentoClient, DatabentoDownloadNotStartedError
from atrade.market_data.databento_import import import_databento_files
from atrade.market_data.us_trading_days import find_first_trading_day_of_quarter, find_previous_trading_day
from atrade.market_data.us_universe import (
    WINDOW_CALENDAR_DAYS,
    has_ranking_window,
    has_us_universe,
    save_us_universe,
    to_utc_day,
)

logger = logging.getLogger(__name__)
NEW_YORK = ZoneInfo("America/New_York")
UPDATE_TIME_ET = time(6, 0)
FALLBACK_TIME_ET = time(9, 0)
RETRY_INTERVAL = timedelta(minutes=15)
CHECK_INTERVAL_SECONDS = 60.0
MAX_PAID_DOWNLOADS_PER_QUARTER = 3


class UsUniverseUpdate:
    def __init__(self, *, database_url: str, clock: Clock, client: DatabentoClient, download_dir: Path) -> None:
        self.database_url = database_url
        self.clock = clock
        self.client = client
        self.download_dir = download_dir
        self.next_try_utc: datetime | None = None
        self.saved_quarter_start_utc: datetime | None = None
        self.stopped_quarter_start_utc: datetime | None = None
        # By last ranking day. A path is here only after its download ended without an error.
        self.downloaded_paths: dict[date, Path] = {}
        self.paid_downloads: Counter[datetime] = Counter()

    async def keep_updating(self) -> None:
        """Runs until the caller cancels it. An error is logged, and the update tries again after 15 minutes."""
        while True:
            try:
                await asyncio.to_thread(self.update_if_due)
            except Exception:
                logger.exception("The quarterly US universe update failed. It tries again in 15 minutes.")
                self.next_try_utc = self.clock.read_now_utc() + RETRY_INTERVAL
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    def is_due(self, now_utc: datetime) -> bool:
        first_trading_day = find_first_trading_day_of_quarter(now_utc.astimezone(NEW_YORK).date())
        if now_utc < datetime.combine(first_trading_day, UPDATE_TIME_ET, NEW_YORK):
            return False
        return self.next_try_utc is None or now_utc >= self.next_try_utc

    def find_last_ranking_day(self, now_utc: datetime, previous_trading_day: date) -> date | None:
        """The previous trading day when its bar is available. At 09:00 ET, 1 trading day earlier. Else None."""
        if self.client.read_daily_summary_end_utc() >= to_utc_day(previous_trading_day + timedelta(days=1)):
            return previous_trading_day
        if now_utc.astimezone(NEW_YORK).time() >= FALLBACK_TIME_ET:
            last_ranking_day = find_previous_trading_day(previous_trading_day)
            logger.warning(
                "The EQUS.SUMMARY bar of %s is not available at 09:00 ET. The US universe uses the window to %s.",
                previous_trading_day,
                last_ranking_day,
            )
            return last_ranking_day
        self.next_try_utc = now_utc + RETRY_INTERVAL
        logger.info("The EQUS.SUMMARY bar of %s is not available. Next try in 15 minutes.", previous_trading_day)
        return None

    def download(self, quarter_start_utc: datetime, last_ranking_day: date) -> Path | None:
        """The file of the window to `last_ranking_day`. This process buys it at most 1 time. None at the limit of
        downloads that can bill: the update of the quarter then stops until a restart."""
        if last_ranking_day not in self.downloaded_paths:
            if self.paid_downloads[quarter_start_utc] >= MAX_PAID_DOWNLOADS_PER_QUARTER:
                self.stopped_quarter_start_utc = quarter_start_utc
                logger.error(
                    "The US universe update of %s stops after %d downloads that can bill. A restart clears the limit.",
                    f"{quarter_start_utc:%Y-%m-%d}",
                    MAX_PAID_DOWNLOADS_PER_QUARTER,
                )
                return None
            self.paid_downloads[quarter_start_utc] += 1
            try:
                # The full window, also when the previous quarter has less than 63 trading days.
                self.downloaded_paths[last_ranking_day] = self.client.download_daily_summary(
                    last_ranking_day - timedelta(days=WINDOW_CALENDAR_DAYS),
                    last_ranking_day + timedelta(days=1),
                    self.download_dir,
                )
            except DatabentoDownloadNotStartedError:
                self.paid_downloads[quarter_start_utc] -= 1
                raise
        return self.downloaded_paths[last_ranking_day]

    def update_if_due(self) -> None:
        now_utc = self.clock.read_now_utc()
        if not self.is_due(now_utc):
            return
        first_trading_day = find_first_trading_day_of_quarter(now_utc.astimezone(NEW_YORK).date())
        quarter_start_utc = to_utc_day(first_trading_day)
        if quarter_start_utc in (self.saved_quarter_start_utc, self.stopped_quarter_start_utc):
            return
        with psycopg.connect(self.database_url) as connection:
            if has_us_universe(connection, quarter_start_utc):
                self.saved_quarter_start_utc = quarter_start_utc
                return
        last_ranking_day = self.find_last_ranking_day(now_utc, find_previous_trading_day(first_trading_day))
        if last_ranking_day is None:
            return
        if not has_ranking_window(database_url=self.database_url, last_ranking_day=last_ranking_day):
            path = self.download(quarter_start_utc, last_ranking_day)
            if path is None:
                return
            import_databento_files(database_url=self.database_url, file_paths=[path])
        save_us_universe(
            database_url=self.database_url, quarter_start_utc=quarter_start_utc, last_ranking_day=last_ranking_day
        )
        self.next_try_utc = None
        logger.info("Saved the US universe of the quarter that starts on %s.", first_trading_day)
