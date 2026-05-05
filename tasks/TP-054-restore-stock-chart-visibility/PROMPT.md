# Task: TP-054 - Restore stock chart visibility

**Created:** 2026-05-05
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This task diagnoses and fixes a user-visible chart rendering regression across the stock symbol route, terminal chart workspace, lightweight-charts component, layout CSS, and validation scripts. It is frontend-focused and reversible, but it spans multiple chart/workspace modules and needs both plan and code review.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-054-restore-stock-chart-visibility/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Fix the current regression where stock charts are not visibly rendering in the CHART workspace (for example `/symbols/AAPL` or chart actions from the market monitor). Preserve truthful provider states: show a visible candlestick chart when real candle data exists, show loading/error/empty states when data is unavailable, and never replace missing provider data with fake candles. The fix must validate the final layout after TP-053 removes top chrome and compacts filters.

## Dependencies

- **Task:** TP-053 (top chrome removal and compact market filters should land first so chart visibility is validated in the final workspace layout)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — active chart/workspace visual authority
- `docs/architecture/paper-trading-workspace.md` — chart workflow, provider-state, safety, and API-boundary contract
- `docs/architecture/modules.md` — frontend chart/module ownership map
- `docs/architecture/provider-abstractions.md` — chart range, candle, exact identity, and provider-unavailable semantics
- `docs/architecture/analysis-engines.md` — load if chart-to-analysis handoff or analysis workspace behavior changes
- `README.md` — current runtime surface and verification entry points
- `PLAN.md` — active queue and follow-up direction

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, and active docs
- **Services required:** None for source/build checks. Real IBKR/iBeam verification is optional and must use ignored local `.env` values; automated scripts must cleanly validate unavailable-provider behavior without requiring live credentials.

## File Scope

