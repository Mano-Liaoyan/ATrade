# Task: TP-043 - Redesign workspace navigation with a terminal-style shell

**Created:** 2026-05-04
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This is a major frontend UI refactor that changes the information architecture, layout components, CSS system, and integration test markers while preserving backend/API behavior. It is reversible and does not touch auth or data persistence, but the visual/navigation blast radius is broad enough to require plan and code review.
**Score:** 4/8 — Blast radius: 1, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-043-terminal-workspace-shell/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Refactor the paper-trading workspace UI into a more navigable, terminal-inspired shell that makes search, watchlist, trending opportunities, chart context, provider status, and analysis entry points easy to find. Use industry finance terminals such as Bloomberg Terminal only as high-level inspiration for command-first navigation, dense information panels, persistent context, and keyboard-friendly workflows; do **not** copy proprietary Bloomberg visuals, assets, trademarks, or exact layouts.

## Dependencies

- **Task:** TP-042 (chart range controls must use corrected lookback semantics before layout work repositions them)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/paper-trading-workspace.md` — frontend workspace behavior, paper-only safety, workflow boundaries
- `docs/architecture/modules.md` — frontend module map and workflow module responsibilities
- `docs/architecture/provider-abstractions.md` — provider-neutral payload behavior that UI labels must preserve

## Environment

- **Workspace:** `frontend/`
- **Services required:** None for source/build checks; local API/frontend shell tests must skip cleanly when optional local runtimes are unavailable

## File Scope

- `frontend/app/page.tsx`
- `frontend/app/globals.css`
- `frontend/components/TerminalWorkspaceShell.tsx` (new)
- `frontend/components/WorkspaceCommandBar.tsx` (new)
- `frontend/components/WorkspaceNavigation.tsx` (new)
- `frontend/components/WorkspaceContextPanel.tsx` (new)
- `frontend/components/TradingWorkspace.tsx`
- `frontend/components/SymbolChartView.tsx`
- `frontend/components/SymbolSearch.tsx`
- `frontend/components/TrendingList.tsx`
- `frontend/components/Watchlist.tsx`
- `frontend/components/BrokerPaperStatus.tsx`
- `frontend/components/AnalysisPanel.tsx`
- `frontend/lib/workspaceShellWorkflow.ts` (new if useful)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (new)
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `tests/apphost/frontend-workspace-workflow-module-tests.sh`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Create reusable workspace shell primitives

- [ ] Create `TerminalWorkspaceShell`, `WorkspaceCommandBar`, `WorkspaceNavigation`, and `WorkspaceContextPanel` components that provide a persistent header/command area, navigational anchors, primary content region, and right-side context without introducing a new UI framework
- [ ] Add CSS tokens/classes in `frontend/app/globals.css` for dense terminal-style panels, high-contrast navigation, responsive collapse, focus states, and accessible keyboard/tab order
- [ ] Preserve current paper-only, provider-state, and exact instrument identity messaging; the shell must not add broker actions or fake market data
- [ ] Create `tests/apphost/frontend-terminal-shell-ui-tests.sh` with source/SSR assertions for shell components, navigation landmarks, focusable controls, and no proprietary Bloomberg assets

**Artifacts:**
- `frontend/components/TerminalWorkspaceShell.tsx` (new)
- `frontend/components/WorkspaceCommandBar.tsx` (new)
- `frontend/components/WorkspaceNavigation.tsx` (new)
- `frontend/components/WorkspaceContextPanel.tsx` (new)
- `frontend/app/globals.css` (modified)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (new)

### Step 2: Refactor the home workspace into navigable panels

- [ ] Update `frontend/app/page.tsx` and `TradingWorkspace.tsx` so search, trending, watchlist, and provider/status context live inside the new shell with clear visual hierarchy and stable `data-testid` markers
- [ ] Keep `useWatchlistWorkflow`, `useSymbolSearchWorkflow`, and market-data clients behind rendering components; do not reintroduce direct client/storage orchestration into renderers
- [ ] Rework `TrendingList`, `Watchlist`, and `SymbolSearch` presentation to fit the shell while preserving pin/unpin behavior, backend watchlist authority, and provider-unavailable copy
- [ ] Run targeted frontend build/shell tests for the home workspace

**Artifacts:**
- `frontend/app/page.tsx` (modified)
- `frontend/components/TradingWorkspace.tsx` (modified)
- `frontend/components/SymbolSearch.tsx` (modified)
- `frontend/components/TrendingList.tsx` (modified)
- `frontend/components/Watchlist.tsx` (modified)
- `frontend/app/globals.css` (modified)

### Step 3: Refactor the chart workspace into the same shell

- [ ] Update `SymbolChartView.tsx` so chart, range controls, search-another-symbol, analysis, and broker status are arranged in the same terminal-style shell/navigation model
- [ ] Ensure chart controls from TP-042 remain visible and understandable on desktop and mobile, including range selector, stream state, current source, and fallback notes
- [ ] Preserve `BrokerPaperStatus`, `AnalysisPanel`, candlestick rendering, indicator rendering, and SignalR-to-HTTP fallback behavior
- [ ] Update existing frontend integration assertions only where user-facing markers intentionally move

**Artifacts:**
- `frontend/components/SymbolChartView.tsx` (modified)
- `frontend/components/BrokerPaperStatus.tsx` (modified if needed)
- `frontend/components/AnalysisPanel.tsx` (modified if needed)
- `frontend/app/globals.css` (modified)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run frontend checks: `cd frontend && npm run build`
- [ ] Run integration/shell tests: `bash tests/apphost/frontend-terminal-shell-ui-tests.sh`, `bash tests/apphost/frontend-trading-workspace-tests.sh`, and `bash tests/apphost/frontend-workspace-workflow-module-tests.sh`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — describe the terminal-inspired workspace shell, navigation regions, and paper-only safety constraints
- `docs/architecture/modules.md` — update frontend module map for new shell components/workflow helper if introduced
- `README.md` — verification entry point list if `frontend-terminal-shell-ui-tests.sh` is added

**Check If Affected:**
- `docs/architecture/provider-abstractions.md` — update only if provider/source labels or frontend payload interpretation changes
- `PLAN.md` — update only if this task discovers follow-up UI work that must be queued separately

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Home workspace and chart workspace share a coherent terminal-style shell with clear navigation landmarks
- [ ] Search, watchlist, trending, chart controls, provider status, and analysis entry points are easier to locate without losing existing behavior
- [ ] UI uses original ATrade implementation/CSS only; no proprietary Bloomberg assets, copied layouts, or new external UI dependencies
- [ ] Frontend still talks only to `ATrade.Api`

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-043): complete Step N — description`
- **Bug fixes:** `fix(TP-043): description`
- **Tests:** `test(TP-043): description`
- **Hydration:** `hydrate: TP-043 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Copy Bloomberg Terminal UI, assets, colors, trademarks, screenshots, or proprietary layouts; use industry terminals only as broad UX inspiration
- Add a new UI component library or design dependency unless explicitly justified and approved through review
- Add direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, or LEAN
- Add real order placement or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
