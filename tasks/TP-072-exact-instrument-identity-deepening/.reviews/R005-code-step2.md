## Code Review: Step 2 — Deepen backend Exact Instrument Identity implementation (Iteration 2)

### Verdict: APPROVE

### Summary

All five R004 issues are fixed. The `ExactInstrumentIdentity.CreateInstrumentKey()` no longer emits `ibkrConid`. The `TryNormalizeExistingInstrumentKey` parse-and-reconstruct path drops `ibkrConid` and reconstructs via the single canonical path. The SQL backfill `concat_ws` now aliases `ibkr_conid` into `providerSymbolId` instead of emitting a separate `ibkrConid=` segment. All workspace test expected strings are updated and include durable `Assert.DoesNotContain("ibkrConid")` guardrails. Contract tests (20/20), workspace tests (30/30), and backtesting tests (47/47) all pass. Full solution builds with zero warnings and zero errors.

### Issues Found

*None at critical or important severity.*

### Pattern Violations

- **None.** The single runtime path for canonical key construction, parse-and-reconstruct for legacy normalization, and SQL backfill aliasing (not emitting) `ibkr_conid` all follow the design intent consistently.

### Test Gaps

*None remaining.* The three test gaps from R004 are all addressed:
- ✅ `Assert.DoesNotContain("ibkrConid")` added to all workspace normalizer and instrument-key tests
- ✅ SQL backfill guardrail test (`Assert.DoesNotContain("ibkrConid", sql)`) added to `PostgresWorkspaceWatchlistSqlTests`
- ✅ Edge-case contract test `NormalizeExistingInstrumentKey_PrefersProviderSymbolIdWhenLegacyIbkrConidDiffers` added — tests the scenario where `providerSymbolId=X` and `ibkrConid=Y` with X ≠ Y

### Suggestions

1. **`WorkspaceWatchlistInstrumentKey.Create()` retains `ibkrConid` as a parameter.** This is correct (it delegates through `ExactInstrumentIdentity.Create()` which stores it as metadata but excludes it from the key). A brief code comment noting that `ibkrConid` is passed through for metadata-only storage would help future readers at `WorkspaceWatchlistInstrumentKey.cs:9`.

2. **`NormalizeReplacement_DeduplicatesOnlyExactInstrumentKeys...`** could add an explicit `Assert.DoesNotContain("ibkrConid", symbol.InstrumentKey, StringComparison.OrdinalIgnoreCase)` on the IBKR-provider entry (3rd element in `Assert.Collection`) for defense in depth — optional, not blocking.

3. **The SQL backfill aliasing of `ibkr_conid` → `providerSymbolId`** (line 57 of `PostgresWorkspaceWatchlistSql.cs`) is a one-off legacy repair path as allowed by the completion criteria. Step 3/5 documentation should make explicit that this is an SQL-level alias for legacy rows only — runtime code already constructs keys through the single `Create()` path.

4. **Step 3/5 documentation** should explicitly state that `IbkrConid` remains a stored record property (provider-specific metadata) but is excluded from canonical `instrumentKey` / `pinKey` emission. This is already the behavior — just needs documentation.

5. **Backtesting module confirmed clean:** All 47 backtesting tests pass without changes. `BacktestRequestValidator.NormalizeSymbol` calls `MarketDataSymbolIdentity.Create(...)` without `ibkrConid`, and all identity flows through `ExactInstrumentIdentity` — no Step 2 work needed in `ATrade.Backtesting/`.

6. **Frontend `instrumentIdentity.ts` still emits `ibkrConid`** in `createProvisionalInstrumentKey` — this is expected to be addressed in Step 4 (frontend identity handoff).