- `frontend/components/CandlestickChart.tsx`
- `frontend/components/terminal/TerminalChartWorkspace.tsx`
- `frontend/components/terminal/TerminalInstrumentHeader.tsx` (check if affected)
- `frontend/lib/symbolChartWorkflow.ts`
- `frontend/lib/terminalChartWorkspaceWorkflow.ts`
- `frontend/lib/marketDataClient.ts` (check if affected)
- `frontend/app/symbols/[symbol]/page.tsx` (check if affected)
- `frontend/app/globals.css`
- `tests/apphost/frontend-stock-chart-visibility-tests.sh` (new)
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh`
- `tests/apphost/frontend-chart-range-preset-tests.sh`
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh` (check if affected)
- `README.md`
- `PLAN.md`
- `docs/design/atrade-terminal-ui.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/provider-abstractions.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Reproduce and pin down the chart visibility failure

> ⚠️ Hydrate: Expand based on whether the failure is caused by route/module state, provider/data state, chart container sizing, `lightweight-charts` lifecycle, or workspace overflow/layout.

- [ ] Inspect `/symbols/[symbol]` route initialization, market-monitor chart intents, `useTerminalChartWorkspaceWorkflow`, `TerminalChartWorkspace`, `CandlestickChart`, and relevant CSS to identify why stock candles do not produce a visible chart
- [ ] Distinguish a real no-data/provider-unavailable state from a UI rendering failure; do not treat unavailable provider data as a reason to add fake chart data
- [ ] Record the root cause and impacted files in STATUS.md discoveries before implementing the fix

**Artifacts:**
- `STATUS.md` (modified discoveries)
- Chart/workflow/layout source files listed in File Scope (read/diagnosed)

### Step 2: Make the stock chart visibly render when candle data exists

- [ ] Update `CandlestickChart` and/or chart workspace layout so the `lightweight-charts` canvas receives a non-zero width and height, resizes after module/layout changes, and remains visible for stock candle payloads
- [ ] Preserve OHLC legend, volume, SMA overlays, fit-content behavior, crosshair updates, and cleanup on unmount/data/range changes
- [ ] Ensure `TerminalChartWorkspace` only renders the chart for actual `chart.candles` and continues to show truthful loading, error, and empty states without fake data
- [ ] Ensure `/symbols/{symbol}` and market-monitor Chart actions keep the CHART module active with the selected symbol and exact identity metadata when available

**Artifacts:**
- `frontend/components/CandlestickChart.tsx` (modified)
- `frontend/components/terminal/TerminalChartWorkspace.tsx` (modified if needed)
- `frontend/lib/symbolChartWorkflow.ts` (modified if needed)
- `frontend/lib/terminalChartWorkspaceWorkflow.ts` (modified if needed)
- `frontend/app/symbols/[symbol]/page.tsx` (modified only if route/module state is part of the bug)

### Step 3: Protect chart visibility in CSS and validation

- [ ] Update `frontend/app/globals.css` so the chart region/container cannot collapse or be hidden by the full-viewport workspace layout, compact filters, side indicator grid, or mobile breakpoint behavior
- [ ] Create `tests/apphost/frontend-stock-chart-visibility-tests.sh` to validate the chart visibility contract: chart route/workspace source wiring, `CandlestickChart` render path, explicit chart container sizing/resizing behavior, preserved provider-unavailable/empty states, and no fake candle data
- [ ] Update existing chart/layout validation scripts to assert the fixed chart contract and remove any stale assumptions that would allow a collapsed chart container to pass

**Artifacts:**
- `frontend/app/globals.css` (modified)
- `tests/apphost/frontend-stock-chart-visibility-tests.sh` (new)
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh` (modified)
- `tests/apphost/frontend-chart-range-preset-tests.sh` (modified only if affected)
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh` (modified only if affected)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run new chart visibility validation: `bash tests/apphost/frontend-stock-chart-visibility-tests.sh`
- [ ] Run chart/analysis validation: `bash tests/apphost/frontend-terminal-chart-analysis-tests.sh`
- [ ] Run chart range preset validation: `bash tests/apphost/frontend-chart-range-preset-tests.sh`
- [ ] Run final layout validation: `bash tests/apphost/frontend-simplified-workspace-layout-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] Update active docs to describe the restored visible chart sizing/rendering contract and any changed chart layout behavior
- [ ] Update README/PLAN verification inventory or current frontend surface text if the new chart visibility validation script should be listed
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md, including the root cause and whether real-provider local verification was available or skipped

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — chart workspace visible sizing/layout contract after the fix
- `docs/architecture/paper-trading-workspace.md` — chart rendering/provider-truthful states if implementation behavior changes
- `docs/architecture/modules.md` — frontend chart component ownership if `CandlestickChart`/terminal chart responsibilities change
- `docs/architecture/provider-abstractions.md` — update if candle/range/provider-state handling changes
- `README.md` — verification entry-point list/current runtime surface if adding the new validation script or changing chart behavior text
- `PLAN.md` — current/follow-up direction if affected

**Check If Affected:**
- `docs/architecture/analysis-engines.md` — update only if chart-to-analysis handoff, selected range, or analysis workspace states change

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] `/symbols/{stock}` and market-monitor Chart actions render the CHART workspace for the selected stock symbol instead of a blank/collapsed chart area when candle data exists
- [ ] `CandlestickChart` receives and maintains non-zero render dimensions and still cleans up `lightweight-charts` resources correctly
- [ ] Loading, error, provider-unavailable, and empty candle states remain explicit and truthful; no fake candle data is introduced
- [ ] Exact provider/market/currency/asset-class identity remains visible and flows into chart/analysis handoff where available
- [ ] The final layout after TP-053 still has no top header or visible safety strip, compact filters, no page-level vertical scrolling, and an internally visible chart workspace

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-054): complete Step N — description`
- **Bug fixes:** `fix(TP-054): description`
- **Tests:** `test(TP-054): description`
- **Hydration:** `hydrate: TP-054 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Use fake/mock candle data to make charts appear
- Hide provider-unavailable/provider-not-configured/authentication-required states or exact identity metadata
- Break chart range lookback semantics, exact identity query propagation, or chart-to-analysis handoff
- Reintroduce the removed command system, old shell/list route wrappers, context/monitor/footer chrome, top app brand header, or visible global safety strip
- Add direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, or LEAN
- Add real order placement, simulated order-entry UI, buy/sell buttons, order tickets, previews, confirmations, or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
