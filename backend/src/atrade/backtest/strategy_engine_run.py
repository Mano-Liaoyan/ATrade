"""Runs the code of one strategy version on saved bars in the NautilusTrader backtest engine.

Only the backtest child process calls this module, because the engine blocks the event loop and the strategy
code is user code (docs/architecture.md section 10).
"""

# The NautilusTrader 2.0 stubs type some parameters as a bare dict (docs/architecture.md section 16 G).
# pyright: reportUnknownMemberType=false

import functools
import inspect
import math
import traceback
from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any, Literal, cast

from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
from nautilus_trader.common import CacheConfig, FileWriterConfig, LoggerConfig, LogLevel, TimeEvent, logger_flush
from nautilus_trader.config import StrategyConfig
from nautilus_trader.execution import FixedFeeModel
from nautilus_trader.model import (
    AccountId,
    AccountType,
    AggressorSide,
    BarType,
    Currency,
    Equity,
    InstrumentId,
    Money,
    OmsType,
    OrderDenied,
    OrderFilled,
    OrderRejected,
    OrderSide,
    OrderType,
    Position,
    PositionSide,
    Price,
    Quantity,
    StrategyId,
    Symbol,
    TradeId,
    TradeTick,
    Venue,
)
from nautilus_trader.persistence import BarDataWrangler, DataCatalogConfig, ParquetDataCatalog
from nautilus_trader.trading import Strategy

from atrade.backtest.arrow_bars import NANOSECONDS_PER_SECOND, convert_bars_to_arrow_bytes, convert_to_ns
from atrade.backtest.backtest_metrics import BacktestTrade
from atrade.backtest.backtest_store import BacktestRequest
from atrade.foundation.bar import Bar, BarPeriod, find_bar_end
from atrade.foundation.instrument import Instrument
from atrade.strategy import StrategyFileError, load_strategy_classes

MIN_PRICE_PRECISION = 2
# NautilusTrader refuses a precision above 9 in its standard-precision build. IBKR prices have fewer places.
MAX_PRECISION = 9
# The matching engine drops each bar whose volume precision is not the size precision of the instrument, and `Equity`
# has size precision 0.
ENGINE_VOLUME_PRECISION = 0
ERROR_LOG_FILE_NAME = "strategy_errors"
LOOK_BACK_CATALOG_DIRECTORY_NAME = "look_back_catalog"
# The catalog says that it holds all bars from the first to the last UNIX nanosecond (1, not 0: 0 means "no time").
# Then the data engine sends each `request_bars` only to the catalog. A part of the request that the catalog does
# not hold goes to the venue data client. The backtest data client cannot answer, and the request never ends.
CATALOG_FIRST_NS = 1
CATALOG_LAST_NS = 2**63 - 1
# The engine fills a market order on a bar at the bar close. So each bar also gets a trade tick at its open, 1
# millisecond after the bar start: later than the end of the bar before. A `datetime` and `Date.parse` in the browser
# keep a millisecond, so the fill time stays inside its bar for the equity curve and the trade marks. These ticks are real engine data: the last price of an instrument is its last open, and a strategy
# can read them (docs/architecture/backtest.md section 10.10.3).
OPEN_TICK_DELAY_NS = 1_000_000
# The engine splits a bar into 4 ticks. The open tick has the volume of 1 of them.
BAR_VOLUME_PARTS = 4


SINGLE_INSTRUMENT_ON_UNIVERSE_MESSAGE = (
    "This strategy trades a single instrument: its configuration needs instrument_id or bar_type. A universe gives"
    " neither. Run it on one instrument, or use a multi-instrument strategy."
)


class StrategyFailedError(Exception):
    """The strategy code failed. The message is the error that the user sees."""


def count_decimal_places(value: Decimal) -> int:
    exponent = value.normalize().as_tuple().exponent
    if not isinstance(exponent, int) or exponent >= 0:
        return 0
    return min(-exponent, MAX_PRECISION)


def round_up_volumes(bars: list[Bar]) -> list[Bar]:
    """Rounds each volume up to whole shares (ENGINE_VOLUME_PRECISION). The stock split adjustment gives fractional
    volumes. Rounding up keeps each volume above zero: the matching engine fills no order on a bar with volume 0."""
    return [replace(bar, volume=bar.volume.to_integral_value(rounding=ROUND_CEILING)) for bar in bars]


