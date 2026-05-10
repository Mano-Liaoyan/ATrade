## Code Review: Step 4: Update frontend identity handoff

### Verdict: APPROVE

### Summary
The Step 4 changes are minimal, targeted, and correct. Two files were modified — `instrumentIdentity.ts` and `terminalRoutes.ts` — surgically removing `ibkrConid` from the three public frontend surfaces that matter: provisional key construction, URL query-param emission, and route identity parsing. Internal normalization, display components, and backward-compatible type fields preserve `ibkrConid` where the task explicitly allows it ("only as an IBKR-specific adapter alias"). The authority chain (backend `pinKey`/`instrumentKey` > optimistic `createProvisionalInstrumentKey`) is intact. The apphost tests that previously asserted `ibkrConid` presence in source will break, but that is a natural consequence handled by Step 6.

### Issues Found
*None*

### Pattern Violations
*None*

### Test Gaps
*None in the current step — the apphost tests are a Step 6 concern. The worker should expect these tests to fail and fix them:*
- `frontend-chart-watchlist-default-tests.sh` lines 132–134 (asserts `firstTerminalQueryValue(searchParams.ibkrConid)` and `params.set('ibkrConid', …)`)
- `frontend-stock-chart-visibility-tests.sh` lines 67, 79
- `frontend-terminal-chart-analysis-tests.sh` line 106
- `frontend-terminal-route-architecture-tests.sh` line 146
- `frontend-terminal-regression-suite-tests.sh` lines 164, 171, 172 should now pass (they assert `ibkrConid` is NOT present)

### Suggestions
1. **`toNavigationInstrumentIdentity` / `toRouteIdentity` cleanup:** `terminalMarketMonitorWorkflow.ts:700` and `TerminalChartLandingModule.tsx:380` still forward `ibkrConid` into `InstrumentIdentityInput` when building navigation intents. This is harmless (the URL serializer ignores it), but removing the `ibkrConid` line would make intent clear to future readers that it's not a canonical field. Consider dropping it in a follow-up clean-up step.

2. **`parseIbkrConid` visibility:** The function is used exclusively by `getSearchResultIdentity`, `getTrendingSymbolIdentity`, and `getMarketDataIdentity` — all within the same module. It could be made module-private (unexported) to reinforce that `ibkrConid` is an internal adapter concern, not a public API.

3. **Legacy route behavior note:** After this change, legacy URLs carrying only `?ibkrConid=…` (without `provider` or `providerSymbolId`) will resolve to a bare-symbol route identity rather than an IBKR-identified one. This is consistent with the task's mandate, but the STATUS.md notes could document it as a minor behavioral shift for operator awareness.

4. **Quality checks:** No typecheck/lint/format commands were configured in this project (`taskplane-config.json` has no `testing.commands`, `frontend/package.json` has no `typecheck`/`lint`/`format:check` scripts), and `npm run build` could not run because `node_modules` is absent in the worktree. Quality checks were not exercised — the operator should verify the frontend build passes in a full environment during Step 6.
