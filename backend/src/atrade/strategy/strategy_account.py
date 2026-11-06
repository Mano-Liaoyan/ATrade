"""The account of a running strategy, for generated code (docs/architecture/strategy.md section 9.8.2).

A backtest has its account on the venue of the instruments (ADR 0003). A forward test has 1 account on the venue
FORWARD_TEST_VENUE for all instrument venues (ADR 0007).
"""

from typing import Any
from weakref import WeakSet

from nautilus_trader.model import Venue
from nautilus_trader.trading import Strategy

FORWARD_TEST_VENUE = Venue("ATRADE")
# Generated code can call find_account on each bar. Each strategy instance writes the warning 1 time only.
warned_strategies: WeakSet[Strategy] = WeakSet()


def find_account(strategy: Strategy, instrument_venue: Venue) -> Any | None:
    account = strategy.portfolio.account(instrument_venue) or strategy.portfolio.account(FORWARD_TEST_VENUE)
    if account is None and strategy not in warned_strategies:
        warned_strategies.add(strategy)
        strategy.log.warning(f"No account on the venues {instrument_venue} and {FORWARD_TEST_VENUE}. No buy is sent.")
    return account
