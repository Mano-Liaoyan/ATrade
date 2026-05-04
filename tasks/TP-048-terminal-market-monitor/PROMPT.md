# Task: TP-048 - Rebuild search, trending, and watchlist as a terminal market monitor

**Created:** 2026-05-04
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This aggressively replaces the current search/watchlist/trending presentation with a dense terminal market monitor while preserving backend API contracts and exact instrument identity. It touches core frontend workflows/components and tests but does not alter backend persistence or security boundaries.
**Score:** 4/8 — Blast radius: 1, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-048-terminal-market-monitor/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Replace the old search, trending, and watchlist UI with a Fincept-style terminal market monitor: dense sortable rows, search command integration, ranked/bounded IBKR result exploration, saved pin/watchlist state, selected-instrument detail panel, and open-chart/open-analysis actions. The monitor must preserve ATrade's exact provider-market identity and backend-owned watchlist authority while eliminating the long flat search/list UI.

## Dependencies

- **Task:** TP-047 (terminal shell, command registry, module rail, and layout must exist)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — market monitor and visual-density requirements
- `docs/architecture/paper-trading-workspace.md` — search/watchlist/trending and exact identity contract
- `docs/architecture/modules.md` — frontend workflow/client boundaries
- `docs/architecture/provider-abstractions.md` — provider-neutral search/trending identity fields and source metadata

## Environment

- **Workspace:** `frontend/`
- **Services required:** None for source/build checks; provider-backed runtime checks must skip cleanly if local IBKR/iBeam is unavailable

## File Scope

- `frontend/components/terminal/TerminalMarketMonitor.tsx` (new)
- `frontend/components/terminal/MarketMonitorTable.tsx` (new)
- `frontend/components/terminal/MarketMonitorSearch.tsx` (new)
- `frontend/components/terminal/MarketMonitorFilters.tsx` (new)
- `frontend/components/terminal/MarketMonitorDetailPanel.tsx` (new)
- `frontend/lib/terminalMarketMonitorWorkflow.ts` (new)
- `frontend/lib/symbolSearchWorkflow.ts` (modify, reuse, or retire)
- `frontend/lib/watchlistWorkflow.ts`
- `frontend/lib/watchlistClient.ts`
- `frontend/lib/marketDataClient.ts`
- `frontend/lib/instrumentIdentity.ts`
- `frontend/types/marketData.ts`
- `frontend/components/SymbolSearch.tsx` (delete or retire if replaced)
- `frontend/components/TrendingList.tsx` (delete or retire if replaced)
- `frontend/components/Watchlist.tsx` (delete or retire if replaced)
- `frontend/components/MarketLogo.tsx` (reuse, replace, or retire)
- `frontend/components/terminal/ATradeTerminalApp.tsx`
- `frontend/lib/terminalCommandRegistry.ts`
- `frontend/app/globals.css`
- `tests/apphost/frontend-terminal-market-monitor-tests.sh` (new)
- `tests/apphost/frontend-symbol-search-exploration-tests.sh`
- `tests/apphost/frontend-workspace-workflow-module-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `README.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Model market monitor state and actions

- [ ] Create `terminalMarketMonitorWorkflow` or equivalent that combines trending symbols, bounded/ranked search results, watchlist pins, provider/source state, filters, sorting, selected instrument, and open-module actions
- [ ] Preserve existing API clients and exact identity helpers; browser calls must still go through `ATrade.Api` only and search must still use explicit capped limits
- [ ] Keep backend watchlist authority, optimistic pin/unpin states, cached fallback copy, provider/authentication error copy, debounce/minimum-query behavior, and exact instrument query handoff
- [ ] Add targeted source assertions for no unbounded search fetches and no direct provider/database/browser secrets access

**Artifacts:**
- `frontend/lib/terminalMarketMonitorWorkflow.ts` (new)
- `frontend/lib/symbolSearchWorkflow.ts` (modified, reused, or retired)
- `frontend/lib/watchlistWorkflow.ts` (modified if needed)
- `frontend/lib/marketDataClient.ts` (modified only if clearer request options are needed)
- `frontend/types/marketData.ts` (modified if monitor view models are exported)
- `tests/apphost/frontend-terminal-market-monitor-tests.sh` (new)

