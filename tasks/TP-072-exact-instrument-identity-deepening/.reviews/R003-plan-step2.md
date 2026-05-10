## Plan Review: Step 2 — Deepen backend Exact Instrument Identity implementation

### Verdict: APPROVE

### Summary

The four checkboxes in Step 2 cover the right implementation outcomes: remove
`ibkrConid` from canonical key emission, keep IBKR alias handling provider‑specific,
enforce a single runtime key‑construction path, and normalize legacy key inputs
forward.  The Step 1 contract tests are already pinned and failing against the
current code — the TDD scaffolding is in place, and the expected shape of each
change is clearly defined by those tests.  The plan is sufficient to proceed.

### Issues Found

*None at critical or important severity.*

### Missing Items

*None.*  The four outcomes span the core `CreateInstrumentKey()` change, the
`TryNormalizeExistingInstrumentKey` upgrade from trim‑only to parse‑and‑reconstruct,
the SQL backfill repair in `PostgresWorkspaceWatchlistSql`, and the cascading
watchlist‑test updates called out in the previous review — all are either
explicitly covered by the checkboxes or naturally pulled in by the file scope.

### Suggestions

1.  **`TryNormalizeExistingInstrumentKey` needs a parse‑and‑reconstruct path.**
    Today it only trims whitespace and validates length — it does not inspect
    or rewrite key segments.  The Step 1 contract test
    `NormalizeExistingInstrumentKey_AcceptsLegacyIbkrConidSegmentAndNormalizesForward`
    expects the legacy key to come back *without* the `ibkrConid` segment.  This
    is more than adjusting an assertion; it requires parsing the `|`‑delimited
    key, extracting the known segment names (`provider`, `providerSymbolId`,
    `ibkrConid`, `symbol`, `exchange`, `currency`, `assetClass`), dropping
    `ibkrConid`, and reconstructing in the canonical order.  The R002 code
    review flagged two edge cases this normalizer should handle:
    - A legacy key where `ibkrConid` differs from a non‑empty `providerSymbolId`
    - A legacy key missing the `providerSymbolId` segment entirely (for IBKR
      keys, alias from `ibkrConid` into `providerSymbolId`).  
    The worker should handle both during implementation.

2.  **SQL backfill in `PostgresWorkspaceWatchlistSql.Initialize` emits `ibkrConid`.**
    The `concat_ws` expression at the bottom of the `Initialize` constant builds
    the `instrument_key` column with an `ibkrConid=` segment for legacy rows
    where the key is `NULL` or blank.  This is a one‑off legacy‑repair path
    (explicitly allowed by the completion criteria), but it must be updated to
    match the canonical format so new rows and back‑filled rows have consistent
    keys.  The file is in Step 2 scope (`src/ATrade.Workspaces/*`) — update the
    `concat_ws` to drop the `ibkrConid` segment at the same time as the
    `CreateInstrumentKey()` change.

3.  **Watchlist test expected strings cascade.**
    `WorkspaceWatchlistInstrumentKeyTests.Normalize_CreatesStableProviderMarketInstrumentKey`
    and `WatchlistSymbolJson_ExposesInstrumentKeyAndPinKeyAliases` both hardcode
    `ibkrConid=265598` in expected key strings.  These will break when
    `CreateInstrumentKey()` changes and should be updated in this step so the
    workspace test suite stays green.

4.  **`WorkspaceWatchlistIntakeTests.ExactUnpinValidatesAndNormalizesInstrumentKeyBeforeRepositoryCall`**
    calls `WorkspaceWatchlistInstrumentKey.Create(...)` to build the key it
    passes to `UnpinByInstrumentKeyAsync`.  This test will automatically pick up
    the corrected key shape once `CreateInstrumentKey()` is fixed — no separate
    assertion update needed, but the worker should verify it passes.

5.  **Backtesting code already provider‑neutral — confirm no regressions.**
    The backtesting module (contracts, validation, repository, SQL) carries no
    direct `ibkrConid` references — all identity flows through
    `MarketDataSymbolIdentity`, which delegates to `ExactInstrumentIdentity`.
    The `BacktestRequestValidator.NormalizeSymbol` method calls
    `MarketDataSymbolIdentity.Create(…)` with **no `ibkrConid` argument** for
    the provider‑identity path (the `ibkrConid` parameter defaults to `null`
    in the `Create` overload).  This is already correct and should remain
    unchanged.  The Step 1 backtest contract tests should pass cleanly when
    Step 2 is complete because the serialized `request_json` never contained an
    `ibkrConid` field.  No Step 2 work is needed in `ATrade.Backtesting/`.

6.  **Consider adding a deterministic sort to `CreateInstrumentKey()`.**
    The current implementation hard‑codes the segment order.  That is fine and
    consistent.  Any future segment additions should maintain this stable order.
    No action needed — just a note that the order is contractual and tested.
