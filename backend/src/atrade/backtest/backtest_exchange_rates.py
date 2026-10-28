"""The daily exchange rates of a backtest of an instrument that is not in USD (docs/architecture/backtest.md 10.8).

The start route saves the rates from IBKR. The child reads only the saved rates and converts the results to USD with
the rate of the last complete day before each time.
"""

from bisect import bisect_right
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

from atrade.backtest.backtest_access import format_message_time
from atrade.backtest.backtest_metrics import BacktestTrade, EquityPoint
from atrade.backtest.backtest_store import BacktestRequest
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.market_data import (
    ExchangeRateReader,
    ExchangeRatesNotReadError,
    SavedExchangeRate,
    read_saved_exchange_rates,
)

USD = "USD"
# The start needs the rate of a complete day before it. The forex market is closed at most a few days, for example
# from Friday to Monday or over Christmas.
EXCHANGE_RATE_LOOK_BACK = timedelta(days=7)
CENT = Decimal("0.01")
# IBKR stock prices have at most 4 decimal places. A converted price keeps 4.
PRICE_STEP = Decimal("0.0001")


class DailyExchangeRates:
    """The USD value of 1 unit of the instrument currency at a time: the rate of the last day that ended at or
    before that time. A day rate is the close of the day, so a time inside the day uses the day before."""

    def __init__(self, rates: list[SavedExchangeRate]) -> None:
        self.day_ends_utc = [rate.day_start_utc + BarPeriod.ONE_DAY.length for rate in rates]
        self.usd_per_unit = [rate.usd_per_unit for rate in rates]

    def find_usd_per_unit(self, time_utc: datetime) -> Decimal | None:
        index = bisect_right(self.day_ends_utc, time_utc)
        if index == 0:
            return None
        return self.usd_per_unit[index - 1]

    def read_usd_per_unit(self, time_utc: datetime) -> Decimal:
        """`find_usd_per_unit` for a time at or after the backtest start, which the child checked first."""
        usd_per_unit = self.find_usd_per_unit(time_utc)
        if usd_per_unit is None:
            message = f"There is no exchange rate before {format_message_time(time_utc)}."
            raise LookupError(message)
        return usd_per_unit


def find_exchange_rate_range(request: BacktestRequest) -> TimeRange:
    return TimeRange(
        start_utc=request.time_range.start_utc - EXCHANGE_RATE_LOOK_BACK, end_utc=request.time_range.end_utc
    )


def describe_missing_start_rate(request: BacktestRequest) -> str:
    """The message of a backtest without a saved rate before its start: the route refuses it, and the child fails."""
    currency = request.instrument.currency
    start_utc = request.time_range.start_utc
    return (
        f"There is no saved {currency} to USD exchange rate of a day in the {EXCHANGE_RATE_LOOK_BACK.days} days before"
        f" {format_message_time(start_utc)}. A backtest converts the paper capital to {currency} with it."
    )


async def read_daily_exchange_rates(*, database_url: str, request: BacktestRequest) -> DailyExchangeRates:
    """The saved rates of the backtest. It never calls IBKR."""
    rates = await read_saved_exchange_rates(
        database_url=database_url, currency=request.instrument.currency, time_range=find_exchange_rate_range(request)
    )
    return DailyExchangeRates(rates)


async def save_exchange_rates(
    *, database_url: str, exchange_rate_reader: ExchangeRateReader, request: BacktestRequest
) -> str | None:
    """Saves the missing daily rates of the backtest from IBKR. Returns why the backtest cannot run, or None.

    A USD instrument needs no rates.
    """
    currency = request.instrument.currency
    if currency == USD:
        return None
    rate_range = find_exchange_rate_range(request)
    needed_rates = (
        f"A backtest of a {currency} instrument needs the daily {currency} to USD exchange rates from IBKR"
        f" from {format_message_time(rate_range.start_utc)} to {format_message_time(rate_range.end_utc)}."
    )
    try:
        await exchange_rate_reader.save_daily_rates(currency, rate_range)
    except ExchangeRatesNotReadError as error:
        return f"{needed_rates} {error}"
    exchange_rates = await read_daily_exchange_rates(database_url=database_url, request=request)
    if exchange_rates.find_usd_per_unit(request.time_range.start_utc) is None:
        return describe_missing_start_rate(request)
    return None


def convert_paper_capital(paper_capital_usd: Decimal, usd_per_unit: Decimal, currency_precision: int) -> Decimal:
    """The paper capital in the instrument currency at the start rate, with the decimal places of the currency."""
    return (paper_capital_usd / usd_per_unit).quantize(Decimal(1).scaleb(-currency_precision))


def convert_equity_curve_to_usd(
    exchange_rates: DailyExchangeRates, equity_curve: list[EquityPoint]
) -> list[EquityPoint]:
    """`equity_curve` is in the instrument currency. Each point uses the rate at its time."""
    return [
        EquityPoint(
            time_utc=point.time_utc,
            equity_usd=(point.equity_usd * exchange_rates.read_usd_per_unit(point.time_utc)).quantize(CENT),
        )
        for point in equity_curve
    ]


def convert_trades_to_usd(exchange_rates: DailyExchangeRates, trades: list[BacktestTrade]) -> list[BacktestTrade]:
    """`trades` are in the instrument currency. Each trade uses the rate at its fill time."""
    converted: list[BacktestTrade] = []
    for trade in trades:
        usd_per_unit = exchange_rates.read_usd_per_unit(trade.time_utc)
        converted.append(
            replace(
                trade,
                price_usd=(trade.price_usd * usd_per_unit).quantize(PRICE_STEP),
                commission_usd=(trade.commission_usd * usd_per_unit).quantize(CENT),
            )
        )
    return converted
