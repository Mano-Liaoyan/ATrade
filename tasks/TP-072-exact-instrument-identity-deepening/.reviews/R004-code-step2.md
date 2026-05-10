## Code Review: Step 2 — Deepen backend Exact Instrument Identity implementation

### Verdict: REVISE

### Summary

The `ExactInstrumentIdentity.cs` core change is correct — `CreateInstrumentKey()` no longer emits `ibkrConid`, `TryNormalizeExistingInstrumentKey` now parses-and-reconstructs legacy keys into the provider-neutral format, and the new `ParseInstrumentKeySegments`/`GetSegmentValue` helpers are clean. All 6 contract tests and all 47 backtesting tests pass. However, **3 workspace tests fail** because their expected key strings still hardcode `ibkrConid` segments, and the **SQL backfill `concat_ws` still emits `ibkrConid`** — both were explicitly flagged in the R003 plan review and must be addressed before this step is complete.

### Issues Found

1. **[tests/ATrade.Workspaces.Tests/WorkspaceWatchlistInstrumentKeyTests.cs:22] [critical]** — `Normalize_CreatesStableProviderMarketInstrumentKey` expects `"provider=ibkr|providerSymbolId=265598|ibkrConid=265598|symbol=AAPL|..."` but the implementation now emits `"provider=ibkr|providerSymbolId=265598|symbol=AAPL|..."` (no `ibkrConid` segment). **Fix:** Remove `ibkrConid=265598|` from the expected string. Also add `Assert.DoesNotContain("ibkrConid", normalized.InstrumentKey)` to make the guardrail durable.

2. **[tests/ATrade.Workspaces.Tests/WorkspaceWatchlistNormalizerTests.cs:111] [critical]** — `Normalize_FillsManualStockDefaultsAndNormalizesMetadataForFutureProviderEnrichment` expects `"provider=ibkr|providerSymbolId=272093|ibkrConid=272093|symbol=MSFT|..."` but the implementation emits without `ibkrConid`. **Fix:** Remove `ibkrConid=272093|` from the expected string. Add `Assert.DoesNotContain("ibkrConid", normalized.InstrumentKey)`.

3. **[tests/ATrade.Workspaces.Tests/WorkspaceWatchlistNormalizerTests.cs:146] [critical]** — `Normalize_UsesManualUsdStockDefaultsWhenMetadataIsMissing` expects `"provider=manual|providerSymbolId=|ibkrConid=|symbol=NVDA|..."` but the implementation emits `"provider=manual|providerSymbolId=|symbol=NVDA|..."` (empty `ibkrConid` segment removed). **Fix:** Remove `ibkrConid=|` from the expected string. Add `Assert.DoesNotContain("ibkrConid", normalized.InstrumentKey)`.

4. **[src/ATrade.Workspaces/PostgresWorkspaceWatchlistSql.cs:58] [important]** — The `Initialize` SQL `concat_ws` backfill still emits an `ibkrConid` segment:
   ```sql
   'ibkrConid=' || COALESCE(ibkr_conid::text, ''),
   ```
   This means legacy rows repaired by this one-off backfill get `ibkrConid`-bearing keys, which is inconsistent with the canonical format for all new rows. The R003 plan review explicitly called this out: "it must be updated to match the canonical format so new rows and back-filled rows have consistent keys." **Fix:** Remove the `ibkrConid` line from `concat_ws`. The `ibkr_conid` column persists in the table for metadata, but the backfilled `instrument_key` should match the canonical shape.

5. **[tests/ATrade.Workspaces.Tests/WorkspaceWatchlistInstrumentKeyTests.cs:40] [minor]** — `WatchlistSymbolJson_ExposesInstrumentKeyAndPinKeyAliases` constructs a `WorkspaceWatchlistSymbol` using a hardcoded key containing `ibkrConid=265598`. While this test passes (it only tests JSON serialization of a manually-constructed object), it perpetuates the stale key format in test assertions. **Fix:** Update the key constant to the canonical format without `ibkrConid`.

### Pattern Violations

- **None.** The implementation approach — single runtime path via `Create()` for canonical key construction, parse-and-reconstruct for legacy normalization — is consistent and follows the design intent.

### Test Gaps

1. **Missing `Assert.DoesNotContain("ibkrConid")` in workspace tests.** The contract tests (`ExactInstrumentIdentityContractTests`) defensively assert `DoesNotContain("ibkrConid")` on every key. The workspace tests (`WorkspaceWatchlistNormalizerTests`, `WorkspaceWatchlistInstrumentKeyTests`) should do the same to prevent regression when future changes touch the normalizer or intake paths.

2. **No test for SQL backfill exclusion of `ibkrConid`.** The `PostgresWorkspaceWatchlistSqlTests.Initialize_IsIdempotentAndMigratesPrimaryKeyToInstrumentKey` only checks that `concat_ws` is present, not what segments it emits. **Suggest adding:** `Assert.DoesNotContain("ibkrConid", sql, StringComparison.OrdinalIgnoreCase)` to catch future regressions.

3. **Edge case when legacy `ibkrConid` differs from `providerSymbolId`.** The `NormalizeExistingInstrumentKey` code correctly prefers `providerSymbolId` over `ibkrConid` for the canonical key, but there's no explicit test asserting this behavior when both are present and differ (e.g., `providerSymbolId=X|ibkrConid=Y` with X ≠ Y). The Step 1 contract test `NormalizeExistingInstrumentKey_AcceptsLegacyIbkrConidSegmentAndNormalizesForward` only tests them as equal. **Suggest:** Add a test variant where they differ.

### Suggestions

1. **The `IbkrConid` record property on `ExactInstrumentIdentity` is still stored** even though it's excluded from the canonical key. This is correct for compatibility — it preserves the value for IBKR adapter paths and database column storage. The Step 3/5 docs should make this explicit: `IbkrConid` is provider-specific metadata, not an identity dimension.

2. **`WorkspaceWatchlistNormalizerTests.NormalizeReplacement_DeduplicatesOnlyExactInstrumentKeysWhilePreservingFirstSeenOrder`** (line ~22) checks `symbol.InstrumentKey` only implicitly through `Assert.Collection` — it doesn't verify the key shape. **Suggest:** Add explicit `Assert.DoesNotContain("ibkrConid", symbol.InstrumentKey)` on the ibkr-provider entry for defense in depth.

3. **The `WorkspaceWatchlistInstrumentKey.Create()` helper** (line 9) retains `ibkrConid` as a parameter, which is fine since it delegates through `ExactInstrumentIdentity.Create()` and the canonical key no longer emits it. No change needed, but a code comment noting that `ibkrConid` is passed through for metadata but excluded from the key output would help future readers.

4. **Backtesting module confirmation:** As noted in the R003 plan review, `BacktestRequestValidator.NormalizeSymbol` calls `MarketDataSymbolIdentity.Create(...)` *without* an `ibkrConid` argument, and all 47 backtesting tests pass. No Step 2 changes are needed in `ATrade.Backtesting/`.

5. **Frontend `instrumentIdentity.ts` still emits `ibkrConid` in `createProvisionalInstrumentKey`** — this is expected to be addressed in Step 4 (frontend identity handoff). The backend-side contract tests and workspace normalization are the scope of Step 2.
