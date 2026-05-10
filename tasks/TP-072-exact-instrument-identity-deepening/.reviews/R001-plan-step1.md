## Plan Review: Step 1 — Pin provider-neutral identity/key contract tests first

### Verdict: APPROVE

### Summary

The four checkboxes in Step 1 cover the right test-first outcomes: backing the
canonical key contract, legacy-key normalization, frontend provisional keys, and
saved-backtest identity persistence.  Each outcome is scoped at the right level
— a meaningful behavioural assertion, not an implementation checklist.  The
current codebase makes it clear which assertions will need to change, and the
worker has enough context to write concrete failing tests before touching the
implementation in Steps 2–4.  The plan is sufficient to proceed.

### Issues Found

*None at critical or important severity.*

### Missing Items

*None.*  The four outcomes span the provider-neutral key contract, backward
compatibility with legacy `ibkrConid`-bearing keys, the frontend provisional-key
path, and saved backtest run identity — all the seams the task touches.

### Suggestions

1.  **Distinguish "field present" from "segment absent in key."**  
    The `ExactInstrumentIdentity` record will continue to carry `IbkrConid` as a
    metadata field even after the canonical key stops emitting it.  The backend
    contract tests in checkbox 1 should clearly assert both that
    `identity.IbkrConid` is populated (when an IBKR instrument is supplied) and
    that `identity.InstrumentKey` does **not** contain `ibkrConid=`.  Naming
    test methods with this distinction (e.g.
    `InstrumentKey_ExcludesIbkrConid_WhenConidIsPresent`) will make the contract
    unambiguous in future reviews.

2.  **Legacy-key normalization will need a parse-and-reconstruct path.**  
    Today `TryNormalizeExistingInstrumentKey` only validates length and
    whitespace; it does not parse/reconstruct the key.  Checkbox 2's tests will
    likely need to call a new (or renamed) normalizer that actually parses a
    legacy `ibkrConid`-bearing key and returns a canonical key *without* the
    `ibkrConid` segment.  The worker should be aware this is more than just
    updating assertions — it may require defining the normalization entry point
    in Step 1's tests before the implementation lands in Step 2.

3.  **Watchlist InstrumentKey tests cascade automatically, but verify the
    cascade.**  
    `WorkspaceWatchlistInstrumentKey.Create(...)` delegates to
    `ExactInstrumentIdentity.Create(...).InstrumentKey`.  Updating the core
    contract tests will force the watchlist tests to pass or fail accordingly,
    so no separate watchlist-key checkbox is needed.  However, the worker should
    confirm after the Step 2 implementation that
    `WorkspaceWatchlistInstrumentKeyTests.Normalize_CreatesStableProviderMarketInstrumentKey`
    (which today asserts `ibkrConid=265598` in the key) and the JSON serialisation
    test both cleanly pass with the updated canonical shape.

4.  **Backtesting identity types are largely provider-neutral already.**  
    `BacktestResultSymbolEnvelope` and `BacktestRunUpdateSymbolPayload` already
    carry `provider`, `providerSymbolId`, `symbol`, `assetClass`, `exchange`,
    `currency` without an `ibkrConid` field.  The saved-backtest tests in
    checkbox 4 should therefore focus on verifying that the *persisted and
    displayed* identity tuple is the full set of provider-neutral fields and
    that no new `ibkrConid` segment leaks into stored JSON or SignalR payloads.
