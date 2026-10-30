"""Databento import: stock split adjustment at save time and symbol change links.

Real PostgreSQL, hand-made DBN files of the Databento fake, and the IBKR fake
(docs/architecture/market_data.md sections 8.8.3, 8.8.4, and 8.13.1).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import LiteralString

import psycopg
import pytest

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import (
    BarRequest,
    BarSource,
    DatabentoImportReport,
    ImportCheckError,
    check_import_detections,
    import_databento_files_with_ibkr,
    read_saved_bars,
)
from tests.fakes.databento import (
    CLOSE_PRICE,
    DAILY_SCHEMA,
    OPENING_PRICE,
    STATISTICS_SCHEMA,
    DailyRecord,
    DbnFile,
    StatisticRecord,
    write_dbn_files,
)
from tests.fakes.ibkr import FakeGatewayConnection

CHECKED_AT_UTC = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
PURCHASE_START = date(2018, 5, 1)
PURCHASE_END = date(2024, 7, 1)
SOURCE_ORDER = [BarSource.DATABENTO, BarSource.IBKR]
# Monday 2020-01-06 to Friday 2020-01-10, then Monday 2020-01-13.
TRADING_DAYS = [date(2020, 1, 6) + timedelta(days=offset) for offset in (0, 1, 2, 3, 4, 7)]


@dataclass(frozen=True)
class DailyBar:
    """One Databento daily bar of a NASDAQ symbol. The official open and close are the open and the close."""

    symbol: str
    day: date
    open: Decimal
    close: Decimal
    volume: int


def utc_day(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def create_bars(symbol: str, days: list[date], prices: list[tuple[str, str, int]]) -> list[DailyBar]:
    """`prices` holds (open, close, volume) for each day."""
    return [
        DailyBar(symbol, day, Decimal(open_price), Decimal(close), volume)
        for day, (open_price, close, volume) in zip(days, prices, strict=True)
    ]


def create_history_files(bars: list[DailyBar], nyse_symbols: frozenset[str] = frozenset()) -> list[DbnFile]:
    """The 4 history files. The symbols in `nyse_symbols` are listed on NYSE, all other symbols on NASDAQ."""
    daily_records: dict[str, list[DailyRecord]] = {"XNAS.ITCH": [], "XNYS.PILLAR": []}
    statistic_records: dict[str, list[StatisticRecord]] = {"XNAS.ITCH": [], "XNYS.PILLAR": []}
    for bar in bars:
        dataset = "XNYS.PILLAR" if bar.symbol in nyse_symbols else "XNAS.ITCH"
        high = max(bar.open, bar.close)
        low = min(bar.open, bar.close)
        daily_records[dataset].append(DailyRecord(bar.symbol, bar.day, bar.open, high, low, bar.close, bar.volume))
        statistic_records[dataset] += [
            StatisticRecord(bar.symbol, bar.day, OPENING_PRICE, bar.open),
            StatisticRecord(bar.symbol, bar.day, CLOSE_PRICE, bar.close),
        ]
    return [
        DbnFile(dataset, DAILY_SCHEMA, PURCHASE_START, PURCHASE_END, daily_records=daily_records[dataset])
        for dataset in daily_records
    ] + [
        DbnFile(dataset, STATISTICS_SCHEMA, PURCHASE_START, PURCHASE_END, statistic_records=statistic_records[dataset])
        for dataset in statistic_records
    ]


def ibkr_bars(days: list[date], closes: list[str]) -> list[Bar]:
    return [
        Bar(
            start_utc=utc_day(day),
            open=Decimal(close),
            high=Decimal(close),
            low=Decimal(close),
            close=Decimal(close),
            volume=Decimal(1000),
        )
        for day, close in zip(days, closes, strict=True)
    ]


def serve_same_closes(gateway: FakeGatewayConnection, bars: list[DailyBar], exchange: str = "NASDAQ") -> None:
    """IBKR has the same closes as Databento: no stock split."""
    instrument = Instrument(symbol=bars[0].symbol, exchange=exchange, currency="USD")
    gateway.historical_bars[instrument] = ibkr_bars([bar.day for bar in bars], [str(bar.close) for bar in bars])


@pytest.fixture
async def gateway() -> FakeGatewayConnection:
    connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    await connection.connect()
    return connection


async def run_import(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection, files: list[DbnFile]
) -> DatabentoImportReport:
    return await import_databento_files_with_ibkr(
        database_url=database_url, file_paths=write_dbn_files(tmp_path, files), gateway=gateway
    )


async def read_bars(database_url: str, symbol: str, exchange: str = "NASDAQ") -> list[Bar]:
    instrument = Instrument(symbol=symbol, exchange=exchange, currency="USD")
    time_range = TimeRange(utc_day(PURCHASE_START), utc_day(PURCHASE_END))
    saved_bars = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(instrument, BarPeriod.ONE_DAY, time_range),
        source_order=SOURCE_ORDER,
    )
    return saved_bars.bars


def read_table(database_url: str, query: LiteralString) -> list[tuple[object, ...]]:
    with psycopg.connect(database_url) as connection:
        return connection.execute(query).fetchall()


STOCK_SPLIT_QUERY: LiteralString = """
    SELECT symbol, exchange, currency, ex_date_utc, split_ratio, source, confirmation FROM stock_split ORDER BY id
