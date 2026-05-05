# Task: TP-053 - Remove top chrome and compact market filters

**Created:** 2026-05-05
**Size:** M

## Review Level: 1 (Plan Only)

**Assessment:** This is a frontend-only layout/density cleanup using existing terminal workspace patterns, with test and doc updates. It touches the shared app frame and market-monitor filter presentation but does not change provider contracts, auth, persistence, or data models.
**Score:** 2/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 0

## Canonical Task Folder

```
tasks/TP-053-remove-top-chrome-compact-filters/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Remove the visible top ATrade workspace brand header and the yellow paper-safety strip from the active paper workspace so the module frame starts directly with the rail/workspace content. Preserve the paper-only safety contract in the remaining HOME/help/status/disabled-module/no-order surfaces and validation docs. Also compact the market-monitor filters so filtering stays available, accessible, and count-preserving while taking much less vertical space.

## Dependencies

- **None**

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — active frontend visual/density authority
- `docs/architecture/paper-trading-workspace.md` — paper-only safety and browser/API boundary contract
- `docs/architecture/modules.md` — frontend module/component/workflow ownership map
- `README.md` — current runtime surface and verification entry points
- `PLAN.md` — active queue and follow-up direction
- `docs/architecture/provider-abstractions.md` — load only if provider/source label behavior changes; this task should avoid that
- `docs/architecture/analysis-engines.md` — load only if analysis user-facing states change; this task should avoid that

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, and active docs
- **Services required:** None for source/build checks; frontend dev-server validation scripts must keep using fake/unavailable API base URLs when they do not require live services

## File Scope

- `frontend/components/terminal/ATradeTerminalApp.tsx`
- `frontend/components/terminal/MarketMonitorFilters.tsx`
- `frontend/components/terminal/TerminalMarketMonitor.tsx` (only if needed for compact-mode wiring/copy)
- `frontend/app/globals.css`
- `tests/apphost/frontend-top-chrome-filter-density-tests.sh` (new)
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh`
- `tests/apphost/frontend-terminal-market-monitor-tests.sh`
- `tests/apphost/frontend-no-command-shell-tests.sh` (check if affected)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (check if affected)
- `tests/apphost/frontend-terminal-cutover-tests.sh` (check if affected)
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

### Step 1: Remove the visible app header and safety strip

- [ ] Update `frontend/components/terminal/ATradeTerminalApp.tsx` so it no longer renders `<header className="atrade-terminal-app__header">`, `.atrade-terminal-app__brand`, `ATrade Workspace`, `Paper Trading Workspace`, or the visible `terminal-safety-strip` block
- [ ] Keep the `sr-only` navigation status, `TerminalModuleRail`, `TerminalWorkspaceLayout`, active module content, disabled module content, and all no-order/safety messaging that belongs inside actual modules
- [ ] Update `frontend/app/globals.css` so the app grid no longer reserves header/safety-strip rows and remove now-unused `.atrade-terminal-app__header`, `.atrade-terminal-app__brand`, and `.terminal-safety-strip` styling
- [ ] Ensure the active workspace still fills the full viewport and preserves no page-level vertical scrolling after the top chrome is removed

