## Plan Review: Step 6 — Testing & Verification

### Verdict: APPROVE

### Summary

The Step 6 plan describes a standard testing & verification workflow: run targeted test suites, run the full solution test suite, fix failures, and verify the build. The R009 (Step 4) review already identified the specific apphost tests that will fail due to the `ibkrConid` removal — the worker is primed that this is expected, not a surprise. The plan is adequate for achieving the "all tests passing" outcome.

### Issues Found

*None blocking.*

### Missing Items

*None.* The checkboxes cover the required testing scope. The R009 review already enumerated which apphost tests will break and need migration (see Suggestions below for a consolidation).

### Suggestions

1. **[Suggestion]** **Apphost test migration awareness.** The R009 code review for Step 4 identified exactly which apphost tests will fail on `ibkrConid` assertions. The worker should be aware these fall into two distinct categories:

   **A. Source-code assertion tests** (assert `ibkrConid` in frontend code that was changed in Step 4):
   - `frontend-chart-watchlist-default-tests.sh` (lines 123, 132–134)
   - `frontend-stock-chart-visibility-tests.sh` (lines 67, 79)
   - `frontend-terminal-chart-analysis-tests.sh` (line 106)
   - `frontend-terminal-route-architecture-tests.sh` (line 146)
   - `frontend-terminal-market-monitor-tests.sh` (line 95)
   
   **Will pass as-is:** `frontend-terminal-regression-suite-tests.sh` already asserts `ibkrConid` **absence** (lines 164, 171, 172).

   **B. Canonical-key-string and API-payload tests** (use `ibkrConid` in expected key values and POST/response assertions — these need the `ibkrConid` segment removed from canonical key strings and response `ibkrConid` assertions updated):
   - `apphost-postgres-watchlist-volume-tests.sh` (lines 16–18 canonical keys, line 341 response assertion)
   - `postgres-watchlist-persistence-tests.sh` (lines 329–331 canonical keys, line 281 response assertion)

   Category B tests also reference `ibkrConid` in POST request bodies (e.g., `request_json POST '/api/workspace/watchlist' '{"symbol":"AAPL","provider":"ibkr","providerSymbolId":"265598","ibkrConid":265598,…}'`). Per the task's legacy-acceptance policy, sending `ibkrConid` in POST payloads should still be accepted — but the tests may need to stop asserting `ibkrConid` in API *responses* since the backend no longer emits it as a canonical field.

   The worker may want to capture one discovery noting this migration before starting test execution.

2. **[Suggestion]** **Integration-test infrastructure dependency.** The `apphost-postgres-watchlist-volume-tests.sh` and `postgres-watchlist-persistence-tests.sh` tests require Docker/Postgres infrastructure. Per PROMPT.md's environment section, these should skip cleanly when infrastructure is unavailable. The plan doesn't address how to handle gracefully-skipped integration tests — no change needed, but the worker should verify skip behavior is correct if running in an environment without those services.

3. **[Suggestion]** **Frontend build verification.** The `frontend/package.json` has a `build` script (`next build`), but `node_modules` may not be present in the worktree (R009 noted this). The Step 6 plan says "Frontend build passing **if frontend identity code changes**" — since Step 4 did change frontend identity code, the build should run. The worker should run `npm install` first if needed.

4. **[Note]** **No quality-check commands configured.** The `.pi/taskplane-config.json` has no `testing.commands` section, and neither the root nor `frontend/package.json` defines `typecheck`, `lint`, or `format:check` scripts. Quality checks are not exercised in this review — the operator should verify the frontend build in a full environment during Step 6.

### Verification Summary

- **Checkbox coverage** ✅ — All 7 checkboxes cover the testing scope: targeted suites, full suite, frontend build, fixes, and build verification.
- **Known failures addressed** ✅ — R009 already primed the worker about which apphost tests need migration. "Fix all failures" covers this work.
- **Environment guardrails** ✅ — PROMPT.md specifies "runtime scripts must skip clearly when optional infrastructure is unavailable," which covers integration-test dependencies.
- **Regression suite alignment** ✅ — `frontend-terminal-regression-suite-tests.sh` asserts `ibkrConid` absence and should pass as-is, providing a useful regression guardrail.