### Step 2: Implement dense terminal monitor components

- [ ] Create `TerminalMarketMonitor`, `MarketMonitorTable`, `MarketMonitorSearch`, `MarketMonitorFilters`, and `MarketMonitorDetailPanel` using terminal primitives from TP-046
- [ ] Render trending/search/watchlist entries as dense rows with symbol, name, provider, provider id when available, exchange, currency, asset class, source, score/rank, saved-pin state, and clear loading/error/unavailable states
- [ ] Add sorting, metadata filter chips, show-more/show-less result exploration, row selection, keyboard/focus-friendly controls, and compact laptop behavior
- [ ] Provide chart/analysis actions that route through the terminal command/module registry while preserving exact identity query parameters

**Artifacts:**
- `frontend/components/terminal/TerminalMarketMonitor.tsx` (new)
- `frontend/components/terminal/MarketMonitorTable.tsx` (new)
- `frontend/components/terminal/MarketMonitorSearch.tsx` (new)
- `frontend/components/terminal/MarketMonitorFilters.tsx` (new)
- `frontend/components/terminal/MarketMonitorDetailPanel.tsx` (new)
- `frontend/app/globals.css` (modified)

### Step 3: Integrate monitor into commands and retire old list UI

- [ ] Wire `SEARCH <query>`, `WATCH` / `WATCHLIST`, and `HOME` terminal commands to focus or prefill the market monitor as appropriate
- [ ] Replace old `SymbolSearch`, `TrendingList`, and `Watchlist` usage in active routes/modules; delete obsolete components if no longer imported
- [ ] Ensure visible-disabled `SCREENER` remains unavailable rather than becoming a fake screener through monitor filters
- [ ] Update tests previously targeting the old search/list layout to target the terminal market monitor behavior and markers

**Artifacts:**
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/lib/terminalCommandRegistry.ts` (modified)
- `frontend/components/SymbolSearch.tsx` (deleted or retired)
- `frontend/components/TrendingList.tsx` (deleted or retired)
- `frontend/components/Watchlist.tsx` (deleted or retired)
- `tests/apphost/frontend-symbol-search-exploration-tests.sh` (modified)
- `tests/apphost/frontend-workspace-workflow-module-tests.sh` (modified)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run market monitor validation: `bash tests/apphost/frontend-terminal-market-monitor-tests.sh`
- [ ] Run search exploration validation: `bash tests/apphost/frontend-symbol-search-exploration-tests.sh`
- [ ] Run workflow module validation: `bash tests/apphost/frontend-workspace-workflow-module-tests.sh`
- [ ] Run frontend workspace validation: `bash tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Run frontend checks: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — describe terminal market monitor behavior, bounded search, watchlist authority, exact identity rows, and no fake screener/data
- `docs/architecture/modules.md` — record market monitor workflow/component ownership and replacement of old list components
- `README.md` — add `tests/apphost/frontend-terminal-market-monitor-tests.sh` to verification entry points once created

**Check If Affected:**
- `docs/design/atrade-terminal-ui.md` — update only if implementation requires approved monitor interaction refinements
- `docs/architecture/provider-abstractions.md` — update only if search/trending payload interpretation changes, which this task should avoid

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Search, trending, and watchlist now live in a dense terminal market monitor rather than separate long/list panels
- [ ] Monitor supports bounded ranked search, filters, sorting, selected-instrument detail, pin/unpin, and open chart/analysis actions
- [ ] Exact provider-market identity is visible and preserved for chart/pin actions
- [ ] No fake screener, fake market data, direct provider/database access, or order-entry behavior is introduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-048): complete Step N — description`
- **Bug fixes:** `fix(TP-048): description`
- **Tests:** `test(TP-048): description`
- **Hydration:** `hydrate: TP-048 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Fetch or render unbounded search result lists in the browser
- Hide provider, provider id, exchange, currency, or asset-class identity from pin/chart actions
- Turn `SCREENER` into a fake full screener; it remains visible-disabled in this batch
- Copy FinceptTerminal/Bloomberg source, assets, screenshots, branding, or pixel-identical proprietary layouts
- Add direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, or LEAN
- Add real order placement, simulated order-entry UI, or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
