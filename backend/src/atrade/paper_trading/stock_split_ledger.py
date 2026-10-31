"""The owner ledger at a stock split: the check of one instrument, the ledger change, and the "Split check needed"
state with "Apply split" and "Keep ledger" (docs/architecture/paper_trading.md sections 11.11 and 11.13).

- One transaction writes the `stock_split` row of `market_data`, changes the stored bars, and writes all
  `split_adjustment` rows of the owners.
- The cash in lieu uses the last stored daily close before the ex-date. Without a stored daily bar, it uses the last
  IBKR daily close, which IBKR adjusted for the stock split already.
- The worker restarts the forward tests that trade the instrument (forward_test.md section 12.22).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

import psycopg

from atrade.foundation.clock import Clock
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection
from atrade.market_data import (
    SplitConfirmation,
    StockSplitCandidate,
    StockSplitChange,
    apply_stock_split,
    apply_stock_split_in_transaction,
    read_last_daily_bars,
)
from atrade.paper_trading import owner_ledger_store, split_check_store
from atrade.paper_trading.manual_order_ledger import OrderAmounts
from atrade.paper_trading.owner_ledger_store import LedgerEntry, Owner, OwnerPosition
from atrade.paper_trading.split_check_store import NewSplitCheck, SplitCheck
from atrade.paper_trading.stock_split_rules import calculate_split_adjustments, find_split_evidence

type CheckResult = Literal["no_split", "incomplete", "confirmed", "split_check_needed"]


class SplitCheckNotFoundError(LookupError):
    pass


class SplitCheckResolvedError(Exception):
    """The instrument is not in the "Split check needed" state for this split check."""


@dataclass(frozen=True)
class InstrumentCheck:
    """One instrument of the daily check. `candidate` is evidence A, or None. `check_day_utc` is the ex-date of a
    stock split without evidence A. At the last try, incomplete evidence gives the "Split check needed" state."""

    account: str
    instrument: Instrument
    account_quantity: Decimal
    candidate: StockSplitCandidate | None
    check_day_utc: datetime
    is_last_try: bool


@dataclass(frozen=True)
class InstrumentCheckOutcome:
    result: CheckResult
    # The forward tests that held the instrument before a confirmed stock split. The worker restarts them.
    forward_test_ids: list[int]


NO_SPLIT = InstrumentCheckOutcome(result="no_split", forward_test_ids=[])


def find_owner_quantities(entries: list[LedgerEntry], instrument: Instrument) -> dict[Owner, Decimal]:
    return {
        position.owner: position.quantity
        for position in owner_ledger_store.sum_owner_positions(entries)
        if position.instrument == instrument and position.quantity > 0
    }


def find_forward_test_ids(owner_quantities: dict[Owner, Decimal]) -> list[int]:
    return [owner.forward_test_id for owner in owner_quantities if owner.forward_test_id is not None]


def find_instrument_positions(entries: list[LedgerEntry], instrument: Instrument) -> list[OwnerPosition]:
    return [
        position for position in owner_ledger_store.sum_owner_positions(entries) if position.instrument == instrument
    ]


@dataclass(frozen=True)
class LedgerChange:
    account: str
    change: StockSplitChange
    account_quantity_after: Decimal
    confirmation: SplitConfirmation


class StockSplitLedger:
    def __init__(self, *, database_url: str, gateway_connection: GatewayConnection, clock: Clock) -> None:
        self.database_url = database_url
        self.clock = clock
        self.amounts = OrderAmounts(gateway_connection=gateway_connection, clock=clock)

    async def check_instrument(self, check: InstrumentCheck) -> InstrumentCheckOutcome:
        """Section 11.11 for one instrument. Raises GatewayRequestError when IBKR does not answer."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            entries = await owner_ledger_store.select_entries(connection, account=check.account)
            split_checks = await split_check_store.select_split_checks(connection, account=check.account, status=None)
            candidate = check.candidate
            if candidate is not None and await split_check_store.has_stock_split_check(connection, candidate.id):
                # "Keep ledger" leaves the candidate. The check does not check it again.
                candidate = None
        instrument_checks = [item for item in split_checks if item.instrument == check.instrument]
        if any(item.status == "needed" for item in instrument_checks):
            return NO_SPLIT
        owner_quantities = find_owner_quantities(entries, check.instrument)
        quantity_before = sum(owner_quantities.values(), Decimal(0))
        if quantity_before == 0:
            if candidate is None:
                return NO_SPLIT
            # No owner holds the instrument: evidence A alone confirms the stock split.
            await apply_stock_split(
                database_url=self.database_url,
                change=to_change(candidate),
                confirmation="bar_evidence",
                recorded_at_utc=self.clock.read_now_utc(),
            )
            return InstrumentCheckOutcome(result="confirmed", forward_test_ids=[])
        evidence = find_split_evidence(
            bar_ratio=None if candidate is None else candidate.split_ratio,
            quantity_before=quantity_before,
            quantity_after=check.account_quantity,
        )
        if evidence is None or any(
            item.status == "kept"
            and item.account_quantity_before == quantity_before
            and item.account_quantity_after == check.account_quantity
            for item in instrument_checks
        ):
            return NO_SPLIT
        if evidence.kind == "confirmed" and candidate is not None:
            await self.change_ledger(
                LedgerChange(
                    account=check.account,
                    change=to_change(candidate),
                    account_quantity_after=check.account_quantity,
                    confirmation="both_evidences",
                ),
                split_check_id=None,
            )
            return InstrumentCheckOutcome(result="confirmed", forward_test_ids=find_forward_test_ids(owner_quantities))
        if evidence.kind in {"position_only", "bar_ratio_only"} and not check.is_last_try:
            return InstrumentCheckOutcome(result="incomplete", forward_test_ids=[])
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            await split_check_store.insert_split_check(
                connection,
                NewSplitCheck(
                    account=check.account,
                    instrument=check.instrument,
                    stock_split_id=None if candidate is None else candidate.id,
                    ex_date_utc=check.check_day_utc if candidate is None else candidate.ex_date_utc,
                    detected_ratio=evidence.ratio,
                    evidence="position_only" if evidence.kind == "confirmed" else evidence.kind,
                    account_quantity_before=quantity_before,
                    account_quantity_after=check.account_quantity,
                ),
                self.clock.read_now_utc(),
            )
            await connection.commit()
        return InstrumentCheckOutcome(result="split_check_needed", forward_test_ids=[])

    async def find_last_close(self, change: StockSplitChange) -> Decimal:
        """The last close before the ex-date in the old form."""
        bars = await read_last_daily_bars(
            database_url=self.database_url, instruments=[change.instrument], before_utc=change.ex_date_utc, bar_count=1
        )
        stored_bars = bars.get(change.instrument, [])
        if stored_bars:
            return stored_bars[-1].close
        return await self.amounts.read_last_close(change.instrument) * change.split_ratio

    async def change_ledger(self, ledger_change: LedgerChange, *, split_check_id: int | None) -> list[OwnerPosition]:
        """Writes the stock split, changes the stored bars, and writes the split adjustments in one transaction.
        With `split_check_id`, it also ends the state. Returns the owner positions of the instrument after the change.
        Raises StockSplitConfirmedError when market_data confirmed the stock split already."""
        change = ledger_change.change
        last_close = await self.find_last_close(change)
        usd_per_unit = await self.amounts.convert_to_usd(Decimal(1), change.instrument.currency)
        now_utc = self.clock.read_now_utc()
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            async with connection.transaction():
                entries = await owner_ledger_store.select_entries(connection, account=ledger_change.account)
                stock_split_id = await apply_stock_split_in_transaction(
                    connection, change=change, confirmation=ledger_change.confirmation, recorded_at_utc=now_utc
                )
                adjustments = calculate_split_adjustments(
                    owner_quantities=find_owner_quantities(entries, change.instrument),
                    split_ratio=change.split_ratio,
                    account_quantity_after=ledger_change.account_quantity_after,
                    last_close_before_ex_date=last_close,
                )
                await split_check_store.insert_split_adjustments(
                    connection,
                    account=ledger_change.account,
                    instrument=change.instrument,
                    stock_split_id=stock_split_id,
                    adjustments=[(adjustment, adjustment.cash_in_lieu * usd_per_unit) for adjustment in adjustments],
                    time_utc=now_utc,
                )
                if split_check_id is not None:
                    await split_check_store.write_resolution(
                        connection,
                        split_check_id=split_check_id,
                        status="applied",
                        stock_split_id=stock_split_id,
                        resolved_at_utc=now_utc,
                    )
            entries = await owner_ledger_store.select_entries(connection, account=ledger_change.account)
        return find_instrument_positions(entries, change.instrument)

    async def read_needed_check(self, split_check_id: int) -> SplitCheck:
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            split_check = await split_check_store.select_split_check(connection, split_check_id)
        if split_check is None:
            message = f"Split check {split_check_id} not found."
            raise SplitCheckNotFoundError(message)
        if split_check.status != "needed":
            message = f"{split_check.symbol} is not in the Split check needed state of split check {split_check_id}."
            raise SplitCheckResolvedError(message)
        return split_check

    async def apply_split(self, split_check_id: int) -> list[OwnerPosition]:
        """ "Apply split": the ledger change with the detected ratio. Raises SplitCheckNotFoundError,
        SplitCheckResolvedError, or StockSplitConfirmedError."""
        split_check = await self.read_needed_check(split_check_id)
        return await self.change_ledger(
            LedgerChange(
                account=split_check.account,
                change=StockSplitChange(
                    instrument=split_check.instrument,
                    ex_date_utc=split_check.ex_date_utc,
                    split_ratio=split_check.detected_ratio,
                ),
                account_quantity_after=split_check.account_quantity_after,
                confirmation="user_apply",
            ),
            split_check_id=split_check_id,
        )

    async def keep_ledger(self, split_check_id: int) -> SplitCheck:
        """ "Keep ledger": no ledger change and no bar change. The difference stays as "Unattributed"."""
        split_check = await self.read_needed_check(split_check_id)
        async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
            await split_check_store.write_resolution(
                connection,
                split_check_id=split_check_id,
                status="kept",
                stock_split_id=None,
                resolved_at_utc=self.clock.read_now_utc(),
            )
            await connection.commit()
        return split_check