**Artifacts:**
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/app/globals.css` (modified)

### Step 2: Compact market-monitor filters without losing behavior

- [ ] Refactor `frontend/components/terminal/MarketMonitorFilters.tsx` into a denser filter bar/section: shorter header, no long explanatory paragraph consuming its own row, active-count and Clear-all actions retained, and filter groups/chips arranged compactly
- [ ] Preserve accessibility and behavior: `data-testid="market-monitor-filters"`, `aria-label`, fieldset/legend semantics or equivalent accessible labels, `aria-pressed`, `data-monitor-filter-key`, `data-monitor-filter-value`, row-count `aria-label`s, selected-filter toggling, and Clear-all disablement
- [ ] Update `frontend/app/globals.css` to reduce filter padding, gaps, legend/chip spacing, and wrapping footprint while keeping touch/click targets usable and readable across desktop/mobile breakpoints
- [ ] Keep filtering local to the capped search/trending/watchlist payload; do not fetch additional rows or alter provider/search/watchlist workflow semantics

**Artifacts:**
- `frontend/components/terminal/MarketMonitorFilters.tsx` (modified)
- `frontend/components/terminal/TerminalMarketMonitor.tsx` (modified only if compact wiring/copy changes)
- `frontend/app/globals.css` (modified)

### Step 3: Add focused validation for removed chrome and filter density

- [ ] Create `tests/apphost/frontend-top-chrome-filter-density-tests.sh` to assert active source/rendered markup no longer contains `atrade-terminal-app__header`, `atrade-terminal-app__brand`, `terminal-safety-strip`, `ATrade Workspace`, or `Paper Trading Workspace`
- [ ] In the new validation script, assert the module rail, workspace layout, market monitor, paper-only/no-order module copy, and provider/API boundary surfaces remain present
- [ ] In the new validation script, assert market-monitor filters remain present and interactive by checking filter test IDs/data attributes, active-count/Clear-all controls, `aria-pressed`, and row-count labels while rejecting the retired long filter explainer copy
- [ ] Update affected existing apphost frontend scripts so their expectations match the removed header/safety strip and compact filter layout

**Artifacts:**
- `tests/apphost/frontend-top-chrome-filter-density-tests.sh` (new)
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh` (modified)
- `tests/apphost/frontend-terminal-market-monitor-tests.sh` (modified)
- `tests/apphost/frontend-no-command-shell-tests.sh` (modified only if affected)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (modified only if affected)
- `tests/apphost/frontend-terminal-cutover-tests.sh` (modified only if affected)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run new chrome/filter validation: `bash tests/apphost/frontend-top-chrome-filter-density-tests.sh`
- [ ] Run affected layout/market-monitor validations: `bash tests/apphost/frontend-simplified-workspace-layout-tests.sh` and `bash tests/apphost/frontend-terminal-market-monitor-tests.sh`
- [ ] Run no-command/shell/cutover validations if touched: `bash tests/apphost/frontend-no-command-shell-tests.sh`, `bash tests/apphost/frontend-terminal-shell-ui-tests.sh`, and `bash tests/apphost/frontend-terminal-cutover-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] Update the active design/workspace/module docs so they describe the rail-first workspace without the top brand header or visible safety strip, and describe filters as compact controls
- [ ] Update README/PLAN verification inventory or current frontend surface text if it references the removed top chrome or needs the new validation script listed
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — rail-first workspace frame, removed top header/safety strip, compact market-monitor filter density
- `docs/architecture/paper-trading-workspace.md` — paper-only safety remains enforced without a global visible safety strip; compact market monitor filter presentation
- `docs/architecture/modules.md` — frontend component ownership after removing app-level header/safety strip and compacting filters
- `README.md` — verification entry-point list/current runtime surface if affected by the new validation script or removed chrome
- `PLAN.md` — follow-up direction/current queue wording if affected

**Check If Affected:**
- `docs/architecture/provider-abstractions.md` — update only if provider/source labels or market-data state semantics change, which this task should avoid
- `docs/architecture/analysis-engines.md` — update only if analysis user-facing states change, which this task should avoid

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Active source/rendered markup no longer includes the exact top header snippet: `atrade-terminal-app__header`, `atrade-terminal-app__brand`, `ATrade Workspace`, or `Paper Trading Workspace`
- [ ] Active source/rendered markup no longer includes the exact safety strip snippet: `terminal-safety-strip` or `data-testid="terminal-safety-strip"`
- [ ] Paper-only/no-order safety remains visible in appropriate module/help/status/disabled contexts and no order controls are introduced
- [ ] Market-monitor filters remain usable and accessible while consuming materially less vertical space; the long explanatory filter paragraph is removed or collapsed into compact copy
- [ ] Filter behavior, selected state, counts, and Clear-all behavior are unchanged

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-053): complete Step N — description`
- **Bug fixes:** `fix(TP-053): description`
- **Tests:** `test(TP-053): description`
- **Hydration:** `hydrate: TP-053 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Remove the module rail, active module/workflow navigation, HOME/SEARCH/WATCHLIST market monitor, CHART, ANALYSIS, STATUS, HELP, or visible-disabled future modules
- Remove paper-only/no-order safety from the product contract; only remove the requested global visible header and safety strip
- Hide provider-unavailable/provider-not-configured/authentication-required states or exact identity metadata
- Add fake data, direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, or LEAN
- Add real order placement, simulated order-entry UI, buy/sell buttons, order tickets, previews, confirmations, or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
