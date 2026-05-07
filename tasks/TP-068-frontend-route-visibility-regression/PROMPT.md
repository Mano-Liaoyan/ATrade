# Task: TP-068 - Frontend route and visibility regression suite

**Created:** 2026-05-07
**Size:** S

## Review Level: 1 (Plan Only)

**Assessment:** This is a regression/test consolidation task across route, visibility, and documentation checks after the frontend UX changes. It primarily modifies validation scripts/docs, with low security risk and easy reversibility.
**Score:** 2/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 0

## Canonical Task Folder

```
tasks/TP-068-frontend-route-visibility-regression/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Add a final regression net after the layout, routing, chart landing, and purpose-built module changes. The suite should verify the accepted route matrix, `/symbols/[symbol]` removal, desktop browser visibility/scroll ownership guardrails, visible disabled-module routes, and distinct Home/Search/Watchlist surfaces so future iterations do not regress these requirements.

## Dependencies

- **Task:** TP-064 (layout/browser visibility guardrails must be implemented)
- **Task:** TP-065 (canonical route architecture and old symbol route removal must be implemented)
- **Task:** TP-066 (chart landing stored-stock default behavior must be implemented)
- **Task:** TP-067 (purpose-built Home/Search/Watchlist modules must be implemented)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — authoritative route/layout/module requirements
- `README.md` — verification inventory
- `PLAN.md` — current frontend direction

## Environment

- **Workspace:** `tests/apphost/`, `frontend/`, active docs
- **Services required:** None for source/static validation. Optional Next.js dev route checks may use `NEXT_PUBLIC_ATRADE_API_BASE_URL=http://127.0.0.1:1` and must not require real IBKR/iBeam/LEAN.

## File Scope

- `tests/apphost/frontend-terminal-regression-suite-tests.sh` (new, or equivalent consolidated script)
- `tests/apphost/frontend-terminal-route-architecture-tests.sh` (check/update if created by TP-065)
- `tests/apphost/frontend-terminal-layout-visibility-tests.sh` (check/update if created by TP-064)
- `tests/apphost/frontend-chart-watchlist-default-tests.sh` (check/update if created by TP-066)
- `tests/apphost/frontend-purpose-built-home-search-watchlist-tests.sh` (check/update if created by TP-067)
- Existing route/layout frontend tests under `tests/apphost/frontend-*.sh` (check/update stale `/symbols` or duplicate-page assertions)
- `frontend/app/*` (read/check only unless a discovered broken route requires small fix)
- `frontend/components/terminal/*` (read/check only unless a discovered broken test marker requires small fix)
- `frontend/lib/*` (read/check only unless a discovered stale route helper requires small fix)
- `docs/design/atrade-terminal-ui.md`
- `README.md`
- `PLAN.md`
- `tasks/CONTEXT.md` (log discoveries only if needed)

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Consolidate route regression coverage

- [ ] Add or update validation that enumerates all accepted enabled routes: `/`, `/search`, `/watchlist`, `/chart`, `/chart/[symbol]`, `/analysis`, `/analysis/[symbol]`, `/backtest`, `/backtest/[symbol]`, `/status`, and `/help`
- [ ] Add or update validation that enumerates all accepted disabled routes: `/news`, `/portfolio`, `/research`, `/screener`, `/econ`, `/ai`, `/node`, `/orders`
- [ ] Validate `/symbols/[symbol]` is absent from source and route tests; do not expect redirect/alias behavior
- [ ] Validate exact identity query preservation for chart/analysis/backtest links through source-level assertions

**Artifacts:**
- `tests/apphost/frontend-terminal-regression-suite-tests.sh` (new or modified equivalent)
- Existing route tests (modified if needed)

### Step 2: Consolidate visibility and page-purpose regression coverage

- [ ] Add or update validation for TP-064 guardrails: desktop Safari/Firefox/Chrome/Edge are documented targets; page-level overflow stays hidden; rail/workspace/detail/table/module regions own visible internal/custom scroll affordances
- [ ] Add or update validation for TP-066 chart landing: `/chart` contains Stored stocks/default-watchlist markers and no hard-coded demo default symbol
- [ ] Add or update validation for TP-067 module distinction: Home/Search/Watchlist have distinct components/copy/test IDs and are not three identical generic market-monitor wrappers
- [ ] Ensure validation remains provider/runtime independent and does not require real credentials

**Artifacts:**
- `tests/apphost/frontend-terminal-regression-suite-tests.sh` (new or modified equivalent)
- Existing visibility/chart/purpose tests (modified if needed)

### Step 3: Sweep stale tests and docs

- [ ] Search active frontend tests/docs for stale `/symbols/[symbol]`, hash-route-only module expectations, or statements that Home/Search/Watchlist are identical market monitors; update to the new accepted contract
- [ ] Update README and PLAN verification inventories if new scripts were added by TP-064 through TP-068
- [ ] Update `docs/design/atrade-terminal-ui.md` only if final validation discovers missing route/visibility/purpose acceptance language

**Artifacts:**
- `tests/apphost/frontend-*.sh` (modified if affected)
- `README.md` (modified if affected)
- `PLAN.md` (modified if affected)
- `docs/design/atrade-terminal-ui.md` (modified if affected)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run consolidated regression validation: `bash tests/apphost/frontend-terminal-regression-suite-tests.sh`
- [ ] Run route architecture validation: `bash tests/apphost/frontend-terminal-route-architecture-tests.sh`
- [ ] Run layout visibility validation: `bash tests/apphost/frontend-terminal-layout-visibility-tests.sh`
- [ ] Run chart landing validation: `bash tests/apphost/frontend-chart-watchlist-default-tests.sh`
- [ ] Run purpose-built module validation: `bash tests/apphost/frontend-purpose-built-home-search-watchlist-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] New/updated verification scripts listed in README/PLAN where appropriate
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `README.md` — verification inventory if a new consolidated script is added
- `PLAN.md` — active/follow-up direction and verification inventory if affected

**Check If Affected:**
- `docs/design/atrade-terminal-ui.md` — update only if validation exposes missing route/visibility/purpose acceptance language
- `tasks/CONTEXT.md` — log tech debt/discoveries only if final sweep finds deferred work

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Consolidated regression validation covers accepted enabled/disabled route matrix
- [ ] `/symbols/[symbol]` absence is validated
- [ ] Desktop browser visibility/scroll ownership guardrails are validated
- [ ] Chart landing stored-stock/default behavior is validated
- [ ] Distinct Home/Search/Watchlist page purposes are validated
- [ ] No fake data, direct provider/database access, order controls, mobile optimization scope, or secrets are introduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-068): complete Step N — description`
- **Bug fixes:** `fix(TP-068): description`
- **Tests:** `test(TP-068): description`
- **Hydration:** `hydrate: TP-068 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Reintroduce `/symbols/[symbol]`, hash-only routing, page-level scrolling, command UI, or identical Home/Search/Watchlist wrappers
- Add fake market data, hard-coded demo stocks, direct provider/runtime/database access, backend endpoints, or persistence changes
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
