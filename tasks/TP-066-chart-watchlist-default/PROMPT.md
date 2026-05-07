# Task: TP-066 - Chart landing watchlist default and stored-stock selector

**Created:** 2026-05-07
**Size:** M

## Review Level: 1 (Plan Only)

**Assessment:** This task builds a focused chart landing experience on top of existing watchlist and chart workflows. It touches frontend workflow/component code only, uses existing API clients, and does not change backend persistence or security contracts.
**Score:** 2/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 0

## Canonical Task Folder

```
tasks/TP-066-chart-watchlist-default/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Make `/chart` useful when the user did not arrive from Search or Watchlist. The accepted behavior is: load the user's backend-owned stored stocks/watchlist, show a visible "Stored stocks" selector/list, automatically display the first saved watchlist instrument as the default chart when available, and show a truthful empty/unavailable state with routes to Search and Watchlist when no stored stock can be loaded. Do not invent demo/default symbols.

## Dependencies

- **Task:** TP-065 (canonical `/chart` and `/chart/[symbol]` routes must exist, and `/symbols/[symbol]` must be removed)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — chart workspace and visibility authority
- `docs/architecture/paper-trading-workspace.md` — watchlist/chart API boundary and no-fake-data rules
- `docs/architecture/provider-abstractions.md` — exact instrument identity semantics
- `README.md` — verification inventory
- `PLAN.md` — current frontend direction

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, active docs
- **Services required:** None for source/build validation. Optional Next.js dev checks may point the API base to an unavailable loopback URL and must still show truthful unavailable states.

## File Scope

- `frontend/app/chart/page.tsx`
- `frontend/app/chart/[symbol]/page.tsx` (check if affected)
- `frontend/components/terminal/ATradeTerminalApp.tsx`
- `frontend/components/terminal/TerminalChartWorkspace.tsx` (check if affected)
- `frontend/components/terminal/TerminalInstrumentHeader.tsx` (check if affected)
- `frontend/components/terminal/TerminalPanel.tsx` (check if affected)
- `frontend/components/terminal/TerminalChartLandingModule.tsx` (new, or equivalent child component)
- `frontend/lib/watchlistWorkflow.ts`
- `frontend/lib/watchlistClient.ts` (check if affected)
- `frontend/lib/instrumentIdentity.ts` (check if route helper affected)
- `frontend/lib/terminalChartWorkspaceWorkflow.ts` (check if affected)
- `frontend/types/terminal.ts` (check if affected)
- `frontend/types/marketData.ts` (check if affected)
- `frontend/app/globals.css`
- `tests/apphost/frontend-chart-watchlist-default-tests.sh` (new)
- Existing chart/watchlist tests under `tests/apphost/frontend-*.sh` (check/update if affected)
- `docs/design/atrade-terminal-ui.md`
- `docs/architecture/paper-trading-workspace.md`
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Build the chart landing selection workflow

- [ ] Reuse existing backend watchlist APIs/workflows to load stored stocks for `/chart`; do not read directly from browser-only caches as authoritative state and do not call databases/providers directly
- [ ] Select the first available stored/watchlist instrument as the default chart candidate, preserving exact provider identity metadata (`provider`, `providerSymbolId`, `exchange`, `currency`, `assetClass`, and IBKR conid when available)
- [ ] Provide state for selecting another stored stock and for opening canonical `/chart/[symbol]`, `/analysis/[symbol]`, or `/backtest/[symbol]` routes with identity query metadata
- [ ] Preserve explicit loading, empty, cached-fallback, and backend-unavailable states without hard-coded symbols such as AAPL/MSFT or synthetic bars

**Artifacts:**
- `frontend/components/terminal/TerminalChartLandingModule.tsx` (new, or equivalent)
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/lib/watchlistWorkflow.ts` (modified if needed)
- `frontend/lib/instrumentIdentity.ts` (modified if needed)

### Step 2: Render `/chart` with stored stocks plus default chart

