"""Daily exchange rates in USD: saves the IBKR forex rates of the days that are not saved yet, and reads the saved
rates. A backtest of an instrument that is not in USD converts its results with them (docs/architecture/backtest.md
section 10.8)."""

import asyncio
from collections import defaultdict
from datetime import timedelta

import psycopg

from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.clock import Clock
from atrade.ibkr import GatewayConnection, GatewayRequestError
from atrade.market_data import exchange_rate_store
from atrade.market_data.bar_reading import find_missing_ranges, limit_to_complete_bars
from atrade.market_data.exchange_rate_store import SavedExchangeRate

USD = "USD"
# IBKR can publish the rate of a day some hours after its close. A day that ended less than 1 day ago is not read, so
# a missing rate is not recorded as "saved" for ever.
PUBLICATION_DELAY = timedelta(days=1)


class ExchangeRatesNotReadError(Exception):
    """Some rates are not saved and IBKR did not return them. The message says why, for the user."""


class ExchangeRateReader:
    def __init__(self, *, database_url: str, clock: Clock, gateway_connection: GatewayConnection) -> None:
        self.database_url = database_url
        self.clock = clock
        self.gateway_connection = gateway_connection
        # One fill of missing ranges at a time for each currency: two equal backtest starts cause one IBKR request.
        self.fill_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def save_daily_rates(self, currency: str, time_range: TimeRange) -> None:
        """Reads from IBKR the rates of the days in the range that ended at least 1 day ago and are not saved yet, and
        saves them.

        Raises ExchangeRatesNotReadError when missing rates cannot be read.
        """
        published_end_utc = min(time_range.end_utc, self.clock.read_now_utc() - PUBLICATION_DELAY)
        complete_range = limit_to_complete_bars(
            TimeRange(time_range.start_utc, published_end_utc), BarPeriod.ONE_DAY, self.clock
        )
        if complete_range is None:
            return
        async with (
            await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection,
            self.fill_locks[currency],
        ):
            saved_ranges = await exchange_rate_store.select_saved_ranges(connection, currency, complete_range)
            missing_ranges = find_missing_ranges(complete_range, saved_ranges)
            if missing_ranges and not self.gateway_connection.is_connected():
                message = "ATrade is not connected to IB Gateway. Connect IB Gateway and start the backtest again."
                raise ExchangeRatesNotReadError(message)
            for missing_range in missing_ranges:
                try:
                    rates = await self.gateway_connection.read_daily_exchange_rates(currency, USD, missing_range)
                except GatewayRequestError as error:
                    message = f"IBKR did not return them: {error}"
                    raise ExchangeRatesNotReadError(message) from error
                await exchange_rate_store.save_exchange_rates_of_range(
                    connection,
                    currency,
                    missing_range,
                    [SavedExchangeRate(day_start_utc=rate.day_start_utc, usd_per_unit=rate.rate) for rate in rates],
                )


async def read_saved_exchange_rates(
    *, database_url: str, currency: str, time_range: TimeRange
) -> list[SavedExchangeRate]:
    """The saved daily rates of the days that start in the range, oldest first. It never calls IBKR."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await exchange_rate_store.select_exchange_rates(connection, currency, time_range)
