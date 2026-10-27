"""Start of the Web process: settings that are not valid stop the start before any connection."""

import logging
from urllib.parse import urlsplit, urlunsplit

import pytest

from atrade.app.web import main


def test_does_not_start_in_live_trading_mode_and_writes_the_reason(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/atrade")
    monkeypatch.setenv("ATRADE_TRADING_MODE", "live")
    caplog.set_level(logging.ERROR)

    with pytest.raises(SystemExit) as stop:
        main()

    assert stop.value.code == 1
    assert "ATrade does not start" in caplog.text
    assert "trading_mode 'live' is not allowed" in caplog.text


def test_does_not_start_with_a_wrong_database_password_and_names_the_volume(
    migrated_database_url: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    parts = urlsplit(migrated_database_url)
    wrong_netloc = f"{parts.username}:not-the-password@{parts.hostname}:{parts.port}"
    monkeypatch.setenv("DATABASE_URL", urlunsplit(parts._replace(netloc=wrong_netloc)))
    monkeypatch.setenv("ATRADE_TRADING_MODE", "paper")
    caplog.set_level(logging.ERROR)

    with pytest.raises(SystemExit) as stop:
        main()

    assert stop.value.code == 1
    assert "PostgreSQL refused the password" in caplog.text
    assert "atrade-postgres18-data" in caplog.text