- [ ] Update the `/chart` route/module to render a "Stored stocks" selector/list and a chart region for the selected/default instrument
- [ ] Automatically render a visible `TerminalChartWorkspace`/candlestick state for the first stored stock when watchlist data exists; keep provider-unavailable/no-candles states explicit instead of blank
- [ ] When the stored list is empty or unavailable, show clear copy and canonical links/buttons to `/search` and `/watchlist`
- [ ] Keep layout under the TP-064 internal-scroll/no-clipping desktop browser guardrail

**Artifacts:**
- `frontend/app/chart/page.tsx` (modified)
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/components/terminal/TerminalChartLandingModule.tsx` (new/modified)
- `frontend/app/globals.css` (modified)

### Step 3: Preserve symbol-specific chart behavior

- [ ] Keep `/chart/[symbol]` rendering the selected symbol directly with exact identity/range query parsing from TP-065
- [ ] Ensure selecting a stored stock from `/chart` can update the chart and/or navigate to `/chart/[symbol]` without losing exact identity metadata
- [ ] Ensure chart-to-analysis/backtest handoff routes remain `/analysis/[symbol]` and `/backtest/[symbol]`

**Artifacts:**
- `frontend/app/chart/[symbol]/page.tsx` (modified if needed)
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/lib/instrumentIdentity.ts` (modified if needed)

### Step 4: Add chart landing validation

- [ ] Create `tests/apphost/frontend-chart-watchlist-default-tests.sh` validating `/chart` route existence, "Stored stocks" selector copy, first-watchlist default behavior markers, exact identity handoff, empty/unavailable state copy, and no hard-coded demo/default symbol
- [ ] Update existing chart/range/stock visibility tests only where route path or shared strings changed
- [ ] Keep validation provider/runtime independent

**Artifacts:**
- `tests/apphost/frontend-chart-watchlist-default-tests.sh` (new)
- Existing frontend chart/watchlist tests (modified if affected)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run chart landing validation: `bash tests/apphost/frontend-chart-watchlist-default-tests.sh`
- [ ] Run stock chart visibility validation: `bash tests/apphost/frontend-stock-chart-visibility-tests.sh`
- [ ] Run chart range preset validation: `bash tests/apphost/frontend-chart-range-preset-tests.sh`
- [ ] Run route architecture validation: `bash tests/apphost/frontend-terminal-route-architecture-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] Update docs to describe `/chart` defaulting to first stored watchlist instrument and the Stored stocks selector
- [ ] Update README/PLAN verification inventory/current frontend surface if a new validation script is added
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — chart landing/default watchlist chart behavior
- `docs/architecture/paper-trading-workspace.md` — frontend chart/watchlist behavior and no-fake-default contract
- `README.md` — verification inventory if a new script is added
- `PLAN.md` — frontend follow-up/current surface if affected

**Check If Affected:**
- `docs/architecture/provider-abstractions.md` — update only if exact identity route semantics change
- `docs/architecture/modules.md` — update only if frontend component/workflow ownership changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] `/chart` shows a Stored stocks selector/list
- [ ] `/chart` automatically displays the first backend watchlist instrument when available
- [ ] Stored stock selection preserves exact provider/market identity and can open canonical chart/analysis/backtest routes
- [ ] Empty/unavailable watchlist states are explicit and link to Search/Watchlist
- [ ] No hard-coded demo stock, synthetic chart bars, fake provider data, direct provider/database access, order controls, mobile optimization scope, or secrets are introduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-066): complete Step N — description`
- **Bug fixes:** `fix(TP-066): description`
- **Tests:** `test(TP-066): description`
- **Hydration:** `hydrate: TP-066 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Add a fake default chart, hard-code example stocks, or synthesize candle data
- Treat browser localStorage as authoritative watchlist state
- Add backend endpoints, database schema changes, direct provider/runtime/database access, or new persistence
- Add order entry, buy/sell controls, broker execution, or live-trading behavior
- Expose secrets, account identifiers, gateway URLs, LEAN workspace paths, process command lines, tokens, or cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
