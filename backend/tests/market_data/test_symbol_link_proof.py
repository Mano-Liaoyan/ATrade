"""Symbol links that need the user check: a link moves bars only with proof (docs/architecture/market_data.md section
8.8.4). Real PostgreSQL and hand-made DBN files."""

from datetime import UTC, datetime
from pathlib import Path
from typing import LiteralString

import psycopg
import pytest

from atrade.market_data import ImportCheckError, check_import_detections, import_databento_files
from tests.fakes.databento import DbnFile, write_dbn_files
from tests.market_data.test_stock_split_import import (
    RENAME_IN_SUMMARY,
    SUMMARY_DAYS,
    TRADING_DAYS,
    create_bars,
    create_history_files,
    read_bars,
    read_table,
)

CHECKED_AT_UTC = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
LINK_STATES: LiteralString = "SELECT old_symbol, new_symbol, state FROM databento_symbol_link ORDER BY id"
LATE = SUMMARY_DAYS[0].replace(year=2026)


def import_files(database_url: str, path: Path, files: list[DbnFile]) -> None:
    import_databento_files(database_url=database_url, file_paths=write_dbn_files(path, files))


def create_change(old_price: str, new_price: str, new_volume: int = 1000) -> list[DbnFile]:
    """OLDX trades to 2020-01-08 and NEWX starts on the next trading day. ANCH trades on all days."""
    old_bars = create_bars("OLDX", TRADING_DAYS[:3], [(old_price, old_price, 1000)] * 3)
    new_bars = create_bars("NEWX", TRADING_DAYS[3:], [(new_price, new_price, new_volume)] * 3)
    anchor_bars = create_bars("ANCH", TRADING_DAYS, [("30", "30", 500)] * 6)
    return create_history_files([*old_bars, *new_bars, *anchor_bars])


async def assert_bars_did_not_move(database_url: str) -> None:
    assert [bar.start_utc.date() for bar in await read_bars(database_url, "OLDX")] == TRADING_DAYS[:3]
    assert [bar.start_utc.date() for bar in await read_bars(database_url, "NEWX")] == TRADING_DAYS[3:]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old_price", "new_price", "new_volume"),
    [
        pytest.param("10.05", "10.00", 1000, id="a delisted SPAC and an IPO open near 10 USD"),
        pytest.param("50", "50", 4000, id="the volume changes more than 3 times"),
        pytest.param("50", "50", 300, id="the volume falls more than 3 times"),
    ],
)
async def test_a_link_without_proof_waits_for_the_user_check_and_moves_no_bar(
    database_url: str, tmp_path: Path, old_price: str, new_price: str, new_volume: int
) -> None:
    import_files(database_url, tmp_path, create_change(old_price, new_price, new_volume))

    assert read_table(database_url, LINK_STATES) == [("OLDX", "NEWX", "waiting")]
    await assert_bars_did_not_move(database_url)


@pytest.mark.anyio
async def test_a_link_with_proof_moves_the_bars_and_a_second_import_moves_them_again(
    database_url: str, tmp_path: Path
) -> None:
    files = create_change("50", "50.2")

    import_files(database_url, tmp_path / "first", files)
    import_files(database_url, tmp_path / "second", files)

    assert read_table(database_url, LINK_STATES) == [("OLDX", "NEWX", "moved")]
    assert await read_bars(database_url, "OLDX") == []
    assert [bar.start_utc.date() for bar in await read_bars(database_url, "NEWX")] == TRADING_DAYS


def import_rename_in_summary(database_url: str, path: Path) -> None:
    history = create_history_files(create_bars("SQ", TRADING_DAYS[:2], [("100", "100", 1000)] * 2))
    import_files(database_url, path / "history", history)
    import_files(database_url, path / "summary", [RENAME_IN_SUMMARY])


