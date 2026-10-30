"""The NautilusTrader instruments and bars of the ATrade clients (docs/architecture/forward_test.md section 12.19)."""

from decimal import Decimal

from nautilus_trader.model import Bar as NautilusBar
from nautilus_trader.model import BarType, Currency, Equity, InstrumentId, Price, Quantity, Symbol, Venue

from atrade.foundation.bar import Bar, BarPeriod
from atrade.foundation.instrument import Instrument

# IBKR prices of stocks have 4 decimal places at most. The bars, the fills, and the instrument use the same precision.
PRICE_PRECISION = 4
VOLUME_PRECISION = 0
NANOSECONDS_PER_SECOND = 1_000_000_000


def create_instrument_id(instrument: Instrument) -> InstrumentId:
    """SYMBOL.<primary exchange>, for example AAPL.NASDAQ, like the IB adapter (section 12.17)."""
    return InstrumentId(Symbol(instrument.symbol), Venue(instrument.exchange))


def create_equity(instrument: Instrument) -> Equity:
    return Equity(
        create_instrument_id(instrument),
        Symbol(instrument.symbol),
        Currency.from_str(instrument.currency),
        PRICE_PRECISION,
        Price(10**-PRICE_PRECISION, PRICE_PRECISION),
        0,
        0,
    )


def create_price(value: Decimal) -> Price:
    return Price.from_str(f"{value:.{PRICE_PRECISION}f}")


def read_bar_period(bar_type: BarType) -> BarPeriod:
    """`AAPL.NASDAQ-1-DAY-LAST-EXTERNAL` -> `1-DAY`."""
    specification = str(bar_type).removeprefix(f"{bar_type.instrument_id}-")
    return BarPeriod(specification.rsplit("-", 2)[0])


def convert_bar(bar: Bar, bar_type: BarType, bar_period: BarPeriod) -> NautilusBar:
    """`ts_event` is the bar end, like the backtest bars: a strategy sees a bar only after its period is over."""
    bar_end_ns = int((bar.start_utc + bar_period.length).timestamp()) * NANOSECONDS_PER_SECOND
    return NautilusBar(
        bar_type,
        create_price(bar.open),
        create_price(bar.high),
        create_price(bar.low),
        create_price(bar.close),
        Quantity.from_str(f"{bar.volume:.{VOLUME_PRECISION}f}"),
        bar_end_ns,
        bar_end_ns,
    )
