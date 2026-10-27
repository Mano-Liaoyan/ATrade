"""The platform DataActor of a forward test: at the end of each bar it saves the bar in the bar store of
`market_data`, and records the new fills and one equity point (docs/architecture/forward_test.md section 12.8).

A Python DataActor gets no order or fill events, so it reads the fills from `self.cache`. It does not use
PostgresCacheConfig: those tables belong to NautilusTrader and can change in each release candidate.
"""

# The NautilusTrader 2.0 stubs type the cache orders and the order events as Any (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAny=false

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import psycopg
from nautilus_trader.common import DataActor
from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType, InstrumentId, OrderFilled, OrderSide

from atrade.backtest import BacktestTrade, calculate_equity_curve
from atrade.forward_test import forward_test_records
from atrade.forward_test.forward_test_records import RecordedFill
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
    # The paper account balance at the first start of the forward test (section 12.1).
    start_balance_usd: Decimal


def convert_ns_to_utc(time_ns: int) -> datetime:
    return datetime.fromtimestamp(time_ns / NANOSECONDS_PER_SECOND, tz=UTC)


def read_fill(event: OrderFilled) -> RecordedFill:
    commission = event.commission
    return RecordedFill(
        trade_id=str(event.trade_id),
        trade=BacktestTrade(
            time_utc=convert_ns_to_utc(event.ts_event),
            side="BUY" if event.order_side == OrderSide.BUY else "SELL",
            quantity_shares=event.last_qty.as_decimal(),
            price_usd=event.last_px.as_decimal(),
            commission_usd=Decimal(0) if commission is None else commission.as_decimal(),
        ),
    )


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
        self.fills: dict[str, RecordedFill] = {}

    def on_start(self) -> None:
        # A restart continues with the fills that the earlier runs recorded (section 12.7).
        with psycopg.connect(self.recorder_input.database_url) as connection:
            recorded_fills = forward_test_records.select_recorded_fills(connection, self.recorder_input.forward_test_id)
        self.fills = {fill.trade_id: fill for fill in recorded_fills}
        self.subscribe_bars(self.recorder_input.bar_type)

    def read_new_fills(self) -> list[RecordedFill]:
        new_fills: list[RecordedFill] = []
        for order in self.cache.orders(instrument_id=self.recorder_input.instrument_id):
            fill_events = [event for event in order.events() if isinstance(event, OrderFilled)]
            new_fills.extend(read_fill(event) for event in fill_events if str(event.trade_id) not in self.fills)
        return new_fills

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
        new_fills = self.read_new_fills()
        self.fills.update((fill.trade_id, fill) for fill in new_fills)
        [equity_point] = calculate_equity_curve(
            paper_capital_usd=self.recorder_input.start_balance_usd,
            bars=[converted_bar],
            bar_period=self.recorder_input.bar_period,
            trades=[fill.trade for fill in self.fills.values()],
        )
        with psycopg.connect(self.recorder_input.database_url, autocommit=True) as connection:
            forward_test_records.save_bar_records(
                connection,
                forward_test_id=self.recorder_input.forward_test_id,
                new_fills=new_fills,
                equity_point=equity_point,
            )