def create_instrument(instrument: Instrument, bars: list[Bar], venue: Venue | None = None) -> Equity:
    """An `Equity` on the exchange of the instrument, or on `venue` (the simulated venue SMART, ADR 0003)."""
    prices = [price for bar in bars for price in (bar.open, bar.high, bar.low, bar.close)]
    price_precision = max([MIN_PRICE_PRECISION, *(count_decimal_places(price) for price in prices)])
    return Equity(
        InstrumentId(Symbol(instrument.symbol), venue or Venue(instrument.exchange)),
        Symbol(instrument.symbol),
        Currency.from_str(instrument.currency),
        price_precision,
        Price(10**-price_precision, price_precision),
        0,
        0,
    )


def create_wrangler(nautilus_instrument: Equity, bar_period: BarPeriod) -> BarDataWrangler:
    return BarDataWrangler(
        bar_period.external_bar_type(nautilus_instrument.id),
        nautilus_instrument.price_precision,
        ENGINE_VOLUME_PRECISION,
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
    wrangler = create_wrangler(nautilus_instrument, bar_period)
    return create_look_back_catalog(look_back_bars, wrangler, bar_period, work_directory)


def make_open_ticks(instrument: Equity, bars: list[Bar]) -> list[TradeTick]:
    """1 trade tick at the open of each bar. A bar without volume also gets a tick: `on_bar` runs on such a bar, so a
    held order must fill before it. The rules of a strategy that sees no order would send the order a second time."""
    ticks: list[TradeTick] = []
    for bar in bars:
        time_ns = convert_to_ns(bar.start_utc) + OPEN_TICK_DELAY_NS
        ticks.append(
            TradeTick(
                instrument.id,
                instrument.make_price(float(bar.open)),
                instrument.make_qty(max(int(bar.volume / BAR_VOLUME_PARTS), 1)),
                AggressorSide.NO_AGGRESSOR,
                TradeId(f"open-{time_ns}"),
                time_ns,
                time_ns,
            )
        )
    return ticks


def make_last_close_tick(instrument: Equity, bars: list[Bar], bar_period: BarPeriod) -> TradeTick:
    """1 trade tick at the close of the last bar, just before its end. An order without a next open fills at this
    close, so the last price of the instrument must be this close, not the last open."""
    bar = bars[-1]
    time_ns = convert_to_ns(find_bar_end(bar.start_utc, bar_period)) - 1
    return TradeTick(
        instrument.id,
        instrument.make_price(float(bar.close)),
        instrument.make_qty(max(int(bar.volume / BAR_VOLUME_PARTS), 1)),
        AggressorSide.NO_AGGRESSOR,
        TradeId(f"close-{time_ns}"),
        time_ns,
        time_ns,
    )


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
            shutdown_on_error=True,
            logging=logging,
            # The orders need only the last open tick. More ticks in the cache cost about 0.8 GB for 500 instruments.
            cache=CacheConfig(tick_capacity=1),
            catalogs=[] if look_back_catalog is None else [look_back_catalog],
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


def find_side_name(order_side: OrderSide) -> Literal["BUY", "SELL"]:
    return "BUY" if order_side == OrderSide.BUY else "SELL"


def read_refused_orders(engine: BacktestEngine) -> list[str]:
    """One line for each order that the risk engine or the venue refused: the time, the order, and the reason."""
    return [
        f"{datetime.fromtimestamp(event.ts_event / NANOSECONDS_PER_SECOND, tz=UTC):%Y-%m-%d %H:%M} UTC:"
        f" {find_side_name(order.side)} {order.quantity} {order.instrument_id.symbol} refused ({event.reason})"
        for order in engine.cache.orders()
        for event in order.events()
        if isinstance(event, OrderDenied | OrderRejected)
    ]


def make_fill_warning(changed_orders: list[str]) -> str | None:
    """The run warning of section 10.10.3: the count of the changed orders and the oldest of them.

    Each line starts with its time, so the smallest line is the oldest.
    """
    if not changed_orders:
        return None
    return f"Changed orders: {len(changed_orders)}. Earliest: {min(changed_orders)}."


def read_trades(engine: BacktestEngine, exchanges: dict[str, str] | None = None) -> list[BacktestTrade]:
    """The fills of all orders, oldest first. `exchanges` gives the real exchange of each symbol when the instruments
    are on a simulated venue. Without it, the exchange is the venue."""
    trades: list[BacktestTrade] = []
    for order in engine.cache.orders():
        symbol = str(order.instrument_id.symbol)
        venue = str(order.instrument_id.venue)
        exchange = venue if exchanges is None else exchanges.get(symbol, venue)
        for event in order.events():
            if not isinstance(event, OrderFilled):
                continue
            commission = event.commission
            trades.append(
                BacktestTrade(
                    time_utc=datetime.fromtimestamp(event.ts_event / NANOSECONDS_PER_SECOND, tz=UTC),
                    side=find_side_name(event.order_side),
                    quantity_shares=event.last_qty.as_decimal(),
                    price_usd=event.last_px.as_decimal(),
                    commission_usd=Decimal(0) if commission is None else commission.as_decimal(),
                    symbol=symbol,
                    exchange=exchange,
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


@dataclass(frozen=True)
class EngineInputs:
    """The strategy code and the ticks of one engine run. `changed_orders` gets the lines of the fill warning."""

    code: str
    config_fields: dict[str, object]
    open_ticks: list[list[TradeTick]]
    last_close_ticks: list[TradeTick]
    changed_orders: list[str] | None = None


def create_config(config_class: type[StrategyConfig], fields: dict[str, object]) -> StrategyConfig:
    """Raises StrategyFileError when a single-instrument strategy runs on a universe, which gives no such fields."""
    try:
        # readability-exception: the StrategyConfig stub has no such fields. The user subclass must define
        # them (docs/architecture/strategy.md section 9.2).
        return config_class(**fields)  # pyright: ignore[reportArgumentType]
    except TypeError as error:
        if "instrument_id" not in fields and any(name in str(error) for name in ("instrument_id", "bar_type")):
            raise StrategyFileError(SINGLE_INSTRUMENT_ON_UNIVERSE_MESSAGE) from error
        raise


def run_engine(engine: BacktestEngine, inputs: EngineInputs, work_directory: Path) -> None:
    """Loads the strategy classes, makes the configuration, adds the open ticks, and runs the engine.

    Raises StrategyFailedError with the strategy error.
    """
    handler_errors: list[str] = []
    reduced_orders: list[str] = []
    ticks = [tick for ticks in inputs.open_ticks for tick in ticks] + inputs.last_close_ticks
    if ticks:
        engine.add_data(ticks)
    try:
        strategy_class, config_class = load_strategy_classes(inputs.code, work_directory)
        config = create_config(config_class, inputs.config_fields)
        checked_class = record_handler_errors(strategy_class, handler_errors)
        open_times_ns = {
            ticks[0].instrument_id: [tick.ts_event for tick in ticks] for ticks in inputs.open_ticks if ticks
        }
        order_class = fill_at_next_open(checked_class, open_times_ns, reduced_orders)
        engine.add_strategy(order_class(config))
        engine.run()
    except StrategyFileError as error:
        raise StrategyFailedError(str(error)) from error
    except Exception as error:
        # readability-exception: any error of the user code ends the backtest with its traceback (G1).
        raise StrategyFailedError("".join(traceback.format_exception(error))) from error
    if handler_errors:
        raise StrategyFailedError(handler_errors[0])
    # The log file still catches errors outside the `on_*` methods, for example in a timer callback.
    error_log = read_error_log(work_directory)
    if error_log:
        raise StrategyFailedError(error_log)
    if inputs.changed_orders is not None:
        inputs.changed_orders.extend(reduced_orders + read_refused_orders(engine))


@dataclass(frozen=True)
class HeldOrder:
    instrument_id: InstrumentId
    side: OrderSide
    send: Callable[[], None]


class HeldOrderCache:
    """The engine cache, with each held order in `orders_inflight_count`. The engine has no such order until its open
    tick. A strategy that sees no order would send the order a second time."""

    def __init__(self, engine_cache: Any, held_orders: dict[str, HeldOrder]) -> None:
        self.engine_cache = engine_cache
        self.held_orders = held_orders

    def __getattr__(self, name: str) -> Any:
        return getattr(self.engine_cache, name)

    def orders_inflight_count(
        self,
        venue: Venue | None = None,
        instrument_id: InstrumentId | None = None,
        strategy_id: StrategyId | None = None,
        account_id: AccountId | None = None,
        side: OrderSide | None = None,
    ) -> int:
        """Each held order belongs to the strategy of this run, on the only account of its venue."""
        held_count = sum(
            venue in {None, held.instrument_id.venue}
            and instrument_id in {None, held.instrument_id}
            and side in {None, held.side}
            for held in self.held_orders.values()
        )
        return self.engine_cache.orders_inflight_count(venue, instrument_id, strategy_id, account_id, side) + held_count


class NextOpenOrders(Strategy):
    """Sends each market order only after the next open tick of its instrument (section 10.10.3).

    The engine then fills the order at this open, for all instruments alike. Its pre-trade check uses this price and
    the cash after the fills before, so it refuses a buy that the cash cannot pay. The engine would end the run on such
    a fill. An instrument without a later open tick goes at once: the order fills at the last close, and the last price
    is this close (`make_last_close_tick`).

    All names have the prefix `_atrade_`, because this class comes before the user class in the method order.
    """

    _atrade_open_times_ns: dict[InstrumentId, list[int]]
    _atrade_reduced_orders: list[str]
    _atrade_waiting_orders: dict[str, HeldOrder]
    _atrade_closing_instruments: set[InstrumentId]

    @property
    def cache(self) -> Any:
        return HeldOrderCache(super().cache, self._atrade_waiting_orders)

    def _atrade_send_at_next_open(self, instrument_id: InstrumentId, side: OrderSide, send: Callable[[], None]) -> None:
        times_ns = self._atrade_open_times_ns.get(instrument_id, [])
        index = bisect_right(times_ns, self.clock.timestamp_ns())
        if index == len(times_ns):
            send()
            return
        waiting_orders = self._atrade_waiting_orders
        name = f"next-open-{self.clock.timestamp_ns()}-{len(waiting_orders)}"
        waiting_orders[name] = HeldOrder(instrument_id, side, send)
        # 1 nanosecond apart. The last close tick of the instrument comes after the last alert: each order sees the cash after the fill of the order before.
        self.clock.set_time_alert_ns(name, times_ns[index] + len(waiting_orders), self._atrade_send_waiting_order)

    def _atrade_send_waiting_order(self, event: TimeEvent) -> None:
        self._atrade_waiting_orders.pop(event.name).send()

    def _atrade_fit_to_cash(self, order: Any) -> Any:
        """`order`, or a smaller order when the free cash pays for only a part of it at the last tick: the price of
        the fill.

        The tick holds a part of the bar volume. The engine fills the rest of a larger order 1 price step higher,
        so that part of the check adds the step. The engine ends the run on a fill above the cash.
        """
        open_tick = self.cache.trade(order.instrument_id)
        account = self.portfolio.account(order.instrument_id.venue)
        free_cash = None if account is None else account.balance_free()
        if order.side != OrderSide.BUY or open_tick is None or free_cash is None:
            return order
        price = open_tick.price.as_decimal()
        if order.quantity.as_decimal() > open_tick.size.as_decimal():
            price += Decimal(1).scaleb(-open_tick.price.precision)
        quantity = math.floor(free_cash.as_decimal() / price)
        if quantity < 1 or quantity >= order.quantity.as_decimal():
            return order
        self._atrade_reduced_orders.append(
            f"{self.clock.utc_now():%Y-%m-%d %H:%M} UTC: BUY {order.quantity} {order.instrument_id.symbol}"
            f" reduced to {quantity} at {open_tick.price}"
        )
        return self.order_factory.market(order.instrument_id, order.side, Quantity.from_int(quantity))

    def submit_order(self, order: Any, *args: Any, **kwargs: Any) -> None:
        if order.order_type != OrderType.MARKET:
            super().submit_order(order, *args, **kwargs)
            return
        parent = super()
        self._atrade_send_at_next_open(
            order.instrument_id,
            order.side,
            lambda: parent.submit_order(self._atrade_fit_to_cash(order), *args, **kwargs),
        )

    def close_position(self, position: Position, *args: Any, **kwargs: Any) -> None:
        # The position stays open until the next open. A second close would sell the position twice.
        closing_instruments = self._atrade_closing_instruments
        if position.instrument_id in closing_instruments:
            return
        parent = super()

        def close() -> None:
            closing_instruments.discard(position.instrument_id)
            parent.close_position(position, *args, **kwargs)

        closing_instruments.add(position.instrument_id)
        side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
        self._atrade_send_at_next_open(position.instrument_id, side, close)


def fill_at_next_open[StrategyClass: type](
    strategy_class: StrategyClass,
    open_times_ns: dict[InstrumentId, list[int]],
    reduced_orders: list[str],
) -> StrategyClass:
    """A subclass of `strategy_class` with the order rule of `NextOpenOrders`."""
    fields = {
        "_atrade_open_times_ns": open_times_ns,
        "_atrade_reduced_orders": reduced_orders,
        "_atrade_waiting_orders": {},
        "_atrade_closing_instruments": set[InstrumentId](),
    }
    subclass = type(strategy_class.__name__, (NextOpenOrders, strategy_class), fields)
    subclass.__module__ = strategy_class.__module__
    subclass.__qualname__ = strategy_class.__qualname__
    return cast("StrategyClass", subclass)


def record_handler_errors[StrategyClass: type](strategy_class: StrategyClass, errors: list[str]) -> StrategyClass:
    """A subclass of `strategy_class` that adds the traceback of each error of its `on_*` methods to `errors`.

    The engine logs a handler error and does not raise it. `logger_flush()` only asks the log writer thread to
    write, so the error log file can still be empty when the child reads it.
    """

    def wrap(method: Callable[..., object]) -> Callable[..., object]:
        @functools.wraps(method)
        def call(*args: object, **kwargs: object) -> object:
            try:
                return method(*args, **kwargs)
            except Exception as error:
                errors.append("".join(traceback.format_exception(error)))
                raise

        return call

    handlers = {
        name: wrap(method)
        for name in dir(strategy_class)
        if name.startswith("on_") and inspect.isfunction(method := getattr(strategy_class, name))
    }
    subclass = type(strategy_class.__name__, (strategy_class,), handlers)
    subclass.__module__ = strategy_class.__module__
    subclass.__qualname__ = strategy_class.__qualname__
    return cast("StrategyClass", subclass)


def run_strategy_on_bars(
    run: StrategyRun, work_directory: Path, changed_orders: list[str] | None = None
) -> list[BacktestTrade]:
    """Returns the trades of the strategy on `run.bars`, in the instrument currency.

    `changed_orders` gets the lines of the fill warning. Raises StrategyFailedError with the strategy error.
    """
    request = run.request
    instrument = request.single_instrument
    all_bars = run.look_back_bars + run.bars
    nautilus_instrument = create_instrument(instrument, all_bars)
    bar_type = BarType.from_str(request.bar_period.external_bar_type(nautilus_instrument.id))
    wrangler = create_wrangler(nautilus_instrument, request.bar_period)
    nautilus_bars = wrangler.process_record_batch_bytes(
        convert_bars_to_arrow_bytes(round_up_volumes(run.bars), request.bar_period)
    )
    engine = create_engine(
        starting_cash=run.starting_cash,
        currency=instrument.currency,
        venue=nautilus_instrument.venue,
        look_back_catalog=create_look_back_catalog(run.look_back_bars, wrangler, request.bar_period, work_directory),
        work_directory=work_directory,
    )
    engine.add_instrument(nautilus_instrument)
    engine.add_data(nautilus_bars)
    # The parameter values of a parameter sweep run replace the defaults (docs/architecture/backtest.md 10.11.2).
    config_fields: dict[str, object] = {
        **(request.parameters or {}),
        "instrument_id": nautilus_instrument.id,
        "bar_type": bar_type,
    }
    open_ticks = [make_open_ticks(nautilus_instrument, run.bars)]
    last_close_ticks = [make_last_close_tick(nautilus_instrument, run.bars, request.bar_period)] if run.bars else []
    inputs = EngineInputs(run.code, config_fields, open_ticks, last_close_ticks, changed_orders)
    run_engine(engine, inputs, work_directory)
    return read_trades(engine)
