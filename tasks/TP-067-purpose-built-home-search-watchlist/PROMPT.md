# Task: TP-067 - Purpose-built Home, Search, and Watchlist modules

**Created:** 2026-05-07
**Size:** M

## Review Level: 1 (Plan Only)

**Assessment:** This task refactors frontend module composition/copy around existing market-monitor, watchlist, and provider-status workflows. It is limited to frontend UI/components/tests/docs, adapts existing patterns, and does not change backend security or persistence.
**Score:** 2/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 0

## Canonical Task Folder

```
tasks/TP-067-purpose-built-home-search-watchlist/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Refactor Home, Search, and Watchlist so users do not see the same generic market-monitor UI on three pages. The accepted split is: Home is a dashboard/overview with provider status, paper safety, quick actions, and compact watchlist/trending context; Search is a search-first workflow with prominent bounded stock search, ranked results, filters, and chart/pin actions; Watchlist is a saved-stocks workflow that puts backend-stored pins first with manage/remove and chart/analysis/backtest actions. Reuse shared lower-level components where helpful, but the page purpose, copy, layout, and default focus must be clearly distinct.

## Dependencies

- **Task:** TP-066 (canonical routes and chart landing stored-stock behavior must exist so page links/actions target the final route model)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — active module UX/layout authority
- `docs/architecture/paper-trading-workspace.md` — search/watchlist/chart workflow and no-fake-data rules
- `docs/architecture/provider-abstractions.md` — provider/exact identity rules
- `docs/architecture/modules.md` — frontend module/component ownership
- `README.md` — verification inventory
- `PLAN.md` — active frontend direction

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, active docs
- **Services required:** None for source/build validation. Optional Next.js dev checks may use an unavailable API base and must show truthful unavailable states.

## File Scope

- `frontend/components/terminal/ATradeTerminalApp.tsx`
- `frontend/components/terminal/TerminalHomeModule.tsx` (new, or equivalent extracted component)
- `frontend/components/terminal/TerminalSearchModule.tsx` (new, or equivalent extracted component)
- `frontend/components/terminal/TerminalWatchlistModule.tsx` (new, or equivalent extracted component)
- `frontend/components/terminal/TerminalMarketMonitor.tsx`
- `frontend/components/terminal/MarketMonitorSearch.tsx`
- `frontend/components/terminal/MarketMonitorTable.tsx`
- `frontend/components/terminal/MarketMonitorDetailPanel.tsx`
- `frontend/components/terminal/TerminalProviderDiagnostics.tsx` (check if home status summary uses it)
- `frontend/lib/terminalMarketMonitorWorkflow.ts`
- `frontend/lib/watchlistWorkflow.ts`
- `frontend/lib/symbolSearchWorkflow.ts` (check if affected)
- `frontend/lib/terminalModuleRegistry.ts` (check if copy/description affected)
- `frontend/app/globals.css`
- `tests/apphost/frontend-purpose-built-home-search-watchlist-tests.sh` (new)
- Existing market-monitor/search/watchlist tests under `tests/apphost/frontend-*.sh` (check/update if affected)
- `docs/design/atrade-terminal-ui.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md` (check/update if component ownership changes)
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Split page composition by purpose

- [ ] Extract or restructure Home/Search/Watchlist module rendering so each page has its own component/composition instead of three thin wrappers around identical `TerminalMarketMonitor` markup
- [ ] Keep shared workflow/table/filter/detail primitives reusable underneath, but expose page mode/props or child components only where they make the three module purposes clearer
- [ ] Preserve exact identity handoff, bounded API-backed search, backend-owned watchlist authority, provider unavailable states, and no-order guardrails

**Artifacts:**
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/components/terminal/TerminalHomeModule.tsx` / `TerminalSearchModule.tsx` / `TerminalWatchlistModule.tsx` (new or equivalent)
- `frontend/components/terminal/TerminalMarketMonitor.tsx` (modified if needed)
- `frontend/lib/terminalMarketMonitorWorkflow.ts` / `watchlistWorkflow.ts` (modified if needed)

### Step 2: Implement a dashboard-focused Home module

