"""Symbol links: a link moves bars only before 2024-07-01 and with proof (docs/architecture/market_data.md section
8.8.4). Real PostgreSQL and hand-made DBN files."""

from datetime import UTC, date, datetime
from pathlib import Path
from typing import LiteralString

import psycopg
import pytest

from atrade.market_data import import_databento_files
from tests.fakes.databento import DbnFile, write_dbn_files
from tests.market_data.test_stock_split_import import (
    RENAME_IN_SUMMARY,
    SUMMARY_DAYS,
    TRADING_DAYS,
    create_bars,
    create_history_files,
    create_summary_file,
    read_bars,
    read_table,
)

LINKS: LiteralString = "SELECT old_symbol, new_symbol FROM databento_symbol_link ORDER BY id"
MEMBERS: LiteralString = "SELECT rank, symbol FROM us_universe_member ORDER BY quarter_start_utc, rank"
LATE = SUMMARY_DAYS[0].replace(year=2026)


def import_files(database_url: str, path: Path, files: list[DbnFile]) -> None:
    import_databento_files(database_url=database_url, file_paths=write_dbn_files(path, files))


def create_change(old_price: str, new_price: str, new_volume: int = 1000) -> list[DbnFile]:
    """OLDX trades to 2020-01-08 and NEWX starts on the next trading day. ANCH trades on all days."""
    old_bars = create_bars("OLDX", TRADING_DAYS[:3], [(old_price, old_price, 1000)] * 3)
    new_bars = create_bars("NEWX", TRADING_DAYS[3:], [(new_price, new_price, new_volume)] * 3)
    anchor_bars = create_bars("ANCH", TRADING_DAYS, [("30", "30", 500)] * 6)
    return create_history_files([*old_bars, *new_bars, *anchor_bars])


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


async def read_days(database_url: str, symbol: str) -> list[date]:
    return [bar.start_utc.date() for bar in await read_bars(database_url, symbol, end=LATE)]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("old_price", "new_price", "new_volume"),
    [
        pytest.param("10.05", "10.00", 1000, id="a delisted SPAC and an IPO open near 10 USD"),
        pytest.param("50", "50", 4000, id="the volume changes more than 3 times"),
        pytest.param("50", "50", 300, id="the volume falls more than 3 times"),
    ],
)
async def test_a_candidate_without_proof_gets_no_link_and_moves_no_bar(
    database_url: str, tmp_path: Path, old_price: str, new_price: str, new_volume: int
) -> None:
    import_files(database_url, tmp_path, create_change(old_price, new_price, new_volume))

    assert read_table(database_url, LINKS) == []
    assert await read_days(database_url, "OLDX") == TRADING_DAYS[:3]
    assert await read_days(database_url, "NEWX") == TRADING_DAYS[3:]


@pytest.mark.anyio
async def test_a_link_with_proof_moves_the_bars_and_a_second_import_moves_them_again(
    database_url: str, tmp_path: Path
) -> None:
    files = create_change("50", "50.2")

    import_files(database_url, tmp_path / "first", files)
    import_files(database_url, tmp_path / "second", files)

    assert read_table(database_url, LINKS) == [("OLDX", "NEWX")]
    assert await read_days(database_url, "OLDX") == []
    assert await read_days(database_url, "NEWX") == TRADING_DAYS


@pytest.mark.anyio
async def test_a_delisted_spac_and_an_unrelated_ipo_in_the_equs_summary_period_are_not_merged(
    database_url: str, tmp_path: Path
) -> None:
    import_files(
        database_url,
        tmp_path / "history",
        create_history_files(create_bars("SPAC", TRADING_DAYS[:2], [("10.05", "10.05", 1000)] * 2)),
    )
    summary = create_summary_file(
        [("SPAC", SUMMARY_DAYS[0], "10.05"), ("IPOX", SUMMARY_DAYS[1], "10"), ("IPOX", SUMMARY_DAYS[2], "11")]
    )

    import_files(database_url, tmp_path / "summary", [summary])

    assert read_table(database_url, LINKS) == [("SPAC", "IPOX")]
    assert await read_days(database_url, "SPAC") == [*TRADING_DAYS[:2], SUMMARY_DAYS[0]]
    assert await read_days(database_url, "IPOX") == SUMMARY_DAYS[1:3]


@pytest.mark.anyio
async def test_a_reused_ticker_in_the_equs_summary_period_gets_no_link_and_the_saved_quarters_stay(
    database_url: str, tmp_path: Path
) -> None:
    quarter = datetime(2025, 1, 2, tzinfo=UTC)
    insert_member(database_url, quarter, 1, "SQ")
    insert_member(database_url, quarter, 2, "XYZ")
    history = [
        *create_bars("SQ", TRADING_DAYS[:2], [("100", "100", 1000)] * 2),
        *create_bars("XYZ", TRADING_DAYS[:1], [("7", "7", 1000)]),
    ]
    import_files(database_url, tmp_path / "history", create_history_files(history))

    import_files(database_url, tmp_path / "summary", [RENAME_IN_SUMMARY])

    assert read_table(database_url, LINKS) == []
    assert await read_days(database_url, "SQ") == [*TRADING_DAYS[:2], *SUMMARY_DAYS[:2]]
    assert await read_days(database_url, "XYZ") == [TRADING_DAYS[0], *SUMMARY_DAYS[2:4]]
    assert read_table(database_url, MEMBERS) == [(1, "SQ"), (2, "XYZ")]


@pytest.mark.anyio
async def test_a_rename_in_the_equs_summary_period_keeps_the_old_symbol_in_the_saved_quarters(
    database_url: str, tmp_path: Path
) -> None:
    insert_member(database_url, datetime(2025, 1, 2, tzinfo=UTC), 1, "SQ")
    history = create_bars("SQ", TRADING_DAYS[:2], [("100", "100", 1000)] * 2)
    import_files(database_url, tmp_path / "history", create_history_files(history))

    import_files(database_url, tmp_path / "summary", [RENAME_IN_SUMMARY])

    assert read_table(database_url, LINKS) == [("SQ", "XYZ")]
    assert read_table(database_url, MEMBERS) == [(1, "SQ")]
    assert await read_days(database_url, "SQ") == [*TRADING_DAYS[:2], *SUMMARY_DAYS[:2]]


@pytest.mark.anyio
async def test_a_new_symbol_with_older_saved_bars_is_a_reused_ticker_and_gets_no_link(
    database_url: str, tmp_path: Path
) -> None:
    older_bar = create_bars("NEWX", TRADING_DAYS[:1], [("7", "7", 1000)])
    import_files(database_url, tmp_path / "first", create_history_files(older_bar))

    import_files(
        database_url,
        tmp_path / "second",
        create_history_files(
            [
                *create_bars("OLDX", TRADING_DAYS[1:3], [("50", "50", 1000)] * 2),
                *create_bars("NEWX", TRADING_DAYS[3:], [("50", "50", 1000)] * 3),
                *create_bars("ANCH", TRADING_DAYS, [("30", "30", 500)] * 6),
            ]
        ),
    )

    assert read_table(database_url, LINKS) == []
    assert await read_days(database_url, "OLDX") == TRADING_DAYS[1:3]
    assert await read_days(database_url, "NEWX") == [TRADING_DAYS[0], *TRADING_DAYS[3:]]
