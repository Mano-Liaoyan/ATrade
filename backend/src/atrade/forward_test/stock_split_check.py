"""The daily stock split check of the forward-test worker (docs/architecture/forward_test.md section 12.22).

- The check runs before the market opens on each trading day: 08:00 ET for US instruments (USD) and 08:30 HKT for HK
  instruments (HKD). When the evidence is not complete, it tries again every 15 minutes until 5 minutes before the
  open. The last try writes the "Split check needed" state for incomplete evidence.
- The US trading days are the days of `market_data` (weekdays without New Year's Day and Good Friday). The HK trading
  days are the weekdays.
- When IB Gateway is not reachable at the last try, the check logs it and runs on the next trading day.
- It reads evidence A again for each checked instrument, then gives each instrument to the owner ledger
  (`StockSplitLedger` of `paper_trading`). After a confirmed stock split, or after "Apply split" on the paper trading
  page, it asks the worker to restart the forward tests that hold or trade the instrument. A flat strategy also needs
  the restart: its indicators hold prices from before the stock split.
- The connection uses the bar fetcher client ID. The connection lock keeps one connection of the 2 jobs at a time.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from atrade.forward_test.forward_test_universe import read_forward_tests_by_instrument
from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection, GatewayRequestError
from atrade.market_data import (
    StockSplitCandidate,
    is_us_trading_day,
    read_stock_split_candidates,
    record_stock_split_evidence,
)
from atrade.paper_trading import (
    InstrumentCheck,
    PaperAccountCheckError,
    StockSplitLedger,
    read_owner_instruments,
    read_unrestarted_split_checks,
    require_paper_account,
    write_split_check_restarted,
)

logger = logging.getLogger("atrade.stock_split_check")

RETRY_INTERVAL = timedelta(minutes=15)
LAST_TRY_BEFORE_OPEN = timedelta(minutes=5)
CHECK_INTERVAL_SECONDS = 60.0
STOCK_SECURITY_TYPE = "STK"

type MarketName = Literal["US", "HK"]
# The worker restarts the children of these forward tests (section 12.7).
type RequestRestart = Callable[[list[int]], None]


@dataclass(frozen=True)
class Market:
    name: MarketName
    currency: str
    time_zone: ZoneInfo
    check_time: time
    open_time: time

    def is_trading_day(self, day: date) -> bool:
        return is_us_trading_day(day) if self.name == "US" else day.weekday() < 5  # noqa: PLR2004 - Saturday is 5.


MARKETS = (
    Market(
        name="US", currency="USD", time_zone=ZoneInfo("America/New_York"), check_time=time(8), open_time=time(9, 30)
    ),
    Market(
        name="HK", currency="HKD", time_zone=ZoneInfo("Asia/Hong_Kong"), check_time=time(8, 30), open_time=time(9, 30)
    ),
)


def find_last_try_limit(market: Market, day: date) -> datetime:
    """5 minutes before the open, in UTC. No try starts after it."""
    return (datetime.combine(day, market.open_time, market.time_zone) - LAST_TRY_BEFORE_OPEN).astimezone(UTC)


def find_try_times(market: Market, day: date) -> list[datetime]:
    """The tries of one trading day in UTC when each try finds incomplete evidence: the check time, then every
    15 minutes until 5 minutes before the open."""
    try_time = datetime.combine(day, market.check_time, market.time_zone).astimezone(UTC)
    tries: list[datetime] = []
    while try_time <= find_last_try_limit(market, day):
        tries.append(try_time)
        try_time += RETRY_INTERVAL
    return tries


@dataclass
class MarketState:
    # The local day of the last finished check.
    done_day: date | None = None
    next_try_utc: datetime | None = None
    # The local day on which the check read the flat instruments of the running forward tests.
    flat_read_day: date | None = None


class StockSplitCheck:
    def __init__(  # noqa: PLR0913 readability-exception: one keyword argument per input of the check.
        self,
        *,
        database_url: str,
        clock: Clock,
        settings: Settings,
        open_gateway_connection: Callable[[], GatewayConnection],
        connection_lock: asyncio.Lock,
        request_restart: RequestRestart,
    ) -> None:
        self.database_url = database_url
        self.clock = clock
        self.settings = settings
        self.open_gateway_connection = open_gateway_connection
        self.connection_lock = connection_lock
        self.request_restart = request_restart
        self.market_states: dict[MarketName, MarketState] = {market.name: MarketState() for market in MARKETS}

    async def keep_checking(self) -> None:
        """Runs until the caller cancels it."""
        while True:
            await self.run_due_tries()
            await self.restart_after_apply()
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    async def run_due_tries(self) -> None:
        """Runs the try of each market that is due now. It never raises."""
        now_utc = self.clock.read_now_utc()
        for market in MARKETS:
            state = self.market_states[market.name]
            day = now_utc.astimezone(market.time_zone).date()
            if state.done_day == day or not market.is_trading_day(day):
                continue
            first_try = datetime.combine(day, market.check_time, market.time_zone).astimezone(UTC)
            last_try_limit = find_last_try_limit(market, day)
            if not first_try <= now_utc <= last_try_limit:
                continue
            if state.next_try_utc is not None and now_utc < state.next_try_utc:
                continue
            is_last_try = now_utc + RETRY_INTERVAL > last_try_limit
            is_complete = await self.try_market(market, day, is_last_try=is_last_try)
            if is_complete or is_last_try:
                state.done_day = day
                state.next_try_utc = None
            else:
                state.next_try_utc = now_utc + RETRY_INTERVAL

    async def try_market(self, market: Market, day: date, *, is_last_try: bool) -> bool:
        """One try of one market. True when the evidence of all instruments was complete."""
        async with self.connection_lock:
            gateway_connection = self.open_gateway_connection()
            try:
                await gateway_connection.connect()
                return await self.check_instruments(gateway_connection, market, day, is_last_try=is_last_try)
            except (GatewayRequestError, PaperAccountCheckError) as error:
                logger.warning(
                    "The %s stock split check did not run. IB Gateway or the paper account: %s", market.name, error
                )
                return False
            except Exception:
                logger.exception("The %s stock split check failed.", market.name)
                return False
            finally:
                gateway_connection.disconnect()

    async def check_instruments(
        self, gateway_connection: GatewayConnection, market: Market, day: date, *, is_last_try: bool
    ) -> bool:
        account = require_paper_account(settings=self.settings, gateway_connection=gateway_connection)
        account_quantities = {
            Instrument(
                symbol=position.symbol, exchange=position.exchange, currency=position.currency
            ): position.quantity
            for position in gateway_connection.read_portfolio()
            if position.account == account
            and position.security_type == STOCK_SECURITY_TYPE
            and position.currency == market.currency
        }
        owner_instruments = [
            instrument
            for instrument in await read_owner_instruments(database_url=self.database_url, account=account)
            if instrument.currency == market.currency
        ]
        running_forward_tests = await read_forward_tests_by_instrument(self.database_url)
        running_instruments = [
            instrument for instrument in running_forward_tests if instrument.currency == market.currency
        ]
        held_instruments = [*account_quantities, *owner_instruments]
        instruments = list(dict.fromkeys([*held_instruments, *running_instruments]))
        # IBKR has 1 historical read for each instrument, and a universe has 500 members. A flat member goes only in
        # the first try of a day, so that the tries do not keep the bar fetcher waiting.
        state = self.market_states[market.name]
        await record_stock_split_evidence(
            database_url=self.database_url,
            gateway_connection=gateway_connection,
            instruments=list(dict.fromkeys(held_instruments)) if state.flat_read_day == day else instruments,
            recorded_at_utc=self.clock.read_now_utc(),
        )
        state.flat_read_day = day
        candidates = find_candidates(await read_stock_split_candidates(database_url=self.database_url), market)
        ledger = StockSplitLedger(
            database_url=self.database_url, gateway_connection=gateway_connection, clock=self.clock
        )
        is_complete = True
        for instrument in list(dict.fromkeys([*instruments, *candidates])):
            outcome = await ledger.check_instrument(
                InstrumentCheck(
                    account=account,
                    instrument=instrument,
                    account_quantity=account_quantities.get(instrument, Decimal(0)),
                    candidate=candidates.get(instrument),
                    check_day_utc=datetime.combine(day, time(), UTC),
                    is_last_try=is_last_try,
                )
            )
            logger.info("Stock split check of %s: %s.", instrument.symbol, outcome.result)
            if outcome.result == "incomplete":
                is_complete = False
            if outcome.result == "confirmed":
                self.restart_forward_tests(outcome.forward_test_ids, running_forward_tests.get(instrument, []))
        return is_complete

    def restart_forward_tests(self, holding_ids: list[int], running_ids: list[int]) -> None:
        forward_test_ids = sorted({*holding_ids, *running_ids})
        if forward_test_ids:
            self.request_restart(forward_test_ids)

    async def restart_after_apply(self) -> None:
        """After "Apply split" on the Home page, restarts the forward tests that got a split adjustment and the running
        forward tests of the instrument."""
        try:
            for split_check, forward_test_ids in await read_unrestarted_split_checks(database_url=self.database_url):
                running_forward_tests = await read_forward_tests_by_instrument(self.database_url)
                self.restart_forward_tests(forward_test_ids, running_forward_tests.get(split_check.instrument, []))
                await write_split_check_restarted(
                    database_url=self.database_url,
                    split_check_id=split_check.id,
                    restarted_at_utc=self.clock.read_now_utc(),
                )
        except Exception:
            logger.exception("The restart after Apply split failed. The next check tries again.")


def find_candidates(candidates: list[StockSplitCandidate], market: Market) -> dict[Instrument, StockSplitCandidate]:
    """The latest candidate of each instrument of the market."""
    return {
        candidate.instrument: candidate for candidate in candidates if candidate.instrument.currency == market.currency
    }