@pytest.mark.anyio
async def test_a_rename_in_the_equs_summary_period_has_no_exchange_proof_and_moves_no_bar(
    database_url: str, tmp_path: Path
) -> None:
    import_rename_in_summary(database_url, tmp_path)

    assert read_table(database_url, LINK_STATES) == [("SQ", "XYZ", "waiting")]
    assert [bar.start_utc.date() for bar in await read_bars(database_url, "XYZ", end=LATE)] == SUMMARY_DAYS[2:4]
    assert [bar.start_utc.date() for bar in await read_bars(database_url, "SQ", end=LATE)] == [
        *TRADING_DAYS[:2],
        *SUMMARY_DAYS[:2],
    ]


@pytest.mark.anyio
async def test_the_user_check_moves_the_bars_of_a_waiting_link(database_url: str, tmp_path: Path) -> None:
    import_rename_in_summary(database_url, tmp_path)

    check_import_detections(database_url=database_url, rejected_split_ids=set(), checked_at_utc=CHECKED_AT_UTC)

    assert read_table(database_url, LINK_STATES) == [("SQ", "XYZ", "moved")]
    assert await read_bars(database_url, "SQ", end=LATE) == []
    assert [bar.start_utc.date() for bar in await read_bars(database_url, "XYZ", end=LATE)] == [
        *TRADING_DAYS[:2],
        *SUMMARY_DAYS[:4],
    ]
    assert read_table(database_url, "SELECT symbol FROM daily_bar_summary") == [("XYZ",)]


@pytest.mark.anyio
async def test_a_rejected_link_moves_no_bar_and_the_next_import_does_not_list_it(
    database_url: str, tmp_path: Path
) -> None:
    files = create_change("10.05", "10.00")
    import_files(database_url, tmp_path / "first", files)
    link_id = read_table(database_url, "SELECT id FROM databento_symbol_link")[0][0]

    check_import_detections(
        database_url=database_url,
        rejected_split_ids=set(),
        rejected_link_ids={int(str(link_id))},
        checked_at_utc=CHECKED_AT_UTC,
    )
    report = import_databento_files(database_url=database_url, file_paths=write_dbn_files(tmp_path / "second", files))

    assert report.symbol_links == []
    assert read_table(database_url, LINK_STATES) == [("OLDX", "NEWX", "rejected")]
    await assert_bars_did_not_move(database_url)


def test_the_user_check_refuses_an_id_that_is_not_a_waiting_link(database_url: str, tmp_path: Path) -> None:
    import_files(database_url, tmp_path, create_change("50", "50.2"))
    link_id = read_table(database_url, "SELECT id FROM databento_symbol_link")[0][0]

    with pytest.raises(ImportCheckError, match="symbol link"):
        check_import_detections(
            database_url=database_url,
            rejected_split_ids=set(),
            rejected_link_ids={int(str(link_id))},
            checked_at_utc=CHECKED_AT_UTC,
        )


def insert_member(database_url: str, quarter_start_utc: datetime, rank: int, symbol: str) -> None:
    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            INSERT INTO us_universe_member (
                quarter_start_utc, rank, symbol, exchange, currency, average_trading_value, last_ranking_day_utc
            )
            VALUES (%(quarter_start_utc)s, %(rank)s, %(symbol)s, 'NASDAQ', 'USD', 1000, %(quarter_start_utc)s)
            """,
            {"quarter_start_utc": quarter_start_utc, "rank": rank, "symbol": symbol},
        )


def test_a_move_changes_the_old_symbol_in_the_saved_quarters(database_url: str, tmp_path: Path) -> None:
    first_quarter = datetime(2019, 10, 1, tzinfo=UTC)
    second_quarter = datetime(2020, 1, 2, tzinfo=UTC)
    insert_member(database_url, first_quarter, 1, "OLDX")
    insert_member(database_url, second_quarter, 1, "OLDX")
    insert_member(database_url, second_quarter, 2, "NEWX")

    import_files(database_url, tmp_path, create_change("50", "50.2"))

    assert read_table(database_url, "SELECT rank, symbol FROM us_universe_member ORDER BY quarter_start_utc, rank") == [
        (1, "NEWX"),
        (1, "OLDX"),
        (2, "NEWX"),
    ]
