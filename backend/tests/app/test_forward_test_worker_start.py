"""Start of the forward-test worker: settings that are not valid stop the start and the log names the reason."""

import logging

import pytest

from atrade.app.forward_test_worker import main


def test_does_not_start_when_the_bar_fetcher_client_id_is_in_the_forward_test_range(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/atrade")
    monkeypatch.setenv("ATRADE_IBKR_BAR_FETCHER_CLIENT_ID", "11")
    caplog.set_level(logging.ERROR)

    with pytest.raises(SystemExit) as stop:
        main()

    assert stop.value.code == 1
    assert "The forward-test worker does not start" in caplog.text
    assert "bar fetcher client ID 11 is inside the forward test client ID range" in caplog.text
