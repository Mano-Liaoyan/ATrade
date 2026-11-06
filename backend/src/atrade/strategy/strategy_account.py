"""The account of a running strategy, for generated code (docs/architecture/strategy.md section 9.8.2).

A backtest has its account on the venue of the instruments (ADR 0003). A forward test has 1 account on the venue
FORWARD_TEST_VENUE for all instrument venues (ADR 0007).
"""

from typing import Any

from nautilus_trader.model import Venue
from nautilus_trader.trading import Strategy

FORWARD_TEST_VENUE = Venue("ATRADE")


def find_account(strategy: Strategy, instrument_venue: Venue) -> Any | None:
    account = strategy.portfolio.account(instrument_venue)
    return strategy.portfolio.account(FORWARD_TEST_VENUE) if account is None else account
