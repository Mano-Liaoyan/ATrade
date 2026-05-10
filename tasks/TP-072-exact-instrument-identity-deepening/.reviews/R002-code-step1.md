## Code Review: Step 1 — Pin provider-neutral identity/key contract tests first

### Verdict: APPROVE

### Summary

This step correctly encodes the provider-neutral identity contract as test-first
assertions. The four changed files target exactly the seams the task touches:
the core `ExactInstrumentIdentity` contract, backtest request validation and
persistence, and the frontend apphost regression guard. All changes are
behavioural contract assertions, not implementation — they describe the
*desired* shape of the canonical key, legacy-key normalization, saved-backtest
identity tuple persistence, and frontend route/query handoff. The tests will
fail against the current `ibkrConid`-emitting implementation, which is the
expected test-first posture for Step 1. The backend test projects compile
cleanly. No quality-checks pipeline is configured, so none were exercised.

### Issues Found

*None at critical or important severity.*

### Pattern Violations

*None.*

### Test Gaps

1. **Watchlist `WorkspaceWatchlistInstrumentKeyTests` still asserts old format.**
   `Normalize_CreatesStableProviderMarketInstrumentKey` and
   `WatchlistSymbolJson_ExposesInstrumentKeyAndPinKeyAliases` both hardcode
   `ibkrConid=265598` in expected key strings. These will fail when Step 2
   changes the `CreateInstrumentKey()` implementation. The worker should
   update these tests in Step 2 or Step 3 (adapters/persistence consumers).
   The plan review flagged this cascade explicitly, and it's understood — it
   is not a Step 1 defect, but the worker should not leave these stale into
   Step 2's completion.

2. **Legacy normalization test covers only congruent `ibkrConid`/`providerSymbolId`.**
   `NormalizeExistingInstrumentKey_AcceptsLegacyIbkrConidSegmentAndNormalizesForward`
   tests the case where `ibkrConid` equals `providerSymbolId` (both 265598).
   There is no test for a legacy key where `ibkrConid` differs from a non-empty
   `providerSymbolId` — e.g., `providerSymbolId=12345|ibkrConid=265598`. The
   task's mandate is that `ibkrConid` is IBKR-specific provider metadata, so
   this scenario (if it can arise from real data) should be decided: either
   reject the key, or preserve `providerSymbolId` and drop `ibkrConid`. The
   worker can handle this in Step 2; adding a test now would make the contract
   more explicit.

3. **`NormalizeExistingInstrumentKey_UsesLegacyIbkrConidAsIbkrProviderSymbolAliasOnly` tests empty-string `providerSymbolId` only.**
   The test input has `providerSymbolId=|` (empty). It does not cover the case
   where the `providerSymbolId` segment is entirely absent from a legacy key.
   If such keys exist in the wild, the parse logic in Step 2 should handle
   them gracefully (treat absent segment as null/empty, then alias from conid
   for IBKR). Minor — can be addressed during implementation in Step 2.

4. **Backtest roundtrip test equality depends on `MarketDataSymbolIdentity` record semantics.**
   The new `Assert.Equal(snapshot.Symbol, restored.Symbol)` in
   `PersistedRequestSnapshots_RoundTripBuiltInStrategyDefaults` relies on C#
   record value equality across all six fields. This is correct — the record
   is a `sealed record` with compiler-generated `Equals`. However, the test
   could be made *more* explicit about which fields are compared by asserting
   each field individually (as the block above does). The catch-all `Equal`
   covers the case well, but a future dev adding a non-identity field to
   `MarketDataSymbolIdentity` would silently change what this tests. The
   individual field assertions already present in the
   `Validate_NormalizesSingleSymbolBuiltInStrategyParameterBagAndCosts` test
   serve as the explicit contract. No action needed, but noted for awareness.

### Suggestions

1. **Backend tests will fail until Step 2 is implemented — document this.**
   All assertions in `ExactInstrumentIdentityContractTests` that expect
   `ibkrConid`-free keys will fail because `CreateInstrumentKey()` still emits
   the `ibkrConid` segment. The `NormalizeExistingInstrumentKey` tests will
   also fail because `TryNormalizeExistingInstrumentKey` only trims today.
   This is expected TDD posture, but the worker should confirm these failures
   are *structural* (returning wrong string) not *exceptional* (throwing) so
   Step 2 can proceed cleanly.

2. **Frontend regression script tests source strings that still exist.**
   The three `assert_file_not_contains` checks in
   `frontend-terminal-regression-suite-tests.sh` assert that `ibkrConid`
   patterns are absent from `terminalRoutes.ts` and `instrumentIdentity.ts`.
   Those patterns are still present in the source. The script will fail
   until Step 4 updates the frontend sources. The worker should handle this
   as an expected failing gate, not a surprise.

3. **Consider a `System.Text.Json` property-name test for `ibkrConid` absence.**
   The `PostgresBacktestRunRepositoryTests.PersistenceSafety_SerializesOnlyCanonicalSafeRequestSnapshot`
   now asserts the provider-neutral fields are *present*. It could also assert
   that `"ibkrConid"` is *absent* from the serialized JSON (similar to the
   existing `symbolCode`/`bars`/`account`/`gateway`/`token`/`cookie`
   assertions). This would explicitly guard against the `BacktestRequestSnapshot`
   or its `Symbol` ever leaking an `ibkrConid` field into storage. The existing
   `Assert.DoesNotContain` pattern in that test makes this a one-line addition.

4. **Naming alignment with plan review suggestion #1.**
   The plan review suggested adding a test that distinguishes "field present"
   from "segment absent." The current tests do this implicitly — they verify
   `identity.IbkrConid` is populated separately from `identity.InstrumentKey`
   (e.g., line 21 vs line 26-28 in the updated contract tests). The intent is
   clear enough; no renamed test methods strictly needed, but the worker may
   optionally adopt the suggested naming convention in Step 2.