"""
SYMBOL_LINK_QUERY: LiteralString = """
    SELECT old_symbol, new_symbol, exchange, change_day, checked_at_utc FROM databento_symbol_link ORDER BY id
"""


@pytest.mark.anyio
async def test_a_step_in_the_ratio_of_the_ibkr_close_to_the_databento_close_is_a_stock_split(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """A 2-for-1 split on 2020-01-08. Databento has the prices that are not adjusted. IBKR adjusts its TRADES bars."""
    days = TRADING_DAYS[:4]
    databento_bars = create_bars(
        "SPLT", days, [("200", "202", 1000), ("202", "204", 1100), ("102", "103", 2400), ("103", "104", 2300)]
    )
    gateway.historical_bars[Instrument(symbol="SPLT", exchange="NASDAQ", currency="USD")] = ibkr_bars(
        days, ["101.05", "102.10", "103.00", "104.00"]
    )

    await run_import(database_url, tmp_path, gateway, create_history_files(databento_bars))

    assert read_table(database_url, STOCK_SPLIT_QUERY) == [
        ("SPLT", "NASDAQ", "USD", utc_day(days[2]), Decimal(2), "databento_import", "bar_evidence")
    ]
    bars = await read_bars(database_url, "SPLT")
    assert [(bar.open, bar.close, bar.volume) for bar in bars] == [
        (Decimal(100), Decimal(101), Decimal(2000)),
        (Decimal(101), Decimal(102), Decimal(2200)),
        (Decimal(102), Decimal(103), Decimal(2400)),
        (Decimal(103), Decimal(104), Decimal(2300)),
    ]


@pytest.mark.anyio
async def test_a_constant_ratio_of_the_closes_is_no_stock_split(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """The IBKR close differs a little from the official close, but the ratio does not step."""
    days = TRADING_DAYS[:3]
    databento_bars = create_bars("STAY", days, [("50", "51", 1000), ("51", "52", 1100), ("52", "53", 1000)])
    gateway.historical_bars[Instrument(symbol="STAY", exchange="NASDAQ", currency="USD")] = ibkr_bars(
        days, ["51.05", "51.95", "53.10"]
    )

    await run_import(database_url, tmp_path, gateway, create_history_files(databento_bars))

    assert read_table(database_url, STOCK_SPLIT_QUERY) == []
    bars = await read_bars(database_url, "STAY")
    assert [bar.close for bar in bars] == [Decimal(51), Decimal(52), Decimal(53)]


@pytest.mark.anyio
async def test_the_detection_rule_finds_a_stock_split_of_an_instrument_that_stopped_trading(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """GONE stops 2 days before the end of the purchase. Its close of 80 then the next open of 40 is a ratio of 2,
    and the volume goes up. The stock split waits for the user check: the bars do not change yet."""
    gone_bars = create_bars(
        "GONE", TRADING_DAYS[:4], [("79", "80", 1000), ("80", "80", 1000), ("40", "41", 2100), ("41", "42", 2000)]
    )
    other_bars = create_bars("OTHR", TRADING_DAYS, [("10", "10", 500)] * len(TRADING_DAYS))
    serve_same_closes(gateway, other_bars)

    report = await run_import(database_url, tmp_path, gateway, create_history_files([*gone_bars, *other_bars]))

    assert read_table(database_url, STOCK_SPLIT_QUERY) == [
        ("GONE", "NASDAQ", "USD", utc_day(TRADING_DAYS[2]), Decimal(2), "databento_import", None)
    ]
    assert [(split.instrument.symbol, split.ex_date) for split in report.stock_splits] == [("GONE", TRADING_DAYS[2])]
    bars = await read_bars(database_url, "GONE")
    assert [bar.close for bar in bars] == [Decimal(80), Decimal(80), Decimal(41), Decimal(42)]


@pytest.mark.anyio
async def test_a_price_drop_without_a_volume_rise_is_no_stock_split(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    gone_bars = create_bars("DROP", TRADING_DAYS[:3], [("79", "80", 1000), ("40", "41", 900), ("41", "42", 800)])
    other_bars = create_bars("OTHR", TRADING_DAYS, [("10", "10", 500)] * len(TRADING_DAYS))
    serve_same_closes(gateway, other_bars)

    await run_import(database_url, tmp_path, gateway, create_history_files([*gone_bars, *other_bars]))

    assert read_table(database_url, STOCK_SPLIT_QUERY) == []


def create_symbol_change(
    gateway: FakeGatewayConnection,
    *,
    new_first_day: date = TRADING_DAYS[3],
    new_first_open: str = "100.80",
    new_on_nyse: bool = False,
) -> list[DbnFile]:
    """SQ trades to 2020-01-08 and XYZ starts on the next trading day. ANCH trades on all days."""
    old_bars = create_bars("SQ", TRADING_DAYS[:3], [("99", "99.5", 1000), ("99.5", "100", 1000), ("100", "100", 900)])
    new_days = [day for day in TRADING_DAYS if day >= new_first_day]
    new_bars = create_bars(
        "XYZ", new_days, [(new_first_open, "101", 1000)] + [("101", "101", 1000)] * (len(new_days) - 1)
    )
    anchor_bars = create_bars("ANCH", TRADING_DAYS, [("10", "10", 500)] * len(TRADING_DAYS))
    nyse_symbols = frozenset({"XYZ"}) if new_on_nyse else frozenset[str]()
    serve_same_closes(gateway, anchor_bars)
    # IBKR gives the history of the old symbol under the new symbol.
    linked_bars = [DailyBar("XYZ", bar.day, bar.open, bar.close, bar.volume) for bar in [*old_bars, *new_bars]]
    serve_same_closes(gateway, linked_bars, "NYSE" if new_on_nyse else "NASDAQ")
    return create_history_files([*old_bars, *new_bars, *anchor_bars], nyse_symbols)


@pytest.mark.anyio
async def test_the_import_links_an_old_symbol_to_a_new_symbol_and_saves_the_old_history_under_the_new_symbol(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    report = await run_import(database_url, tmp_path, gateway, create_symbol_change(gateway))

    assert read_table(database_url, SYMBOL_LINK_QUERY) == [("SQ", "XYZ", "NASDAQ", TRADING_DAYS[3], None)]
    assert [(link.old_symbol, link.new_symbol) for link in report.symbol_links] == [("SQ", "XYZ")]
    bars = await read_bars(database_url, "XYZ")
    assert [bar.start_utc.date() for bar in bars] == TRADING_DAYS
    assert await read_bars(database_url, "SQ") == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "symbol_change",
    [
        pytest.param({"new_first_day": TRADING_DAYS[4]}, id="the days are not adjacent trading days"),
        pytest.param({"new_first_open": "101.10"}, id="the prices differ by more than 1%"),
        pytest.param({"new_on_nyse": True}, id="the listing exchanges differ"),
    ],
)
async def test_the_import_does_not_link_when_one_condition_is_false(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection, symbol_change: dict[str, object]
) -> None:
    files = create_symbol_change(gateway, **symbol_change)  # pyright: ignore[reportArgumentType] readability-exception: the parameters hold the keyword arguments.

    report = await run_import(database_url, tmp_path, gateway, files)

    assert read_table(database_url, SYMBOL_LINK_QUERY) == []
    assert report.symbol_links == []
    assert [bar.start_utc.date() for bar in await read_bars(database_url, "SQ")] == TRADING_DAYS[:3]


async def import_a_detected_split(database_url: str, tmp_path: Path, gateway: FakeGatewayConnection) -> list[DbnFile]:
    """GONE stopped trading. The detection rule finds its 2-for-1 split on the third day."""
    gone_bars = create_bars("GONE", TRADING_DAYS[:3], [("79", "80", 1000), ("40", "41", 2100), ("41", "42", 2000)])
    other_bars = create_bars("OTHR", TRADING_DAYS, [("10", "10", 500)] * len(TRADING_DAYS))
    serve_same_closes(gateway, other_bars)
    files = create_history_files([*gone_bars, *other_bars])
    await run_import(database_url, tmp_path, gateway, files)
    return files


@pytest.mark.anyio
async def test_the_user_check_confirms_a_detected_split_and_changes_the_bars_before_the_ex_date(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    await import_a_detected_split(database_url, tmp_path, gateway)

    detections = check_import_detections(
        database_url=database_url, rejected_split_ids=set(), checked_at_utc=CHECKED_AT_UTC
    )

    assert [split.instrument.symbol for split in detections.stock_splits] == ["GONE"]
    assert [row[6] for row in read_table(database_url, STOCK_SPLIT_QUERY)] == ["import_check"]
    bars = await read_bars(database_url, "GONE")
    assert [(bar.close, bar.volume) for bar in bars] == [
        (Decimal(40), Decimal(2000)),
        (Decimal(41), Decimal(2100)),
        (Decimal(42), Decimal(2000)),
    ]


@pytest.mark.anyio
async def test_a_rejected_split_does_not_change_the_bars_also_after_a_second_import(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    files = await import_a_detected_split(database_url, tmp_path, gateway)

    check_import_detections(database_url=database_url, rejected_split_ids={1}, checked_at_utc=CHECKED_AT_UTC)
    await run_import(database_url, tmp_path / "again", gateway, files)

    assert [row[6] for row in read_table(database_url, STOCK_SPLIT_QUERY)] == ["import_rejected"]
    assert [bar.close for bar in await read_bars(database_url, "GONE")] == [Decimal(80), Decimal(41), Decimal(42)]


@pytest.mark.anyio
async def test_the_user_check_records_the_check_time_of_each_symbol_link(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    await run_import(database_url, tmp_path, gateway, create_symbol_change(gateway))

    check_import_detections(database_url=database_url, rejected_split_ids=set(), checked_at_utc=CHECKED_AT_UTC)

    assert read_table(database_url, SYMBOL_LINK_QUERY) == [("SQ", "XYZ", "NASDAQ", TRADING_DAYS[3], CHECKED_AT_UTC)]


@pytest.mark.anyio
async def test_the_user_check_refuses_an_id_that_is_not_a_waiting_split(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    await import_a_detected_split(database_url, tmp_path, gateway)

    with pytest.raises(ImportCheckError, match="ID 7"):
        check_import_detections(database_url=database_url, rejected_split_ids={7}, checked_at_utc=CHECKED_AT_UTC)

    assert [row[6] for row in read_table(database_url, STOCK_SPLIT_QUERY)] == [None]
