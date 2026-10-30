"""Import check program: lists and checks the detections of the Databento import. Real PostgreSQL."""

import logging

import psycopg
import pytest

from atrade.app.databento_check import main

INSERT_DETECTIONS = """
    INSERT INTO stock_split (symbol, exchange, currency, ex_date_utc, split_ratio, source, confirmation, recorded_at_utc)
    VALUES ('GONE', 'NASDAQ', 'USD', '2020-01-08T00:00:00Z', 2, 'databento_import', NULL, now());
    INSERT INTO databento_symbol_link (old_symbol, new_symbol, exchange, change_day)
    VALUES ('SQ', 'XYZ', 'NYSE', '2025-01-21');
"""


@pytest.fixture
def detections(database_url: str, monkeypatch: pytest.MonkeyPatch) -> str:
    with psycopg.connect(database_url) as connection:
        connection.execute(INSERT_DETECTIONS)
    monkeypatch.setenv("DATABASE_URL", database_url)
    return database_url


def test_the_program_lists_the_waiting_splits_and_the_unchecked_links(
    detections: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    main([])

    assert "ID 1: GONE NASDAQ USD, ex-date 2020-01-08, split ratio 2" in caplog.text
    assert "SQ to XYZ on NYSE, from 2025-01-21" in caplog.text


def test_the_program_confirms_all_except_the_rejected_splits(detections: str, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    main(["--accept", "--reject-split", "1"])

    assert "Confirmed 0 stock splits, rejected 1, and checked 1 symbol links." in caplog.text
    with psycopg.connect(detections) as connection:
        row = connection.execute("SELECT confirmation FROM stock_split").fetchone()
    assert row == ("import_rejected",)


def test_the_program_does_not_reject_without_accept(detections: str, caplog: pytest.LogCaptureFixture) -> None:
    with pytest.raises(SystemExit) as stop:
        main(["--reject-split", "1"])

    assert stop.value.code == 1
    assert "--reject-split needs --accept" in caplog.text