def to_change(candidate: StockSplitCandidate) -> StockSplitChange:
    return StockSplitChange(
        instrument=candidate.instrument, ex_date_utc=candidate.ex_date_utc, split_ratio=candidate.split_ratio
    )


async def read_needed_split_checks(*, database_url: str, account: str | None) -> list[SplitCheck]:
    """The instruments in the "Split check needed" state."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await split_check_store.select_split_checks(connection, account=account, status="needed")


async def read_unrestarted_split_checks(*, database_url: str) -> list[tuple[SplitCheck, list[int]]]:
    """The applied split checks whose forward tests the worker did not restart yet, each with the forward tests that
    got a split adjustment."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        applied = await split_check_store.select_split_checks(connection, account=None, status="applied")
        return [
            (
                split_check,
                []
                if split_check.stock_split_id is None
                else await split_check_store.select_split_forward_test_ids(connection, split_check.stock_split_id),
            )
            for split_check in applied
            if split_check.restarted_at_utc is None
        ]


async def write_split_check_restarted(*, database_url: str, split_check_id: int, restarted_at_utc: datetime) -> None:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        await split_check_store.write_restarted(
            connection, split_check_id=split_check_id, restarted_at_utc=restarted_at_utc
        )
        await connection.commit()


async def read_owner_instruments(*, database_url: str, account: str) -> list[Instrument]:
    """The instruments that an owner of the account holds, for the stock split check."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        entries = await owner_ledger_store.select_entries(connection, account=account)
    positions = owner_ledger_store.sum_owner_positions(entries)
    return list(dict.fromkeys(position.instrument for position in positions if position.quantity > 0))


async def read_needed_split_checks_with_holders(*, database_url: str) -> list[tuple[Instrument, list[int]]]:
    """Each instrument in the "Split check needed" state, with the forward tests that hold it."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        needed = await split_check_store.select_split_checks(connection, account=None, status="needed")
        return [
            (split_check.instrument, await split_check_store.select_holding_forward_test_ids(connection, split_check))
            for split_check in needed
        ]
