"""Runs the code of one strategy version on saved bars in the NautilusTrader backtest engine.

Only the backtest child process calls this module, because the engine blocks the event loop and the strategy
code is user code (docs/architecture.md section 10).
"""

import traceback
from dataclasses import dataclass
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
from nautilus_trader.persistence import BarDataWrangler, DataCatalogConfig, ParquetDataCatalog

from atrade.backtest.arrow_bars import NANOSECONDS_PER_SECOND, convert_bars_to_arrow_bytes
from atrade.backtest.backtest_metrics import BacktestTrade
from atrade.backtest.backtest_store import BacktestRequest
from atrade.foundation.bar import Bar, BarPeriod
from atrade.foundation.instrument import Instrument
from atrade.strategy import StrategyFileError, load_strategy_classes

MIN_PRICE_PRECISION = 2
# NautilusTrader refuses a precision above 9 in its standard-precision build. IBKR prices have fewer places.
MAX_PRECISION = 9
ERROR_LOG_FILE_NAME = "strategy_errors"
LOOK_BACK_CATALOG_DIRECTORY_NAME = "look_back_catalog"
# The catalog says that it holds all bars from the first to the last UNIX nanosecond (1, not 0: 0 means "no time").
# Then the data engine sends each `request_bars` only to the catalog. A part of the request that the catalog does
# not hold goes to the venue data client. The backtest data client cannot answer, and the request never ends.
CATALOG_FIRST_NS = 1
CATALOG_LAST_NS = 2**63 - 1


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


def create_look_back_catalog(
    look_back_bars: list[Bar], wrangler: BarDataWrangler, bar_period: BarPeriod, work_directory: Path
) -> DataCatalogConfig:
    """A temporary catalog that answers `request_bars` with the look-back bars (bars before the backtest start).

    The engine replays only the bars of the range. The look-back bars go only to the catalog, so they never fill
    an order and never make an equity point.
    """
    catalog_path = work_directory / LOOK_BACK_CATALOG_DIRECTORY_NAME
    catalog_path.mkdir()
    catalog = ParquetDataCatalog(str(catalog_path))
    nautilus_bars = (
        wrangler.process_record_batch_bytes(convert_bars_to_arrow_bytes(look_back_bars, bar_period))
        if look_back_bars
        else []
    )
    catalog.write_bars(nautilus_bars, start=CATALOG_FIRST_NS, end=CATALOG_LAST_NS)
    return DataCatalogConfig(str(catalog_path))


def write_look_back_catalog(
    look_back_bars: list[Bar], instrument: Instrument, bar_period: BarPeriod, work_directory: Path
) -> DataCatalogConfig:
    """The look-back catalog of `create_look_back_catalog` for a forward test LiveNode, with the bar type
    `SYMBOL.EXCHANGE-<bar period>-LAST-EXTERNAL` (docs/architecture/forward_test.md section 12.15)."""
    nautilus_instrument = create_instrument(instrument, look_back_bars)
    bar_type = BarType.from_str(f"{nautilus_instrument.id}-{bar_period.value}-LAST-EXTERNAL")
    volume_precision = max((count_decimal_places(bar.volume) for bar in look_back_bars), default=0)
    wrangler = BarDataWrangler(str(bar_type), nautilus_instrument.price_precision, volume_precision)
    return create_look_back_catalog(look_back_bars, wrangler, bar_period, work_directory)


def create_engine(
    *,
    starting_cash: Decimal,
    currency: str,
    venue: Venue,
    work_directory: Path,
    look_back_catalog: DataCatalogConfig | None = None,
) -> BacktestEngine:
    # The engine logs strategy errors and goes on. shutdown_on_error stops it at the first error, and the
    # error log file lets the child read the error (the engine does not raise it).
    logging = LoggerConfig(
        stdout_level=LogLevel.WARNING,
        fileout_level=LogLevel.ERROR,
        file_config=FileWriterConfig(directory=str(work_directory), file_name=ERROR_LOG_FILE_NAME),
        fileout_sync_on_flush=True,
    )
    engine = BacktestEngine(
        BacktestEngineConfig(
            shutdown_on_error=True, logging=logging, catalogs=[] if look_back_catalog is None else [look_back_catalog]
        )
    )
    # The account is in the instrument currency, so the engine needs no exchange rates (section 10.8).
    account_currency = Currency.from_str(currency)
    engine.add_venue(
        venue,
        OmsType.NETTING,
        AccountType.CASH,
        [Money.from_str(f"{starting_cash} {currency}")],
        base_currency=account_currency,
        # The backtest has no commission model yet. NautilusTrader 2.0 requires an explicit fee model.
        fee_model=FixedFeeModel(Money(0, account_currency)),
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


def read_currency_precision(currency: str) -> int:
    """The decimal places of a cash amount in the currency, for example 2 for HKD."""
    return Currency.from_str(currency).precision


@dataclass(frozen=True)
class StrategyRun:
    """The inputs of one engine run. The account starts with `starting_cash` in the instrument currency."""

    code: str
    request: BacktestRequest
    starting_cash: Decimal
    bars: list[Bar]
    # The bars before the start, for `request_bars`.
    look_back_bars: list[Bar]


def run_strategy_on_bars(run: StrategyRun, work_directory: Path) -> list[BacktestTrade]:
    """Returns the trades of the strategy on `run.bars`, in the instrument currency.

    Raises StrategyFailedError with the strategy error.
    """
    request = run.request
    all_bars = run.look_back_bars + run.bars
    nautilus_instrument = create_instrument(request.instrument, all_bars)
    bar_type = BarType.from_str(f"{nautilus_instrument.id}-{request.bar_period.value}-LAST-EXTERNAL")
    volume_precision = max(count_decimal_places(bar.volume) for bar in all_bars)
    wrangler = BarDataWrangler(str(bar_type), nautilus_instrument.price_precision, volume_precision)
    nautilus_bars = wrangler.process_record_batch_bytes(convert_bars_to_arrow_bytes(run.bars, request.bar_period))
    engine = create_engine(
        starting_cash=run.starting_cash,
        currency=request.instrument.currency,
        venue=nautilus_instrument.venue,
        look_back_catalog=create_look_back_catalog(run.look_back_bars, wrangler, request.bar_period, work_directory),
        work_directory=work_directory,
    )
    engine.add_instrument(nautilus_instrument)
    engine.add_data(nautilus_bars)
    try:
        strategy_class, config_class = load_strategy_classes(run.code, work_directory)
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
