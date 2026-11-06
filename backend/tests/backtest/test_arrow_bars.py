"""The Arrow form of the bars: prices and volumes in decimal128(38, 16). SQL division of a stock split stores more
than 16 decimal places (market_data.md section 8.13.3)."""

# pyarrow 26 has no type stubs.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

from datetime import UTC, datetime
from decimal import Decimal

import pyarrow
import pytest

from atrade.backtest.arrow_bars import convert_bars_to_arrow_bytes
from atrade.backtest.strategy_engine_run import create_instrument, create_wrangler
from atrade.foundation.bar import Bar, BarPeriod
from atrade.foundation.instrument import Instrument

BAR_START_UTC = datetime(2026, 1, 2, tzinfo=UTC)
INSTRUMENT = Instrument(symbol="SPLT", exchange="NASDAQ", currency="USD")


def convert_and_read(bar: Bar) -> dict[str, Decimal]:
    arrow_bytes = convert_bars_to_arrow_bytes([bar], BarPeriod.ONE_DAY)
    row = pyarrow.ipc.open_stream(arrow_bytes).read_all().to_pylist()[0]
    return {name: row[name] for name in ("open", "high", "low", "close", "volume")}


def test_values_with_more_than_16_decimal_places_are_rounded_half_even_to_16() -> None:
    bar = Bar(
        start_utc=BAR_START_UTC,
        open=Decimal("11202.29999999999999999999999943948"),
        high=Decimal("1.00000000000000015"),
        low=Decimal("1.00000000000000005"),
        close=Decimal("75473798400.00000000000000001207791200000"),
        volume=Decimal("5.302880658436213991769547325368024691358024691358"),
    )

    assert convert_and_read(bar) == {
        "open": Decimal("11202.3000000000000000"),
        "high": Decimal("1.0000000000000002"),
        "low": Decimal("1.0000000000000000"),
        "close": Decimal("75473798400.0000000000000000"),
        "volume": Decimal("5.3028806584362140"),
    }


def test_a_value_with_more_significant_digits_than_the_default_decimal_context_is_rounded() -> None:
    value = Decimal("1234567890123.12345678901234567")
    bar = Bar(start_utc=BAR_START_UTC, open=value, high=value, low=value, close=value, volume=value)

    assert set(convert_and_read(bar).values()) == {Decimal("1234567890123.1234567890123457")}


def test_values_with_up_to_16_decimal_places_do_not_change() -> None:
    bar = Bar(
        start_utc=BAR_START_UTC,
        open=Decimal("123.4567890123456789"),
        high=Decimal("200.5"),
        low=Decimal("0.0000000000000001"),
        close=Decimal(150),
        volume=Decimal(1000000),
    )

    assert convert_and_read(bar) == {
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
    }


def make_split_adjusted_bar(price: Decimal, split_ratio: Decimal) -> Bar:
    adjusted_price = price / split_ratio
    return Bar(
        start_utc=BAR_START_UTC,
        open=adjusted_price,
        high=adjusted_price,
        low=adjusted_price,
        close=adjusted_price,
        volume=Decimal(1000) * split_ratio,
    )


@pytest.mark.parametrize(
    ("price", "split_ratio"),
    [
        (Decimal("150.25"), Decimal(1) / Decimal(3)),
        (Decimal("150.25"), Decimal(4) / Decimal(3)),
        (Decimal("1.75"), Decimal(3) / Decimal(2)),
        (Decimal("0.51"), Decimal(7)),
    ],
)
def test_a_split_adjusted_bar_goes_through_arrow_to_the_wrangler(price: Decimal, split_ratio: Decimal) -> None:
    bar = make_split_adjusted_bar(price, split_ratio)
    arrow_bytes = convert_bars_to_arrow_bytes([bar], BarPeriod.ONE_DAY)

    table = pyarrow.ipc.open_stream(arrow_bytes).read_all()
    assert table.schema.field("close").type == pyarrow.decimal128(38, 16)
    assert abs(table.column("close")[0].as_py() - bar.close) < Decimal("1e-15")
    nautilus_instrument = create_instrument(INSTRUMENT, [bar])
    wrangler = create_wrangler(nautilus_instrument, BarPeriod.ONE_DAY)
    assert len(wrangler.process_record_batch_bytes(arrow_bytes)) == 1
