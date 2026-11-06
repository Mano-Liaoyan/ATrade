"""Bars with more than 16 decimal places: SQL division of a stock split stores them (market_data.md section 8.13.3)."""

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

INSTRUMENT = Instrument(symbol="SPLT", exchange="NASDAQ", currency="USD")


def make_split_adjusted_bar(price: Decimal, split_ratio: Decimal) -> Bar:
    adjusted_price = price / split_ratio
    return Bar(
        start_utc=datetime(2026, 1, 2, tzinfo=UTC),
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
    wrangler = create_wrangler(nautilus_instrument, BarPeriod.ONE_DAY, [bar])
    assert len(wrangler.process_record_batch_bytes(arrow_bytes)) == 1
