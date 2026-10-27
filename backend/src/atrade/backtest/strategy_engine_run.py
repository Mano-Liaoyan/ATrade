"""Runs the code of one strategy version on saved bars in the NautilusTrader backtest engine.

Only the backtest child process calls this module, because the engine blocks the event loop and the strategy
code is user code (docs/architecture.md section 10).
"""

import traceback
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
from nautilus_trader.common import FileWriterConfig, LoggerConfig, LogLevel, logger_flush
from nautilus_trader.execution import FixedFeeModel
from nautilus_trader.model import (
    AccountType,
    BarType,
    Currency,
    Equity,
    InstrumentId,
    Money,
    OmsType,
    OrderFilled,
    OrderSide,
    Price,
    Symbol,
    Venue,
)
from nautilus_trader.persistence import BarDataWrangler

from atrade.backtest.arrow_bars import NANOSECONDS_PER_SECOND, convert_bars_to_arrow_bytes
from atrade.backtest.backtest_metrics import BacktestTrade
from atrade.backtest.backtest_store import BacktestRequest
from atrade.foundation.bar import Bar
from atrade.foundation.instrument import Instrument
from atrade.strategy import StrategyFileError, load_strategy_classes

MIN_PRICE_PRECISION = 2
# NautilusTrader refuses a precision above 9 in its standard-precision build. IBKR prices have fewer places.
MAX_PRECISION = 9
ERROR_LOG_FILE_NAME = "strategy_errors"


class StrategyFailedError(Exception):
    """The strategy code failed. The message is the error that the user sees."""


def count_decimal_places(value: Decimal) -> int:
    exponent = value.normalize().as_tuple().exponent
    if not isinstance(exponent, int) or exponent >= 0:
        return 0
    return min(-exponent, MAX_PRECISION)


def create_instrument(instrument: Instrument, bars: list[Bar]) -> Equity:
    prices = [price for bar in bars for price in (bar.open, bar.high, bar.low, bar.close)]
    price_precision = max([MIN_PRICE_PRECISION, *(count_decimal_places(price) for price in prices)])
    return Equity(
        InstrumentId(Symbol(instrument.symbol), Venue(instrument.exchange)),
        Symbol(instrument.symbol),
        Currency.from_str(instrument.currency),
        price_precision,
        Price(10**-price_precision, price_precision),
        0,
        0,
    )


def create_engine(*, paper_capital_usd: Decimal, venue: Venue, work_directory: Path) -> BacktestEngine:
    # The engine logs strategy errors and goes on. shutdown_on_error stops it at the first error, and the
    # error log file lets the child read the error (the engine does not raise it).
    logging = LoggerConfig(
        stdout_level=LogLevel.WARNING,
        fileout_level=LogLevel.ERROR,
        file_config=FileWriterConfig(directory=str(work_directory), file_name=ERROR_LOG_FILE_NAME),
        fileout_sync_on_flush=True,
    )
    engine = BacktestEngine(BacktestEngineConfig(shutdown_on_error=True, logging=logging))
    usd = Currency.from_str("USD")
    engine.add_venue(
        venue,
        OmsType.NETTING,
        AccountType.CASH,
        [Money.from_str(f"{paper_capital_usd} USD")],
        base_currency=usd,
        # The backtest has no commission model yet. NautilusTrader 2.0 requires an explicit fee model.
        fee_model=FixedFeeModel(Money(0, usd)),
    )
    return engine


def read_error_log(work_directory: Path) -> str:
    logger_flush()
    log_texts = [log_file.read_text() for log_file in sorted(work_directory.glob(f"{ERROR_LOG_FILE_NAME}*"))]
    return "".join(log_texts).strip()


def read_trades(engine: BacktestEngine) -> list[BacktestTrade]:
    trades: list[BacktestTrade] = []
    for order in engine.cache.orders():
        for event in order.events():
            if not isinstance(event, OrderFilled):
                continue
            commission = event.commission
            trades.append(
                BacktestTrade(
                    time_utc=datetime.fromtimestamp(event.ts_event / NANOSECONDS_PER_SECOND, tz=UTC),
                    side="BUY" if event.order_side == OrderSide.BUY else "SELL",
                    quantity_shares=event.last_qty.as_decimal(),
                    price_usd=event.last_px.as_decimal(),
                    commission_usd=Decimal(0) if commission is None else commission.as_decimal(),
                )
            )
    return sorted(trades, key=lambda trade: trade.time_utc)


def run_strategy_on_bars(
    *, code: str, request: BacktestRequest, bars: list[Bar], work_directory: Path
) -> list[BacktestTrade]:
    """Returns the trades of the strategy. Raises StrategyFailedError with the strategy error."""
    nautilus_instrument = create_instrument(request.instrument, bars)
    bar_type = BarType.from_str(f"{nautilus_instrument.id}-{request.bar_period.value}-LAST-EXTERNAL")
    volume_precision = max(count_decimal_places(bar.volume) for bar in bars)
    wrangler = BarDataWrangler(str(bar_type), nautilus_instrument.price_precision, volume_precision)
    nautilus_bars = wrangler.process_record_batch_bytes(convert_bars_to_arrow_bytes(bars, request.bar_period))
    engine = create_engine(
        paper_capital_usd=request.paper_capital_usd, venue=nautilus_instrument.venue, work_directory=work_directory
    )
    engine.add_instrument(nautilus_instrument)
    engine.add_data(nautilus_bars)
    try:
        strategy_class, config_class = load_strategy_classes(code, work_directory)
        # readability-exception: the StrategyConfig stub has no such fields. The user subclass must define
        # them (docs/architecture/strategy.md section 9.2).
        config = config_class(instrument_id=nautilus_instrument.id, bar_type=bar_type)  # pyright: ignore[reportCallIssue]
        engine.add_strategy(strategy_class(config))
        engine.run()
    except StrategyFileError as error:
        raise StrategyFailedError(str(error)) from error
    except Exception as error:
        # readability-exception: any error of the user code ends the backtest with its traceback (G1).
        raise StrategyFailedError("".join(traceback.format_exception(error))) from error
    error_log = read_error_log(work_directory)
    if error_log:
        raise StrategyFailedError(error_log)
    return read_trades(engine)
