"""The bar fetcher of the forward-test worker: it reads the daily bars of the members of multi-instrument forward tests
from IBKR with its own client ID and saves them in ibkr_bar (docs/architecture/forward_test.md section 12.20).

It reads only the ranges that no bar source in the global source order saved. So the daily read after the close
asks IBKR only for the days after the last saved day, and the warm-up fill only for the missing parts of 1 year.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from datetime import datetime, time, timedelta

from atrade.foundation.bar import BarPeriod, TimeRange, floor_to_bar_start
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection, GatewayRequestError
from atrade.market_data import BarRequest, read_unsaved_ranges, save_received_bars

DAILY = BarPeriod.ONE_DAY
# The warm-up of a multi-instrument forward test on daily bars (section 12.17).
WARM_UP_LENGTH = timedelta(days=365)
# IBKR refuses 6 or more requests for the same contract in 2 seconds (market_data.md section 8.4).
REQUEST_INTERVAL_SECONDS = 0.5
# A daily bar starts at 00:00 UTC of its trading date and is complete at the next 00:00 UTC. The daily read runs at
# the first check after this time of each UTC day: after the US close (20:00 or 21:00 UTC) and before the daily IB
# Gateway restart (23:45 ET).
DAILY_READ_TIME_UTC = time(0, 30)
# The worker checks this often if the daily read is due. A daily read that did not reach IB Gateway runs again at the
# next check.
CHECK_INTERVAL_SECONDS = 300.0
# The worker checks this often for a new multi-instrument forward test. Its child starts after the warm-up fill.
NEW_FORWARD_TEST_CHECK_SECONDS = 5.0

logger = logging.getLogger("atrade.bar_fetcher")

# Forward test ID -> the members of each running multi-instrument forward test.
type ReadMemberLists = Callable[[], Awaitable[dict[int, list[Instrument]]]]
type Sleep = Callable[[float], Awaitable[None]]


def join_members(member_lists: Iterable[Iterable[Instrument]]) -> list[Instrument]:
    """The union of the members, in the order of the first appearance: each instrument one time."""
    return list(dict.fromkeys(instrument for members in member_lists for instrument in members))


class BarFetcher:
    def __init__(  # noqa: PLR0913 readability-exception: one keyword argument per input of the bar fetcher.
        self,
        *,
        database_url: str,
        clock: Clock,
        open_gateway_connection: Callable[[], GatewayConnection],
        read_member_lists: ReadMemberLists,
        sleep: Sleep = asyncio.sleep,
        connection_lock: asyncio.Lock | None = None,
    ) -> None:
        self.database_url = database_url
        self.clock = clock
        self.open_gateway_connection = open_gateway_connection
        self.read_member_lists = read_member_lists
        self.sleep = sleep
        # The stock split check uses the same client ID. The lock keeps one connection at a time (section 12.22).
        self.connection_lock = connection_lock or asyncio.Lock()
        # The start of the last UTC day of a daily read that reached IB Gateway.
        self.last_read_day_utc: datetime | None = None
        # The members whose warm-up this worker filled, for each forward test. Its child can start (section 12.17).
        # A new quarter adds members: the next check fills their warm-up.
        self.filled_members: dict[int, set[Instrument]] = {}
        # After a failed fill of a new forward test, the next try waits until this time.
        self.next_new_fill_utc: datetime | None = None

    def is_warm_up_filled(self, forward_test_id: int) -> bool:
        return forward_test_id in self.filled_members

    def find_unfilled_members(self, member_lists: dict[int, list[Instrument]]) -> dict[int, list[Instrument]]:
        """The members without a warm-up fill of this worker: of a new forward test, or new in a quarter."""
        unfilled = {
            forward_test_id: [
                instrument
                for instrument in members
                if instrument not in self.filled_members.get(forward_test_id, set())
            ]
            for forward_test_id, members in member_lists.items()
        }
        return {
            forward_test_id: members
            for forward_test_id, members in unfilled.items()
            if members or not self.is_warm_up_filled(forward_test_id)
        }

    def record_filled(self, member_lists: dict[int, list[Instrument]]) -> None:
        for forward_test_id, members in member_lists.items():
            self.filled_members.setdefault(forward_test_id, set()).update(members)

    async def keep_fetching(self) -> None:
        """Runs until the caller cancels it."""
        loop = asyncio.get_running_loop()
        next_daily_check = loop.time()
        while True:
            if loop.time() >= next_daily_check:
                await self.fetch_when_due()
                next_daily_check = loop.time() + CHECK_INTERVAL_SECONDS
            await self.fill_new_forward_tests()
            await self.sleep(NEW_FORWARD_TEST_CHECK_SECONDS)

    async def fill_new_forward_tests(self) -> None:
        """Fills the 1-year warm-up of each forward test that this worker did not fill yet, before its child starts
        (section 12.17), and of the new members of a quarter. It never raises. When IB Gateway is not reachable, it tries again after
        CHECK_INTERVAL_SECONDS."""
        now_utc = self.clock.read_now_utc()
        if self.next_new_fill_utc is not None and now_utc < self.next_new_fill_utc:
            return
        try:
            member_lists = await self.read_member_lists()
            unfilled = self.find_unfilled_members(member_lists)
            if unfilled:
                await self.fill_warm_up(join_members(unfilled.values()), now_utc)
                self.record_filled(unfilled)
        except GatewayRequestError as error:
            logger.warning("The bar fetcher did not fill a new warm-up. IB Gateway is not reachable: %s", error)
            self.next_new_fill_utc = now_utc + timedelta(seconds=CHECK_INTERVAL_SECONDS)
            return
        except Exception:
            logger.exception("The bar fetcher did not fill the warm-up of a new forward test.")
            self.next_new_fill_utc = now_utc + timedelta(seconds=CHECK_INTERVAL_SECONDS)
            return
        self.next_new_fill_utc = None

    async def fetch_when_due(self) -> None:
        """Runs the daily read when it is due today and did not reach IB Gateway yet today. It never raises: a failure
        must not stop the worker. When IB Gateway is not reachable, the read runs again at the next check."""
        now_utc = self.clock.read_now_utc()
        today_utc = floor_to_bar_start(now_utc, DAILY)
        if self.last_read_day_utc == today_utc or now_utc.time() < DAILY_READ_TIME_UTC:
            return
        try:
            member_lists = await self.read_member_lists()
            await self.fill_warm_up(join_members(member_lists.values()), now_utc)
        except GatewayRequestError as error:
            logger.warning("The bar fetcher did not read the daily bars. IB Gateway is not reachable: %s", error)
            return
        except Exception:
            logger.exception("The daily read of the bar fetcher failed.")
            return
        self.last_read_day_utc = today_utc
        self.record_filled(member_lists)

    async def fill_warm_up(self, instruments: Iterable[Instrument], start_utc: datetime) -> None:
        """Reads the daily bars of the 1-year warm-up before `start_utc` that no bar source saved, and saves them in
        ibkr_bar. A day that is not complete yet is not read.

        Raises GatewayRequestError when IB Gateway is not reachable. A failed read of one instrument is logged and
        not saved, so the next read asks IBKR again.
        """
        end_utc = min(floor_to_bar_start(start_utc, DAILY), floor_to_bar_start(self.clock.read_now_utc(), DAILY))
        time_range = TimeRange(start_utc=end_utc - WARM_UP_LENGTH, end_utc=end_utc)
        bar_requests = [
            BarRequest(instrument=instrument, bar_period=DAILY, time_range=time_range)
            for instrument in join_members([instruments])
        ]
        if not bar_requests:
            return
        async with self.connection_lock:
            gateway_connection = self.open_gateway_connection()
            try:
                await gateway_connection.connect()
                await self.read_and_save(gateway_connection, bar_requests)
            finally:
                gateway_connection.disconnect()

    async def read_and_save(self, gateway_connection: GatewayConnection, bar_requests: list[BarRequest]) -> None:
        is_first_request = True
        for bar_request in bar_requests:
            for missing_range in await read_unsaved_ranges(database_url=self.database_url, bar_request=bar_request):
                if not is_first_request:
                    await self.sleep(REQUEST_INTERVAL_SECONDS)
                is_first_request = False
                missing_request = BarRequest(
                    instrument=bar_request.instrument, bar_period=DAILY, time_range=missing_range
                )
                try:
                    bars = await gateway_connection.read_historical_bars(
                        missing_request.instrument, DAILY, missing_range
                    )
                except GatewayRequestError as error:
                    # A lost connection ends the read. The next check reads the missing ranges again.
                    if not gateway_connection.is_connected():
                        raise
                    logger.warning("The bar fetcher did not read the bars of %s: %s", bar_request.instrument, error)
                    continue
                await save_received_bars(database_url=self.database_url, bar_request=missing_request, bars=bars)
