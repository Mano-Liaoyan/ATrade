# Task: TP-052 - Simplify workspace layout and remove extra chrome

**Created:** 2026-05-05
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This task simplifies the shared frontend layout used by all workspace modules and changes scroll/viewport behavior across the active UI. It remains frontend-only and reversible, but it touches app composition, CSS layout contracts, validation scripts, and active docs.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-052-simplify-workspace-layout/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Simplify the common paper workspace layout after TP-051 removes the command system. The active page should be full-bleed with no left/right outer margins, no background grid, and no page-level vertical scrolling. Remove the shell-only context panel, monitor strip, and footer/status strip: no `terminal-workspace-layout__context`, `terminal-context-summary`, `terminal-workspace-layout__monitor`, `terminal-monitor-panel`, `terminal-status-strip`, context/monitor splitters, or layout reset button should remain in the active page. Keep the real module content intact, especially the dense market monitor inside HOME/SEARCH/WATCHLIST, chart and analysis workspaces, provider diagnostics, disabled modules, `ATrade.Api` boundaries, and no-order safety copy.

## Dependencies

- **Task:** TP-051 (terminal branding and command system must be removed first)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — layout/visual design authority that must be revised for the simplified shell
- `docs/architecture/paper-trading-workspace.md` — paper-only safety and browser/API boundary contract
- `docs/architecture/modules.md` — frontend module/component/workflow ownership map
- `README.md` — current runtime surface and verification entry points
- `PLAN.md` — active queue and follow-up direction
- `docs/architecture/provider-abstractions.md` — load only if provider/source label behavior changes
- `docs/architecture/analysis-engines.md` — load only if analysis user-facing states change

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, and active docs
- **Services required:** None for source/build checks

## File Scope

- `frontend/components/terminal/ATradeTerminalApp.tsx`
- `frontend/components/terminal/TerminalWorkspaceLayout.tsx`
- `frontend/components/terminal/TerminalStatusStrip.tsx` (delete if unused)
- `frontend/lib/terminalLayoutPersistence.ts`
- `frontend/types/terminal.ts`
- `frontend/components/terminal/index.ts`
- `frontend/app/globals.css`
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh` (new)
- `tests/apphost/frontend-no-command-shell-tests.sh`
- `tests/apphost/frontend-terminal-shell-ui-tests.sh`
- `tests/apphost/frontend-terminal-cutover-tests.sh`
- `tests/apphost/frontend-terminal-market-monitor-tests.sh` (check if affected)
- `README.md`
- `PLAN.md`
- `docs/design/atrade-terminal-ui.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Remove context, monitor-strip, and footer chrome from app composition

- [ ] Update `ATradeTerminalApp` so it no longer renders `TerminalContextSummary`, `TerminalMonitorPanel`, `TerminalStatusStrip`, or props named `context`/`monitor` into `TerminalWorkspaceLayout`
- [ ] Delete `TerminalContextSummary`, `TerminalMonitorPanel`, and `TerminalStatusStrip.tsx` if no active imports remain
- [ ] Remove the shell-only HTML regions matching `terminal-workspace-layout__context`, `terminal-context-summary`, `terminal-workspace-layout__monitor`, and `terminal-monitor-panel`
- [ ] Preserve the actual HOME/SEARCH/WATCHLIST `TerminalMarketMonitor` module content and chart/analysis/status/help/disabled module surfaces

