## Plan Review: Step 3 — Update adapters and persistence consumers

### Verdict: APPROVE

### Summary

The four stated outcomes are meaningful and well-aligned with the PROMPT requirements. Importantly, **three of the four outcomes are already achieved** by the work done in Steps 1–2: the API route adapters have zero `ibkrConid` references, the watchlist persistence already routes all key construction through `ExactInstrumentIdentity.Create()`, and the backtesting module has zero `ibkrConid` references anywhere in its identity flow. Step 3 is therefore primarily a **verification and documentation** step. The plan is adequate to complete this — the worker will discover these facts during implementation and can adapt accordingly.

### Issues Found

*None at critical or important severity.*

### Missing Items

- **The plan doesn't acknowledge that most outcomes are already met.** After Steps 1–2, the `ibkrConid` parameter on `MarketDataSymbolIdentity.Create()` is retained only for the IBKR adapter (`IbkrMarketDataProvider`) and defaults to `null` elsewhere. All other callers (API routes, backtest validator, analysis intake, Timescale models) use the provider-neutral tuple only. The worker should be aware they are verifying rather than implementing new adapter/persistence behavior for the first three checkboxes.

- **Legacy repair/backfill documentation is underspecified.** The last checkbox says "Legacy repair/backfill behavior documented in code/tests where unavoidable" but doesn't say **what** to document or **where**. The concrete items to document are:
  1. The SQL `concat_ws` backfill in `PostgresWorkspaceWatchlistSql.Initialize` (line ~57) which aliases `ibkr_conid` → `providerSymbolId` for legacy rows — this is a one-off repair that must not be repeated in new code.
  2. The `TryNormalizeExistingInstrumentKey` parse-and-reconstruct path in `ExactInstrumentIdentity.cs` which accepts legacy `ibkrConid`-bearing keys only to normalize them forward.
  3. The `IbkrConid` record property on `ExactInstrumentIdentity` and `WorkspaceWatchlistSymbol` which is stored as **provider-specific metadata** (not an identity dimension) — this distinction is critical for future readers.

### Suggestions

1. **Update the first checkbox to read more like:** "Verify API route/query adapters accept only provider-neutral fields and add guardrail assertions." Since the API already has zero `ibkrConid` references, the real deliverable is confirmation + any missing guardrail assertions in API-level integration tests.

2. **Add a concrete guardrail check:** grep for `ibkrConid` / `ibkr_conid` / `conid` across `src/ATrade.Api/` and confirm zero matches. Similarly for `src/ATrade.Backtesting/`. This is a cheap cross-check that the adapters haven't regressed.

3. **The `WorkspaceWatchlistSymbolInput.IbkrConid` property** on the input model (line 17 of `WorkspaceWatchlistModels.cs`) is correctly retained — it's the intake shape that clients send, and the normalizer routes it through `ExactInstrumentIdentity.Create()` which stores it as metadata only. A brief code comment on the property noting "provider-specific metadata, excluded from canonical key" would prevent future confusion.

4. **`MarketDataSymbolIdentity.Create(ibkrConid=null)` still has the parameter in the signature.** Only the IBKR adapter paths (`IbkrMarketDataProvider.cs:527,536`) pass a non-null value. All other 6 call sites pass `null` (or omit it). Step 3 should note this is correctly scoped — no change needed, but worth confirming in a code comment.

5. **The backtesting `BacktestResultSymbolEnvelope` record** (line 234 of `BacktestingContracts.cs`) already carries the full provider-neutral tuple (`Symbol`, `Provider`, `ProviderSymbolId`, `AssetClass`, `Exchange`, `Currency`) with zero `ibkrConid`. Confirm this is intentional and matches the PROMPT requirement that "saved backtest runs persist and display the full provider-neutral tuple."

6. **Cross-step awareness from R005:** Step 2's review (R005 suggestion #3) noted the SQL backfill aliasing should be documented in Step 3/5. This plan's "legacy repair/backfill behavior documented" checkbox covers it, but make sure it includes the specific SQL line reference in `PostgresWorkspaceWatchlistSql.cs` and notes that the `ibkr_conid` column is retained for metadata only.
