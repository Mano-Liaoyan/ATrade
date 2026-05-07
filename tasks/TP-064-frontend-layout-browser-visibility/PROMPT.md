# Task: TP-064 - Frontend layout and browser visibility guardrails

**Created:** 2026-05-07
**Size:** M

## Review Level: 1 (Plan Only)

**Assessment:** This is a focused frontend layout/documentation hardening task across the terminal shell, module rail, scroll-owned panels, and active UI docs. It adapts existing layout/scrollbar patterns, avoids security-sensitive flows, and is reversible through CSS/component changes.
**Score:** 2/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 0

## Canonical Task Folder

```
tasks/TP-064-frontend-layout-browser-visibility/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Make the desktop terminal workspace reliably visible across latest stable Safari, Firefox, Chrome, and Edge. The user-confirmed contract is: keep the full-viewport app shell, keep page-level scrolling disabled, but ensure no content is clipped or unreachable by giving overflowing rail, workspace, table, detail, analysis, backtest, status, help, and disabled-module regions explicit internal/custom visible scroll ownership. Store this desktop browser/visibility rule in project memory so later frontend iterations preserve it.

## Dependencies

- **None**

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — active frontend UI/layout authority
- `docs/architecture/paper-trading-workspace.md` — frontend/API and paper-only guardrails
- `README.md` — verification inventory and current surface summary
- `PLAN.md` — current frontend follow-up direction
- `AGENTS.md` — repository memory and agent guardrails

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, active docs, repository guidance
- **Services required:** None for source/static validation. Optional Next.js dev checks may use `NEXT_PUBLIC_ATRADE_API_BASE_URL=http://127.0.0.1:1` and must not require real IBKR/iBeam/LEAN.

## File Scope