**Artifacts:**
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/components/terminal/TerminalWorkspaceLayout.tsx` (modified)
- `frontend/components/terminal/TerminalStatusStrip.tsx` (deleted if unused)
- `frontend/components/terminal/index.ts` (modified if exports change)

### Step 2: Refactor layout and persistence to a single full-viewport workspace

- [ ] Refactor `TerminalWorkspaceLayout` to a single primary content region with no context/monitor splitters, no resize pointer handlers, no layout reset button, and no context/monitor size CSS variables
- [ ] Update `frontend/types/terminal.ts` and `terminalLayoutPersistence.ts` to remove context/monitor layout regions and persisted sizes, or reduce persistence to only still-used non-sensitive UI preferences
- [ ] Ensure the page shell fills the viewport width without centered max-width or `margin: 0 auto`; remove left/right outer gutters while preserving reasonable internal module spacing
- [ ] Ensure the main page/body is not vertically scrollable; use viewport-height layout with page-level `overflow: hidden` and internal module scrolling only where needed for long tables/content

**Artifacts:**
- `frontend/components/terminal/TerminalWorkspaceLayout.tsx` (modified)
- `frontend/lib/terminalLayoutPersistence.ts` (modified)
- `frontend/types/terminal.ts` (modified)
- `frontend/app/globals.css` (modified)

### Step 3: Remove background grid styling and add layout validation

- [ ] Remove the background grid from `frontend/app/globals.css`, including grid-line gradients/background-size on the app shell and any now-unused grid token/CSS that only exists for that background
- [ ] Create `tests/apphost/frontend-simplified-workspace-layout-tests.sh` to assert active frontend source/rendered markup no longer contains the removed context panel, monitor strip, footer/status strip, splitters, layout reset, grid background, centered max-width shell, horizontal auto margins, or page-level scrolling
- [ ] Update `frontend-terminal-shell-ui-tests.sh` and `frontend-terminal-cutover-tests.sh` so they expect the simplified layout and no longer assert the removed regions
- [ ] Keep or add assertions that module rail/workflow content, `TerminalMarketMonitor`, chart/analysis workspaces, provider diagnostics, disabled modules, and no-order/API-boundary safety remain present

**Artifacts:**
- `frontend/app/globals.css` (modified)
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh` (new)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (modified)
- `tests/apphost/frontend-terminal-cutover-tests.sh` (modified)
- `tests/apphost/frontend-terminal-market-monitor-tests.sh` (modified only if affected)

### Step 4: Update active documentation and verification inventory

- [ ] Update the frontend design doc to describe the simplified full-bleed, non-page-scroll layout and removal of context/monitor/footer chrome
- [ ] Update paper workspace and module docs so they no longer describe resizable primary/context/monitor panels, status strip/footer, or background grid as current behavior
- [ ] Update README verification entry points with the new simplified-layout validation script
- [ ] Update PLAN follow-up direction so future frontend work builds on the simplified module workspace layout

**Artifacts:**
- `docs/design/atrade-terminal-ui.md` (modified)
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `README.md` (modified)
- `PLAN.md` (modified)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run simplified layout validation: `bash tests/apphost/frontend-simplified-workspace-layout-tests.sh`
- [ ] Run no-command validation from TP-051: `bash tests/apphost/frontend-no-command-shell-tests.sh`
- [ ] Run updated shell/cutover validations: `bash tests/apphost/frontend-terminal-shell-ui-tests.sh` and `bash tests/apphost/frontend-terminal-cutover-tests.sh`
- [ ] Run affected workflow validations: `bash tests/apphost/frontend-terminal-market-monitor-tests.sh` and `bash tests/apphost/frontend-terminal-chart-analysis-tests.sh`
- [ ] Run frontend checks: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — simplified full-bleed layout, no context/monitor/footer chrome, no background grid, no page-level scroll
- `docs/architecture/paper-trading-workspace.md` — current frontend layout and persistence behavior after simplification
- `docs/architecture/modules.md` — frontend component ownership after removing status strip/context/monitor shell chrome
- `README.md` — verification entry-point list and current runtime frontend surface
- `PLAN.md` — active follow-up direction after simplified layout task

**Check If Affected:**
- `docs/architecture/provider-abstractions.md` — update only if provider/source label behavior changes, which this task should avoid
- `docs/architecture/analysis-engines.md` — update only if analysis user-facing states change, which this task should avoid

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] No active page markup/source renders the monitor strip snippet (`terminal-workspace-layout__monitor` / `terminal-monitor-panel`) or the context aside snippet (`terminal-workspace-layout__context` / `terminal-context-summary`)
- [ ] No active page renders `TerminalStatusStrip` or a footer/status-strip region
- [ ] No context/monitor splitters, layout reset button, or context/monitor persisted size variables remain active
- [ ] App shell spans full viewport width with no left/right outer margins and no centered max-width container
- [ ] Background grid is removed from the active page
- [ ] Main page/body does not vertically scroll; long workspace content scrolls inside module regions when necessary
- [ ] HOME/SEARCH/WATCHLIST market monitor content, CHART, ANALYSIS, STATUS, HELP, disabled modules, no-order safety, and `ATrade.Api` browser boundary remain intact

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-052): complete Step N — description`
- **Bug fixes:** `fix(TP-052): description`
- **Tests:** `test(TP-052): description`
- **Hydration:** `hydrate: TP-052 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Reintroduce a command system removed by TP-051
- Remove the module rail unless a future user-approved task explicitly requests it
- Remove the dense `TerminalMarketMonitor` module content from HOME/SEARCH/WATCHLIST; this task only removes the shell-level monitor strip
- Hide provider-unavailable/provider-not-configured/authentication-required states or exact identity metadata
- Add fake data, direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, or LEAN
- Add real order placement, simulated order-entry UI, or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
