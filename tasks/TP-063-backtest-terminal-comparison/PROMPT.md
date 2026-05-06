# Task: TP-063 - Terminal backtest comparison and equity overlay

**Created:** 2026-05-05
**Size:** M

## Review Level: 1 (Plan Only)

**Assessment:** This is a focused frontend enhancement on top of the BACKTEST workspace: selected-run comparison, metric table, and equity overlays using existing saved result payloads. It is reversible and does not change backend security or persistence contracts.
**Score:** 3/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-063-backtest-terminal-comparison/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Complete the backtesting MVP frontend by adding saved-run comparison: select completed runs from history, compare key metrics side-by-side, and overlay strategy equity curves plus buy-and-hold benchmark curves. The comparison must use persisted `/api/backtests` result payloads only, stay inside the enabled BACKTEST module, and avoid export, optimization, fake results, direct provider access, or order-routing behavior.

## Dependencies

- **Task:** TP-062 (terminal backtest run/history/retry workspace must exist)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — terminal UI design authority
- `docs/architecture/backtesting.md` — saved result/comparison payload contract
- `docs/architecture/paper-trading-workspace.md` — frontend/backend and no-order rules
- `docs/architecture/modules.md` — frontend workflow/component ownership
- `README.md` — verification entry points
- `PLAN.md` — active queue context

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, active docs
- **Services required:** None for source/build validation. Real provider/LEAN runtimes are not required.

## File Scope

- `frontend/types/backtesting.ts` (check if affected)
- `frontend/lib/backtestClient.ts` (check if affected)
- `frontend/lib/terminalBacktestWorkflow.ts`
- `frontend/components/terminal/TerminalBacktestWorkspace.tsx`
- `frontend/components/terminal/BacktestComparisonPanel.tsx` (new, or equivalent local component)
- `frontend/app/globals.css`
- `tests/apphost/frontend-terminal-backtest-comparison-tests.sh` (new)
- `tests/apphost/frontend-terminal-backtest-workspace-tests.sh` (check/update if affected)
- `docs/design/atrade-terminal-ui.md`
- `docs/architecture/backtesting.md`
- `docs/architecture/paper-trading-workspace.md` (check if affected)
- `docs/architecture/modules.md` (check if affected)
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Add comparison selection state and view-model helpers

- [ ] Extend the terminal backtest workflow with selected completed-run IDs, comparison eligibility, selected run summaries, normalized equity/benchmark series, and clear/remove-selection actions
- [ ] Limit comparison to completed runs with real persisted result/equity data; failed/queued/running/cancelled runs remain visible in history but are not selectable for comparison
- [ ] Add deterministic color/label helpers for strategy curve vs buy-and-hold benchmark without relying on proprietary terminal palettes or copied chart assets
- [ ] Add unit/source-level checks as appropriate for selection and normalization helpers

**Artifacts:**
- `frontend/lib/terminalBacktestWorkflow.ts` (modified)
- `frontend/types/backtesting.ts` (modified if needed)

### Step 2: Render comparison table and equity overlay

- [ ] Add a comparison panel inside `TerminalBacktestWorkspace` (or a dedicated child component) with selected-run cards/table for strategy, symbol, range, capital source, return, max drawdown, win rate, trade count, final equity, benchmark return, and status/source metadata
- [ ] Render an accessible equity overlay using existing frontend primitives/SVG/CSS or an already-approved charting dependency; do not introduce a new charting library unless absolutely necessary and documented
- [ ] Show both strategy equity and buy-and-hold benchmark curves for each selected run with clear legends and empty-state messaging when fewer than two completed runs are selected
- [ ] Preserve module-owned scrolling/responsive layout without reintroducing page-level vertical scrolling, old shell chrome, or layout persistence

**Artifacts:**
- `frontend/components/terminal/TerminalBacktestWorkspace.tsx` (modified)
- `frontend/components/terminal/BacktestComparisonPanel.tsx` (new, or equivalent)
- `frontend/app/globals.css` (modified)

### Step 3: Add comparison validation coverage

- [ ] Create `tests/apphost/frontend-terminal-backtest-comparison-tests.sh` validating comparison selection, completed-run-only behavior, metric labels, equity overlay/benchmark strings, no export controls, no fake demo data, and no direct provider/runtime/database access
- [ ] Update the TP-062 backtest workspace validation only where comparison changes shared strings or structure
- [ ] Ensure validation is source/build based and does not require real IBKR/iBeam/LEAN credentials

**Artifacts:**
- `tests/apphost/frontend-terminal-backtest-comparison-tests.sh` (new)
- `tests/apphost/frontend-terminal-backtest-workspace-tests.sh` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run comparison validation: `bash tests/apphost/frontend-terminal-backtest-comparison-tests.sh`
- [ ] Run backtest workspace validation: `bash tests/apphost/frontend-terminal-backtest-workspace-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] Update active docs to describe saved-run comparison, completed-run-only selection, metric table, equity/benchmark overlay, and explicit no-export/no-optimization scope
- [ ] Update README/PLAN verification inventory/current frontend surface if affected
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — BACKTEST comparison UX within the terminal module
- `docs/architecture/backtesting.md` — frontend comparison behavior and result fields used
- `README.md` — verification entry points/current frontend surface if adding new validation script
- `PLAN.md` — active/follow-up direction if affected

**Check If Affected:**
- `docs/architecture/paper-trading-workspace.md` — update only if frontend workspace contract changes
- `docs/architecture/modules.md` — update only if component/workflow ownership changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Users can select completed saved backtests for side-by-side comparison
- [ ] Comparison table shows key metrics and source/capital metadata
- [ ] Equity overlay shows strategy equity and buy-and-hold benchmark curves from persisted result data
- [ ] Queued/running/failed/cancelled runs are not selectable for comparison
- [ ] No export, optimization, fake demo data, synthetic curves, direct provider/runtime access, order controls, or secrets/account identifiers are introduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-063): complete Step N — description`
- **Bug fixes:** `fix(TP-063): description`
- **Tests:** `test(TP-063): description`
- **Hydration:** `hydrate: TP-063 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Add backend endpoints, persistence schema changes, export, optimization, custom strategy code, multi-symbol portfolio backtests, or new charting dependencies unless unavoidable and documented
- Add fake runs, fixture comparison data, synthetic equity curves, or fake benchmark results
- Add direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, LEAN, Docker, or provider runtimes
- Add order entry, buy/sell controls, broker execution, or live-trading behavior
- Expose secrets, account identifiers, gateway URLs, LEAN workspace paths, process command lines, tokens, or cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
