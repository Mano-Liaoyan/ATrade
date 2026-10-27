"""Settings: values come from environment variables, and live trading mode stops the start."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from atrade.foundation.settings import Settings

DATABASE_URL = "postgresql://localhost/atrade"


def test_refuses_live_trading_mode_and_names_the_reason() -> None:
    with pytest.raises(ValidationError, match="trading_mode 'live' is not allowed"):
        Settings(database_url=DATABASE_URL, trading_mode="live")


def test_reads_settings_from_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/atrade")
    monkeypatch.setenv("ATRADE_TRADING_MODE", "paper")
    monkeypatch.setenv("ATRADE_IBKR_ACCOUNT_ID", "DU1234567")
    monkeypatch.setenv("ATRADE_IBKR_HOST", "gateway.example")
    monkeypatch.setenv("ATRADE_IBKR_PAPER_PORT", "4002")
    monkeypatch.setenv("ATRADE_IBKR_WEB_CLIENT_ID", "7")
    monkeypatch.setenv("ATRADE_FORWARD_TEST_CLIENT_ID_FIRST", "20")
    monkeypatch.setenv("ATRADE_FORWARD_TEST_CLIENT_ID_LAST", "25")
    monkeypatch.setenv("ATRADE_LOCAL_PAPER_CAPITAL_USD", "25000.50")

    settings = Settings()  # pyright: ignore[reportCallIssue] readability-exception: pydantic-settings fills required fields from the environment.

    assert settings.database_url == "postgresql://db.example/atrade"
    assert settings.trading_mode == "paper"
    assert settings.ibkr_account_id == "DU1234567"
    assert settings.ibkr_host == "gateway.example"
    assert settings.ibkr_paper_port == 4002
    assert settings.ibkr_web_client_id == 7
    assert settings.forward_test_client_id_first == 20
    assert settings.forward_test_client_id_last == 25
    assert settings.local_paper_capital_usd == Decimal("25000.50")


def test_uses_the_documented_ibkr_defaults() -> None:
    settings = Settings(database_url=DATABASE_URL)

    assert settings.ibkr_account_id is None
    assert settings.ibkr_host == "ib-gateway"
    assert settings.ibkr_paper_port == 4004
    assert settings.ibkr_web_client_id == 1
    assert settings.forward_test_client_id_first == 10
    assert settings.forward_test_client_id_last == 13


def test_treats_an_empty_account_id_as_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATRADE_IBKR_ACCOUNT_ID", "")

    settings = Settings(database_url=DATABASE_URL)

    assert settings.ibkr_account_id is None


def test_refuses_client_id_0_for_the_web_process() -> None:
    with pytest.raises(ValidationError, match="client ID 0"):
        Settings(database_url=DATABASE_URL, ibkr_web_client_id=0)


def test_refuses_a_client_id_that_is_a_multiple_of_1000() -> None:
    with pytest.raises(ValidationError, match="multiple of 1000"):
        Settings(database_url=DATABASE_URL, forward_test_client_id_first=1000, forward_test_client_id_last=1001)


def test_refuses_a_forward_test_client_id_range_that_ends_before_it_starts() -> None:
    with pytest.raises(ValidationError, match="range"):
        Settings(database_url=DATABASE_URL, forward_test_client_id_first=13, forward_test_client_id_last=10)


def test_refuses_a_web_client_id_inside_the_forward_test_range() -> None:
    with pytest.raises(ValidationError, match="Web client ID 11 is inside the forward test client ID range"):
        Settings(database_url=DATABASE_URL, ibkr_web_client_id=11)
