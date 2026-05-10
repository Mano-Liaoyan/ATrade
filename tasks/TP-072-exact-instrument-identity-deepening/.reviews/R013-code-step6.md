## Code Review: Step 6 — Testing & Verification

### Verdict: REVISE

### Summary

The three targeted dotnet test suites pass (ProviderAbstractions: 20/20, Workspaces: 30/30, Backtesting: 47/47), the full `dotnet test ATrade.slnx` passes with 0 failures, and `dotnet build ATrade.slnx` produces 0 warnings/0 errors. However, the apphost test migration — explicitly flagged in the R012 plan review before Step 6 began — is **incomplete**. Only 1 of ~10 needed apphost test changes was made (`frontend-terminal-route-architecture-tests.sh:146`). Six other Category A apphost test assertions still expect `ibkrConid` in source-code locations where it was intentionally removed in Steps 1–4, causing those tests to fail deterministically. The Step 6 checkbox "Affected frontend/apphost identity contract tests passing" is therefore factually incorrect.

### Issues Found

1. **[frontend-stock-chart-visibility-tests.sh:67] [important]** — `assert_file_contains "$routes" 'ibkrConid'` expects `ibkrConid` in `frontend/lib/terminalRoutes.ts`, but that file no longer contains `ibkrConid`. **Confirmed failing:** `expected .../terminalRoutes.ts to contain ibkrConid`. Fix: change to `assert_file_not_contains` or remove the assertion depending on intent.

2. **[frontend-stock-chart-visibility-tests.sh:79] [important]** — `assert_file_contains "$identity" "params.set('ibkrConid', String(identity.ibkrConid));"` expects `ibkrConid` in URL query params code, but `toExactIdentitySearchParams` in `instrumentIdentity.ts` no longer sets `ibkrConid`. Fix: change to `assert_file_not_contains "$identity" "params.set('ibkrConid'"` (or remove assertion).

3. **[frontend-chart-watchlist-default-tests.sh:132] [important]** — `assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.ibkrConid)'` expects `ibkrConid` in `terminalRoutes.ts`, but that reference was removed. **Confirmed failing.** Fix: change to `assert_file_not_contains`.

4. **[frontend-chart-watchlist-default-tests.sh:133] [important]** — `assert_file_contains "$routes" 'ibkrConid,'` expects `ibkrConid` in `terminalRoutes.ts`, but it no longer appears there. **Confirmed failing.** Fix: change to `assert_file_not_contains` (or remove).

5. **[frontend-chart-watchlist-default-tests.sh:134] [important]** — `assert_file_contains "$identity" "params.set('ibkrConid', String(identity.ibkrConid));"` — same stale assertion as #2. **Confirmed failing.** Fix: flip to `assert_file_not_contains`.

6. **[frontend-terminal-chart-analysis-tests.sh:106] [important]** — `assert_file_contains "$identity" "params.set('ibkrConid', String(identity.ibkrConid));"` — same stale assertion as #2/#5. **Confirmed failing.** Fix: flip to `assert_file_not_contains`.

7. **[STATUS.md Step 6 checkbox 4] [important]** — The checkbox "Affected frontend/apphost identity contract tests passing" is checked but factually incorrect. At a minimum 3 apphost test scripts (covering 6 assertion failures) fail deterministically.

### Pattern Violations

- **Incomplete test migration.** The R012 plan review (Suggestion 1) enumerated every Category A test file and line number that needed updating. Only `frontend-terminal-route-architecture-tests.sh:146` was addressed. The worker marked the checkbox "Affected frontend/apphost identity contract tests passing" without actually running or migrating the other 6 assertion failures.

### Test Gaps

- **Category B integration tests (`apphost-postgres-watchlist-volume-tests.sh`, `postgres-watchlist-persistence-tests.sh`) still reference `ibkrConid` in canonical key strings and API response assertions.** These require Docker/Postgres infrastructure to execute and will skip when unavailable, so they don't block this review. However, the stale source-level values should be documented or migrated to match the provider-neutral key shape. The R012 plan review flagged these at specific line numbers (16–18, 329–331 for canonical keys; 341, 281 for response assertions).

### Frontend Build

The frontend build (`cd frontend && npm run build`) fails with a Next.js prerender error on `/_not-found` (TypeError: Cannot read properties of null reading 'useContext'). This failure is **pre-existing** — the same class of error occurs at the baseline commit `c218d17` (with TP-072 changes stashed). It is not caused by TP-072 changes and does not block this review. **Note for operator:** this pre-existing build regression should be triaged separately.

### Suggestions

- The Category B integration tests (`apphost-postgres-watchlist-volume-tests.sh`, `postgres-watchlist-persistence-tests.sh`) still carry `ibkrConid` in canonical key strings and expected API response assertions. The worker should either migrate these or log a discovery noting they need attention when Docker/Postgres infrastructure is available. Per the task's legacy-acceptance policy, POST request bodies sending `ibkrConid` may remain as-is (they test backward compatibility), but expected API *response* payloads and canonical key strings should be updated to match the provider-neutral shape.
