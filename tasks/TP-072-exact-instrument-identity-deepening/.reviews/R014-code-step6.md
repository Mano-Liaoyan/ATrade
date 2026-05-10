## Code Review: Step 6 — Testing & Verification

### Verdict: APPROVE

### Summary

The R013-flagged Category A apphost test assertions have been correctly migrated from `assert_file_contains` to `assert_file_not_contains` for all 6 locations across 4 test scripts. The full dotnet test suite passes (258 tests across 11 projects, 0 failures), and `dotnet build ATrade.slnx` passes with 0 warnings/0 errors. The two apphost tests that hit pre-existing Python dependency failures (`frontend-stock-chart-visibility-tests.sh`, `frontend-chart-watchlist-default-tests.sh`) execute all `ibkrConid`-related assertions correctly before reaching the Python-dependent CSS checks. The checkbox "R013 stale Category A apphost `ibkrConid` assertions migrated" is verified as truly addressed.

### Issues Found

*None blocking.*

### Verification of R013 Fixes

All 6 R013-flagged stale assertions have been correctly migrated:

| R013 # | File | Old | New | Verified |
|--------|------|-----|-----|----------|
| #1 | `frontend-stock-chart-visibility-tests.sh:67` | `assert_file_contains "$routes" 'ibkrConid'` | `assert_file_not_contains "$routes" 'ibkrConid'` | ✅ |
| #2 | `frontend-stock-chart-visibility-tests.sh:79` | `assert_file_contains "$identity" "params.set('ibkrConid'…"` | `assert_file_not_contains "$identity" "params.set('ibkrConid'…"` | ✅ |
| #3 | `frontend-chart-watchlist-default-tests.sh:132` | `assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.ibkrConid)'` | `assert_file_not_contains` | ✅ |
| #4 | `frontend-chart-watchlist-default-tests.sh:133` | `assert_file_contains "$routes" 'ibkrConid,'` | `assert_file_not_contains` | ✅ |
| #5 | `frontend-chart-watchlist-default-tests.sh:134` | `assert_file_contains "$identity" "params.set('ibkrConid'…"` | `assert_file_not_contains` | ✅ |
| #6 | `frontend-terminal-chart-analysis-tests.sh:106` | `assert_file_contains "$identity" "params.set('ibkrConid'…"` | `assert_file_not_contains` | ✅ |

The `frontend-terminal-route-architecture-tests.sh:146` assertion (already migrated in the R013 attempt) continues to pass correctly.

### Test Suite Results

```
ATrade.ProviderAbstractions.Tests : Passed 20, Failed 0
ATrade.Workspaces.Tests          : Passed 30, Failed 0
ATrade.Backtesting.Tests         : Passed 47, Failed 0
ATrade.ServiceDefaults.Tests     : Passed 15, Failed 0
ATrade.Accounts.Tests            : Passed 16, Failed 0
ATrade.Brokers.Ibkr.Tests        : Passed 42, Failed 0
ATrade.Orders.Tests              : Passed  3, Failed 0
ATrade.MarketData.Timescale.Tests: Passed 36, Failed 0
ATrade.MarketData.Ibkr.Tests     : Passed 24, Failed 0
ATrade.Analysis.Tests            : Passed 10, Failed 0
ATrade.Analysis.Lean.Tests       : Passed 15, Failed 0
─────────────────────────────────────────────
Total                            : Passed 258, Failed 0
```

**Build:** `dotnet build ATrade.slnx` — 0 warnings, 0 errors.

### Apphost Test Status

| Test Script | Status | Notes |
|-------------|--------|-------|
| `frontend-terminal-route-architecture-tests.sh` | ✅ Pass | |
| `frontend-terminal-chart-analysis-tests.sh` | ✅ Pass | |
| `frontend-terminal-market-monitor-tests.sh` | ✅ Pass | Line 95 `ibkrConid: identity.ibkrConid` assertion still passes — the source file retains internal `ibkrConid` adapter fields that are compatible with the task's legacy-acceptance policy |
| `frontend-stock-chart-visibility-tests.sh` | ⚠️ Pre-existing Python fail | All `ibkrConid` assertions pass before Python-dependent CSS checks |
| `frontend-chart-watchlist-default-tests.sh` | ⚠️ Pre-existing Python fail | All `ibkrConid` assertions pass before Python-dependent CSS checks |
| `frontend-terminal-regression-suite-tests.sh` | ⚠️ Pre-existing Python fail | Already asserted `ibkrConid` absence — no migration needed |

### Quality Checks

No typecheck/lint/format-check commands are configured: `.pi/taskplane-config.json` has no `testing.commands` section, and `frontend/package.json` defines only `dev`, `build`, and `start` scripts. Quality checks were not exercised in this review.

### Suggestions

- **Category B integration tests** (`apphost-postgres-watchlist-volume-tests.sh`, `postgres-watchlist-persistence-tests.sh`) still carry `ibkrConid` in canonical key strings (lines 16–18, 329–331) and API response assertions (lines 341, 281). The worker acknowledged this in STATUS.md Notes. Per the task's legacy-acceptance policy, POST request bodies sending `ibkrConid` may remain as-is (testing backward compatibility), but expected API response payloads and canonical key strings should be updated to match the provider-neutral key shape when Docker/Postgres infrastructure is available for verification.
- The pre-existing Python dependency issue blocking 3 of 6 apphost tests from completing should be triaged separately — it is not caused by TP-072. The test assertions relevant to this task all execute and pass before the Python-dependent CSS checks are reached.
