"""Settings: values come from environment variables, and live trading mode stops the start."""

import pytest
from pydantic import ValidationError

from atrade.foundation.settings import Settings


def test_refuses_live_trading_mode_and_names_the_reason() -> None:
    with pytest.raises(ValidationError, match="trading_mode 'live' is not allowed"):
        Settings(database_url="postgresql://localhost/atrade", trading_mode="live")


def test_reads_settings_from_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/atrade")
    monkeypatch.setenv("ATRADE_TRADING_MODE", "paper")

    settings = Settings()  # pyright: ignore[reportCallIssue] readability-exception: pydantic-settings fills required fields from the environment.

    assert settings.database_url == "postgresql://db.example/atrade"
    assert settings.trading_mode == "paper"
