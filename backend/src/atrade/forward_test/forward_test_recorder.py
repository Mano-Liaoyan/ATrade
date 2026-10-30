"""The platform DataActor of a forward test: at the end of each bar it saves the bar in the bar store of
`market_data`, and records one equity point (docs/architecture/forward_test.md section 12.8).

The ATrade execution client writes the fills into the owner ledger. The recorder reads them from there, not from
`self.cache`, and does not read the IBKR NetLiquidation.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import psycopg
from nautilus_trader.common import DataActor
from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType, InstrumentId

from atrade.backtest import calculate_equity_curve
from atrade.forward_test import forward_test_records
from atrade.foundation.bar import Bar, BarPeriod, TimeRange, floor_to_bar_start
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarRequest, save_received_bars_blocking

NANOSECONDS_PER_SECOND = 1_000_000_000

logger = logging.getLogger("atrade.forward_test_recorder")


@dataclass(frozen=True)
class RecorderInput:
    database_url: str
    forward_test_id: int
    # The key of the saved bars. A backtest of the same period reads them with it.
    instrument: Instrument
    instrument_id: InstrumentId
    bar_type: BarType
    bar_period: BarPeriod
    # The start of the equity: the allocated capital (section 12.18), or the start balance of an old forward test.
    start_balance_usd: Decimal


def convert_ns_to_utc(time_ns: int) -> datetime:
    return datetime.fromtimestamp(time_ns / NANOSECONDS_PER_SECOND, tz=UTC)


def convert_bar(bar: NautilusBar, bar_period: BarPeriod) -> Bar:
    # ts_event is the bar end (backtest/arrow_bars.py). The equity curve function takes the bar start.
    return Bar(
        start_utc=convert_ns_to_utc(bar.ts_event) - bar_period.length,
        open=bar.open.as_decimal(),
        high=bar.high.as_decimal(),
        low=bar.low.as_decimal(),
        close=bar.close.as_decimal(),
        volume=bar.volume.as_decimal(),
    )


class ForwardTestRecorder(DataActor):
    """readability-exception: NautilusTrader requires a DataActor subclass to get bars (C3, 1 level)."""

    def __init__(self, recorder_input: RecorderInput) -> None:
        super().__init__()
        self.recorder_input = recorder_input

    def on_start(self) -> None:
        self.subscribe_bars(self.recorder_input.bar_type)  # pyright: ignore[reportUnknownMemberType]

    def save_bar(self, bar: Bar) -> None:
        """Saves the complete bar for backtests. A failed save is logged and does not stop the forward test."""
        bar_period = self.recorder_input.bar_period
        if bar.start_utc != floor_to_bar_start(bar.start_utc, bar_period):
            # The bar store keys bars by the bar period start. Another start would add a second bar for one period.
            logger.warning(
                "Forward test %s: a bar starts at %s, not at a bar period start. It is not saved.",
                self.recorder_input.forward_test_id,
                bar.start_utc,
            )
            return
        bar_request = BarRequest(
            instrument=self.recorder_input.instrument,
            bar_period=bar_period,
            time_range=TimeRange(start_utc=bar.start_utc, end_utc=bar.start_utc + bar_period.length),
        )
        try:
            save_received_bars_blocking(
                database_url=self.recorder_input.database_url, bar_request=bar_request, bars=[bar]
            )
        except psycopg.Error as error:
            logger.warning(
                "Forward test %s: the bar of %s was not saved: %s",
                self.recorder_input.forward_test_id,
                bar.start_utc,
                error,
            )

    def on_bar(self, bar: NautilusBar) -> None:
        converted_bar = convert_bar(bar, self.recorder_input.bar_period)
        self.save_bar(converted_bar)
        with psycopg.connect(self.recorder_input.database_url, autocommit=True) as connection:
            fills = forward_test_records.select_ledger_fills_blocking(connection, self.recorder_input.forward_test_id)
            # Equity = the start capital + the cash of the fills up to the bar end + the position at the close.
            [equity_point] = calculate_equity_curve(
                start_cash=self.recorder_input.start_balance_usd,
                bars=[converted_bar],
                bar_period=self.recorder_input.bar_period,
                trades=[fill.trade for fill in fills if fill.instrument == self.recorder_input.instrument],
            )
            forward_test_records.save_equity_point(
                connection, forward_test_id=self.recorder_input.forward_test_id, equity_point=equity_point
            )
