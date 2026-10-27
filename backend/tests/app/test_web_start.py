"""Start of the Web process: settings that are not valid stop the start before any connection."""

import logging

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
