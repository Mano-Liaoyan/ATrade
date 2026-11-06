"""The Arrow form of the bars: prices and volumes in decimal128(38, 16)."""

# pyarrow 26 has no type stubs.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

from datetime import UTC, datetime
from decimal import Decimal

import pyarrow

from atrade.backtest.arrow_bars import convert_bars_to_arrow_bytes
from atrade.foundation.bar import Bar, BarPeriod

BAR_START_UTC = datetime(2026, 1, 2, tzinfo=UTC)


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
