# Task: TP-056 - Add module rail icons and collapse behavior

**Created:** 2026-05-05
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This task changes the primary navigation component, module metadata/types, global layout CSS, and validation/docs. It is frontend-only and reversible, but it affects keyboard/focus navigation and every module rail entry, so plan and code review are warranted.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-056-module-rail-icons-collapse/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Update the module navigation rail so every enabled and visible-disabled module button has a meaningful icon that closely matches the module purpose, and make the rail collapsible to an icon-first compact state. The collapsed state must preserve accessibility, active/focus states, keyboard operation, disabled-module explanations, and the simplified full-viewport workspace contract.

## Dependencies

- **Task:** TP-055 (theme refactor provides the final visual token foundation for the rail)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — active UI authority for module rail, responsive behavior, clean-room guardrails
- `docs/architecture/paper-trading-workspace.md` — direct module/workflow navigation and safety/API boundary contract
- `docs/architecture/modules.md` — frontend module registry ownership if metadata changes
- `README.md` — current runtime surface and verification entry points
- `PLAN.md` — active queue and follow-up direction

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, and active docs
- **Services required:** None for source/build checks. Automated validation must run without live IBKR/iBeam credentials or provider data.

## File Scope

- `frontend/components/terminal/TerminalModuleRail.tsx`
- `frontend/components/terminal/ATradeTerminalApp.tsx` (check if collapse state/status belongs in parent)
- `frontend/lib/terminalModuleRegistry.ts`
- `frontend/types/terminal.ts`
- `frontend/app/globals.css`
- `frontend/components/ui/tooltip.tsx` (check/use if needed for collapsed labels)
- `tests/apphost/frontend-module-rail-icons-collapse-tests.sh` (new)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (check/update if affected)
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh` (check/update if affected)
- `docs/design/atrade-terminal-ui.md`
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

### Step 1: Add a meaningful icon contract for every module

- [ ] Add or centralize icon metadata/mapping for enabled modules: HOME → home/house, SEARCH → search/magnifier, WATCHLIST → watchlist/bookmark/star/pin, CHART → chart/candlestick/line chart, ANALYSIS → analysis/flask/activity, STATUS → status/activity/heartbeat, HELP → help/circle-question
- [ ] Add matching icon metadata/mapping for visible-disabled modules: NEWS → newspaper, PORTFOLIO → briefcase/pie, RESEARCH → file-search/book, SCREENER → sliders/filter, ECON → landmark/globe, AI → bot/sparkles, NODE → workflow/network, ORDERS → ban/shield/receipt disabled
- [ ] Use the existing `lucide-react` dependency; do not add a new icon package unless unavoidable and explicitly justified in STATUS.md discoveries
- [ ] Preserve module labels, short labels, enabled/disabled semantics, routes, and disabled explanations

**Artifacts:**
- `frontend/components/terminal/TerminalModuleRail.tsx` (modified)
- `frontend/lib/terminalModuleRegistry.ts` (modified if metadata lives there)
- `frontend/types/terminal.ts` (modified if metadata type is added)

### Step 2: Implement collapsible rail behavior accessibly

- [ ] Add a visible rail collapse/expand control with clear icon, accessible name, and `aria-expanded`/`aria-label` or equivalent state semantics
- [ ] Render icon + label in expanded mode and icon-first compact navigation in collapsed mode; collapsed labels must remain available through `title`, visually hidden text, or existing Radix tooltip primitives
- [ ] Preserve active-module and selected-disabled styling, focus visibility, keyboard activation, disabled-module click behavior, and screen-reader names in both states
- [ ] Update layout CSS so the collapsed rail narrows without reintroducing top chrome, page-level scrolling, layout persistence, command inputs, or unsafe localStorage state

**Artifacts:**
- `frontend/components/terminal/TerminalModuleRail.tsx` (modified)
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified only if parent state/status is needed)
- `frontend/app/globals.css` (modified)
- `frontend/components/ui/tooltip.tsx` (used/modified only if needed)

### Step 3: Add navigation rail validation coverage

- [ ] Create `tests/apphost/frontend-module-rail-icons-collapse-tests.sh` to validate that every enabled and visible-disabled module has an icon, icon labels are accessible, the collapse control exists, collapsed state uses a distinct data/class contract, active/disabled states remain represented, and no command/top-chrome/order-entry surfaces are reintroduced
- [ ] Update existing shell/layout validation scripts only where needed so they accept the new icon/collapse markup while preserving prior no-command, no-top-chrome, full-viewport, no-page-scroll, and no-order assertions
- [ ] Ensure validation is deterministic and provider-independent

**Artifacts:**
- `tests/apphost/frontend-module-rail-icons-collapse-tests.sh` (new)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (modified if needed)
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run new rail validation: `bash tests/apphost/frontend-module-rail-icons-collapse-tests.sh`
- [ ] Run shell validation: `bash tests/apphost/frontend-terminal-shell-ui-tests.sh`
- [ ] Run simplified layout validation: `bash tests/apphost/frontend-simplified-workspace-layout-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] Update active docs to describe rail icon semantics and collapsible behavior
- [ ] Update README/PLAN verification inventory or current frontend surface text if the new rail validation script should be listed
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md, including final icon mapping and collapse-state persistence decision

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — module rail icon/collapse behavior, accessibility expectations, and responsive behavior
- `README.md` — verification entry-point list/current frontend surface if adding the new validation script or changing rail summary
- `PLAN.md` — active/follow-up direction if affected

**Check If Affected:**
- `docs/architecture/paper-trading-workspace.md` — update only if navigation/runtime contract text changes
- `docs/architecture/modules.md` — update only if module registry/type ownership changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Every enabled and visible-disabled rail button has a clear purpose-matched icon
- [ ] The rail can collapse and expand without losing accessible labels, active/focus states, or disabled-module explanations
- [ ] Collapsed rail frees horizontal workspace width and still works at desktop/laptop widths
- [ ] No command system, top app brand header, global safety strip, layout persistence, page-level scrolling, or order-entry affordance is reintroduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-056): complete Step N — description`
- **Bug fixes:** `fix(TP-056): description`
- **Tests:** `test(TP-056): description`
- **Hydration:** `hydrate: TP-056 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Add a new icon dependency if `lucide-react` can supply the required module icons
- Hide labels from assistive technology in collapsed mode
- Make disabled modules keyboard-selectable as active workspaces
- Copy FinceptTerminal/Bloomberg assets, iconography, screenshots, source, styles, names, trademarks, or branding
- Reintroduce the removed command system, old shell/list route wrappers, context/monitor/footer chrome, top app brand header, or visible global safety strip
- Add fake market data, fake provider responses, placeholder news/research/AI content, or invented disabled-module demos
- Add direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, LEAN, or any provider runtime
- Add real order placement, simulated order-entry UI, buy/sell buttons, order tickets, previews, confirmations, or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
