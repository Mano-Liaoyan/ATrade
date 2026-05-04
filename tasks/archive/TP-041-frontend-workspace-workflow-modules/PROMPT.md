# Task: TP-041 - Deepen frontend workspace workflow modules

**Created:** 2026-05-02
**Size:** M

## Review Level: 1 (Plan Only)

**Assessment:** This task stays mostly inside the Next.js frontend and apphost shell tests, extracting workflow modules without intentional visual redesign. Pattern novelty is moderate because frontend rendering modules currently own the orchestration logic.
**Score:** 3/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-041-frontend-workspace-workflow-modules/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Deepen frontend paper-workspace workflow modules so rendering modules receive normalized state and commands instead of owning watchlist migration, exact pin toggling, search debounce/error state, chart HTTP loading, SignalR fallback, and source labeling inline. This matters because the current frontend helpers are shallow adapters while real workflow bugs hide in how rendering modules orchestrate them.

## Dependencies

- **Task:** TP-040 (backend intake modules and HTTP behavior must be stable before frontend workflow extraction)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/paper-trading-workspace.md` — frontend/backed workspace behavior and localStorage rules
- `docs/architecture/modules.md` — frontend module role
- `docs/architecture/provider-abstractions.md` — provider-neutral payload/source metadata

## Environment

- **Workspace:** `frontend/`
- **Services required:** None for TypeScript/build checks; AppHost/frontend scripts must skip cleanly when local runtimes are unavailable

## File Scope

- `frontend/components/TradingWorkspace.tsx`
- `frontend/components/SymbolSearch.tsx`
- `frontend/components/TrendingList.tsx`
- `frontend/components/Watchlist.tsx`
- `frontend/components/SymbolChartView.tsx`
- `frontend/lib/watchlistClient.ts`
- `frontend/lib/watchlistStorage.ts`
- `frontend/lib/marketDataClient.ts`
- `frontend/lib/marketDataStream.ts`
- `frontend/lib/*Workflow*.ts` (new if needed)
- `frontend/types/marketData.ts`
- `frontend/app/symbols/[symbol]/page.tsx`
- `tests/apphost/frontend-workspace-workflow-module-tests.sh` (new)
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`

## Steps

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Extract watchlist and exact pin workflows

- [ ] Create a frontend watchlist workflow module that owns backend load, legacy localStorage migration/fallback, optimistic exact pin toggling, remove actions, and stable error formatting
- [ ] Update `TradingWorkspace`, `Watchlist`, `TrendingList`, and `SymbolSearch` to consume workflow state/commands rather than reimplementing pin logic
- [ ] Preserve localStorage as non-authoritative symbol-only fallback and backend-owned persisted keys as authority
- [ ] Add or update targeted frontend workflow assertions in a new shell test file

**Artifacts:**
- `frontend/lib/*Workflow*.ts` (new/modified)
- `frontend/components/TradingWorkspace.tsx` (modified)
- `tests/apphost/frontend-workspace-workflow-module-tests.sh` (new)

### Step 2: Extract search and chart data workflows

- [ ] Create frontend search/chart workflow modules that own search debounce state, provider error formatting, candle/indicator loading, SignalR subscription, HTTP polling fallback, and source labels
- [ ] Update `SymbolSearch` and `SymbolChartView` to render workflow state while preserving current UI text/markers unless docs/tests need intentional copy updates
- [ ] Keep browser data access behind `ATrade.Api`; no direct Postgres/Timescale/IBKR access
- [ ] Run targeted TypeScript/build and frontend shell tests

**Artifacts:**
- `frontend/lib/*Workflow*.ts` (new/modified)
- `frontend/components/SymbolSearch.tsx` (modified)
- `frontend/components/SymbolChartView.tsx` (modified)

### Step 3: Preserve workspace behavior and test surface

- [ ] Ensure home workspace, symbol page, exact pins, cached read-only fallback, provider-unavailable messages, and SignalR-to-HTTP fallback behavior remain stable
- [ ] Add assertions in `tests/apphost/frontend-workspace-workflow-module-tests.sh` for workflow module seams and no direct database/provider access from frontend
- [ ] Update existing `frontend-trading-workspace-tests.sh` only if user-facing markers intentionally move
- [ ] Run targeted frontend tests

**Artifacts:**
- `tests/apphost/frontend-workspace-workflow-module-tests.sh` (new)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run frontend checks: `cd frontend && npm run build`
- [ ] Run integration tests if affected: `bash tests/apphost/frontend-trading-workspace-tests.sh` and `bash tests/apphost/frontend-workspace-workflow-module-tests.sh`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — frontend workflow module responsibilities if changed
- `docs/architecture/modules.md` — frontend module map if new workflow modules are introduced

**Check If Affected:**
- `README.md` — current runtime surface if frontend behavior changes
- `docs/architecture/provider-abstractions.md` — frontend provider-neutral payload behavior if changed

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Rendering modules are thinner; watchlist, search, chart, and stream fallback behavior live behind frontend workflow module interfaces
- [ ] Existing UI behavior and markers remain stable unless intentionally documented
- [ ] Frontend still talks only to `ATrade.Api`

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-041): complete Step N — description`
- **Bug fixes:** `fix(TP-041): description`
- **Tests:** `test(TP-041): description`
- **Hydration:** `hydrate: TP-041 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Redesign the UI visually unless required to preserve behavior
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