- [ ] Render Home as an overview/dashboard: provider/API status, paper-only/no-order safety reminder, quick actions to `/search`, `/watchlist`, `/chart`, `/analysis`, `/backtest`, `/status`, and compact current market/watchlist context
- [ ] Use compact previews rather than the full generic market monitor; preview content must remain truthful when providers/watchlists are unavailable and must not include fake data
- [ ] Keep Home copy and headings different from Search and Watchlist so the user immediately understands its purpose

**Artifacts:**
- Home module component(s) (new/modified)
- `frontend/app/globals.css` (modified)

### Step 3: Implement search-first and watchlist-first modules

- [ ] Render Search as a prominent bounded stock search workflow with search input focus/copy first, ranked results, filters, and chart/pin/analysis/backtest actions
- [ ] Render Watchlist as a saved-stocks workflow: backend stored pins first, pin/remove/manage affordances, exact identity metadata, and chart/analysis/backtest actions; include explicit empty/unavailable states and route to Search for adding stocks
- [ ] Avoid duplicated titles/descriptions/default layout between Home, Search, and Watchlist while preserving shared lower-level behavior

**Artifacts:**
- Search module component(s) (new/modified)
- Watchlist module component(s) (new/modified)
- `frontend/components/terminal/TerminalMarketMonitor.tsx` / child components (modified if needed)
- `frontend/app/globals.css` (modified)

### Step 4: Add purpose-built module validation

- [ ] Create `tests/apphost/frontend-purpose-built-home-search-watchlist-tests.sh` validating distinct components/copy/test IDs, Home dashboard quick actions, Search search-first copy/focus markers, Watchlist saved-stocks-first copy/actions, and no three identical market-monitor wrappers
- [ ] Update existing market-monitor/search/watchlist tests only where shared strings or component structure changed
- [ ] Keep validation provider/runtime independent

**Artifacts:**
- `tests/apphost/frontend-purpose-built-home-search-watchlist-tests.sh` (new)
- Existing frontend market-monitor/search/watchlist tests (modified if affected)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run purpose-built module validation: `bash tests/apphost/frontend-purpose-built-home-search-watchlist-tests.sh`
- [ ] Run terminal market monitor validation: `bash tests/apphost/frontend-terminal-market-monitor-tests.sh`
- [ ] Run symbol search exploration validation: `bash tests/apphost/frontend-symbol-search-exploration-tests.sh`
- [ ] Run trading workspace validation: `bash tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] Update docs to describe distinct Home/Search/Watchlist responsibilities and shared lower-level market monitor primitives
- [ ] Update README/PLAN verification inventory/current frontend surface if a new validation script is added
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — distinct module UX responsibilities
- `docs/architecture/paper-trading-workspace.md` — user-facing Home/Search/Watchlist workflow descriptions if affected
- `README.md` — verification inventory/current frontend surface if a new script is added
- `PLAN.md` — active frontend direction if affected

**Check If Affected:**
- `docs/architecture/modules.md` — update if components/workflow ownership changes
- `docs/architecture/provider-abstractions.md` — update only if exact identity behavior changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Home is recognizably a dashboard/overview, not a full duplicate Search/Watchlist market-monitor page
- [ ] Search is search-first with prominent bounded stock search and ranked result actions
- [ ] Watchlist is saved-stocks-first with backend pins, manage/remove, and chart/analysis/backtest actions
- [ ] Shared primitives remain reusable without making the three modules look/copy identical
- [ ] Exact identity, provider-unavailable, no-fake-data, no-order, desktop visibility/scrollbar, and API-only browser boundaries are preserved

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-067): complete Step N — description`
- **Bug fixes:** `fix(TP-067): description`
- **Tests:** `test(TP-067): description`
- **Hydration:** `hydrate: TP-067 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Add fake Home dashboard metrics, hard-coded watchlist symbols, or synthetic market data
- Treat browser localStorage as authoritative watchlist state
- Add backend endpoints, database schema changes, direct provider/runtime/database access, or new persistence
- Add order entry, buy/sell controls, broker execution, or live-trading behavior
- Optimize/redesign mobile in this batch
- Expose secrets, account identifiers, gateway URLs, LEAN workspace paths, process command lines, tokens, or cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
