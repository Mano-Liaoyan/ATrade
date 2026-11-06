"""find_account (docs/architecture/strategy.md section 9.8.2)."""

from typing import cast

from nautilus_trader.model import Venue
from nautilus_trader.trading import Strategy

from atrade.strategy import FORWARD_TEST_VENUE, find_account

NASDAQ = Venue("NASDAQ")
ACCOUNT = "the account"


class FakeStrategy:
    """The 2 members of a Strategy that find_account uses."""

    def __init__(self, account_venue: Venue | None = None) -> None:
        self.account_venue = account_venue
        self.warnings: list[str] = []

    @property
    def portfolio(self) -> FakeStrategy:
        return self

    @property
    def log(self) -> FakeStrategy:
        return self

    def account(self, venue: Venue) -> str | None:
        return ACCOUNT if venue == self.account_venue else None

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def test_a_backtest_uses_the_account_of_the_instrument_venue() -> None:
    strategy = FakeStrategy(NASDAQ)

    assert find_account(cast(Strategy, strategy), NASDAQ) == ACCOUNT
    assert strategy.warnings == []


def test_a_forward_test_uses_the_account_of_the_forward_test_venue() -> None:
    strategy = FakeStrategy(FORWARD_TEST_VENUE)

    assert find_account(cast(Strategy, strategy), NASDAQ) == ACCOUNT
    assert strategy.warnings == []


def test_each_strategy_instance_warns_1_time_when_no_account_exists() -> None:
    first_strategy, second_strategy = FakeStrategy(), FakeStrategy()

    for _ in range(3):
        assert find_account(cast(Strategy, first_strategy), NASDAQ) is None
    assert find_account(cast(Strategy, second_strategy), NASDAQ) is None

    assert first_strategy.warnings == ["No account on the venues NASDAQ and ATRADE. No buy is sent."]
    assert len(second_strategy.warnings) == 1