- `AGENTS.md`
- `tasks/CONTEXT.md`
- `docs/design/atrade-terminal-ui.md`
- `docs/architecture/paper-trading-workspace.md` (check/update if affected)
- `README.md` (check/update if verification inventory changes)
- `PLAN.md` (check/update if current frontend direction changes)
- `frontend/app/globals.css`
- `frontend/components/terminal/ATradeTerminalApp.tsx` (check if affected)
- `frontend/components/terminal/TerminalWorkspaceLayout.tsx`
- `frontend/components/terminal/TerminalModuleRail.tsx`
- `frontend/components/terminal/TerminalMarketMonitor.tsx`
- `frontend/components/terminal/MarketMonitorDetailPanel.tsx`
- `frontend/components/terminal/TerminalAnalysisWorkspace.tsx` (check if affected)
- `frontend/components/terminal/TerminalBacktestWorkspace.tsx` (check if affected)
- `frontend/components/terminal/TerminalStatusModule.tsx` (check if affected)
- `frontend/components/terminal/TerminalHelpModule.tsx` (check if affected)
- `frontend/components/terminal/TerminalDisabledModule.tsx` (check if affected)
- `frontend/components/ui/scroll-area.tsx` (check/update if custom scrollbar support needs extension)
- `tests/apphost/frontend-terminal-layout-visibility-tests.sh` (new)
- `tests/apphost/frontend-market-monitor-scrollbar-tests.sh` (check/update if affected)
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh` (check/update if affected)
- `tests/apphost/frontend-module-rail-icons-collapse-tests.sh` (check/update if affected)

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Store the desktop browser visibility rule in project memory

- [ ] Add a durable frontend guardrail to `AGENTS.md` and `tasks/CONTEXT.md`: latest stable desktop Safari, Firefox, Chrome, and Edge must behave consistently; no terminal content may be clipped or unreachable; overflowing regions must own visible internal/custom scrollbars; mobile optimization is not in scope for this batch
- [ ] Update `docs/design/atrade-terminal-ui.md` with the same contract under layout/navigation behavior, including Safari native-scrollbar caveats and the accepted use of app-owned/custom visible scrollbars
- [ ] Check README/PLAN and paper workspace docs for stale wording about scroll ownership or current frontend surface, updating only if the new guardrail changes active guidance

**Artifacts:**
- `AGENTS.md` (modified)
- `tasks/CONTEXT.md` (modified)
- `docs/design/atrade-terminal-ui.md` (modified)
- `README.md` / `PLAN.md` / `docs/architecture/paper-trading-workspace.md` (modified if affected)

### Step 2: Fix terminal shell, rail, and workspace scroll ownership

- [ ] Ensure the module rail remains fully reachable on desktop, including all enabled and visible-disabled modules such as NODE/ORDERS; the rail may scroll internally but must not clip half of a button
- [ ] Ensure the primary workspace owns vertical overflow with visible/styled scroll affordances while `html`, `body`, and the app frame keep page-level `overflow: hidden`
- [ ] Add reusable scrollbar styling/classes or data attributes as needed so Safari, Firefox, Chrome, and Edge have visible tracks/thumbs on scroll-owned regions
- [ ] Preserve the existing full-viewport, rail-first, no top chrome, no command system, no global safety strip, and no layout-persistence contracts

**Artifacts:**
- `frontend/app/globals.css` (modified)
- `frontend/components/terminal/TerminalWorkspaceLayout.tsx` (modified if needed)
- `frontend/components/terminal/TerminalModuleRail.tsx` (modified if needed)
- `frontend/components/ui/scroll-area.tsx` (modified if needed)

### Step 3: Fix module-owned panel visibility

- [ ] Ensure `MarketMonitorDetailPanel` content is fully reachable with internal scrolling or non-sticky responsive behavior; identity/action/reason content must not disappear behind viewport edges
- [ ] Ensure Analysis, Backtest, Status, Help, Chart, and disabled-module surfaces use module-owned scrolling/reflow so long content remains reachable without page scroll
- [ ] Keep market-monitor table vertical and horizontal scrollbars visible and do not regress sticky headers, exact identity columns, or action columns
- [ ] Avoid mobile-specific optimization beyond preserving existing responsive fallbacks; primary acceptance is desktop browser consistency

**Artifacts:**
- `frontend/app/globals.css` (modified)
- `frontend/components/terminal/MarketMonitorDetailPanel.tsx` (modified if needed)
- `frontend/components/terminal/TerminalMarketMonitor.tsx` (modified if needed)
- `frontend/components/terminal/TerminalAnalysisWorkspace.tsx` / `TerminalBacktestWorkspace.tsx` / `TerminalStatusModule.tsx` / `TerminalHelpModule.tsx` / `TerminalDisabledModule.tsx` (modified if needed)

### Step 4: Add layout/browser visibility validation

- [ ] Create `tests/apphost/frontend-terminal-layout-visibility-tests.sh` validating the guardrail docs, rail scroll/reachability markers, primary workspace scroll ownership, custom/visible scrollbar styling for Safari/Firefox/Chrome/Edge, and no page-level scroll regression
- [ ] Update existing market-monitor scrollbar, simplified workspace, or rail collapse tests only where shared layout changes require it
- [ ] Ensure validation is source/static or lightweight Next.js dev only and does not require real provider credentials

**Artifacts:**
- `tests/apphost/frontend-terminal-layout-visibility-tests.sh` (new)
- Existing frontend shell/scrollbar tests (modified if affected)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run layout visibility validation: `bash tests/apphost/frontend-terminal-layout-visibility-tests.sh`
- [ ] Run market-monitor scrollbar validation: `bash tests/apphost/frontend-market-monitor-scrollbar-tests.sh`
- [ ] Run simplified workspace validation: `bash tests/apphost/frontend-simplified-workspace-layout-tests.sh`
- [ ] Run rail icon/collapse validation: `bash tests/apphost/frontend-module-rail-icons-collapse-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Verification inventory updated if a new test script is added
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `AGENTS.md` — durable agent memory for desktop browser consistency and no-clipping/visible-scrollbar guardrail
- `tasks/CONTEXT.md` — Taskplane context memory for the same frontend guardrail
- `docs/design/atrade-terminal-ui.md` — authoritative UI layout/browser visibility contract
- `README.md` — add new validation script if created and update current frontend surface if wording changes
- `PLAN.md` — update follow-up direction/current frontend guardrails if wording changes

**Check If Affected:**
- `docs/architecture/paper-trading-workspace.md` — update only if frontend workspace contract wording changes beyond design doc

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Desktop latest stable Safari, Firefox, Chrome, and Edge are documented as required consistent targets
- [ ] The module rail cannot clip the NODE/disabled buttons; overflow is internally reachable
- [ ] Market monitor detail and all enabled/disabled module content remain reachable through visible internal/custom scroll affordances
- [ ] Page-level scrolling remains disabled; scroll ownership lives inside the terminal workspace/panels
- [ ] No mobile optimization scope, command system, old top chrome, layout persistence, fake data, direct provider/database access, order controls, or secrets are introduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-064): complete Step N — description`
- **Bug fixes:** `fix(TP-064): description`
- **Tests:** `test(TP-064): description`
- **Hydration:** `hydrate: TP-064 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Re-enable page-level scrolling as the solution; use internal scroll ownership instead
- Optimize or redesign the mobile experience in this batch
- Add fake market data, direct provider/runtime/database access, or new backend APIs
- Add order entry, buy/sell controls, broker execution, or live-trading behavior
- Expose secrets, account identifiers, gateway URLs, LEAN workspace paths, process command lines, tokens, or cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
