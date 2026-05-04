# Task: TP-047 - Build the terminal shell, command registry, and resizable layout

**Created:** 2026-05-04
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This is the structural frontend replacement task: routes, shell composition, module registry, command parsing, resizable layout, and layout persistence all change. It remains frontend-only and reversible, but it establishes new application patterns and touches multiple user workflows.
**Score:** 5/8 — Blast radius: 1, Pattern novelty: 2, Security: 0, Reversibility: 2

## Canonical Task Folder

```
tasks/TP-047-terminal-shell-command-layout/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Replace the current home/chart shell structure with an ATrade Terminal application frame: Fincept-style dark desktop terminal shell, first-class module rail, deterministic command input, resizable multi-panel workspace with basic persistence, status/help modules, and visible-disabled placeholders for future terminal breadth. This task creates the navigation/layout backbone that later market-monitor and chart/analysis tasks fill with final module content.

## Dependencies

- **Task:** TP-046 (terminal UI stack and primitives must be available)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — terminal shell, command, layout, module, and visual guardrails
- `docs/architecture/paper-trading-workspace.md` — frontend safety and API-boundary constraints
- `docs/architecture/modules.md` — frontend module responsibilities

## Environment

- **Workspace:** `frontend/`
- **Services required:** None

## File Scope

- `frontend/app/page.tsx`
- `frontend/app/symbols/[symbol]/page.tsx`
- `frontend/app/globals.css`
- `frontend/types/terminal.ts` (new)
- `frontend/lib/terminalCommandRegistry.ts` (new)
- `frontend/lib/terminalModuleRegistry.ts` (new)
- `frontend/lib/terminalLayoutPersistence.ts` (new)
- `frontend/components/terminal/ATradeTerminalApp.tsx` (new)
- `frontend/components/terminal/TerminalCommandInput.tsx` (new)
- `frontend/components/terminal/TerminalModuleRail.tsx` (new)
- `frontend/components/terminal/TerminalWorkspaceLayout.tsx` (new)
- `frontend/components/terminal/TerminalStatusStrip.tsx` (new)
- `frontend/components/terminal/TerminalHelpModule.tsx` (new)
- `frontend/components/terminal/TerminalStatusModule.tsx` (new)
- `frontend/components/terminal/TerminalDisabledModule.tsx` (new)
- `frontend/components/TerminalWorkspaceShell.tsx` (delete or retire if no longer used)
- `frontend/components/WorkspaceCommandBar.tsx` (delete or retire if no longer used)
- `frontend/components/WorkspaceNavigation.tsx` (delete or retire if no longer used)
- `frontend/components/WorkspaceContextPanel.tsx` (delete or retire if no longer used)
- `tests/apphost/frontend-terminal-shell-command-tests.sh` (new)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `README.md`
- `docs/architecture/modules.md`
- `docs/architecture/paper-trading-workspace.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Model terminal modules and deterministic commands

- [ ] Create terminal types and a module registry for enabled modules `HOME`, `SEARCH`, `WATCHLIST`, `CHART`, `ANALYSIS`, `STATUS`, `HELP` and visible-disabled modules `NEWS`, `PORTFOLIO`, `RESEARCH`, `SCREENER`, `ECON`, `AI`, `NODE`, `ORDERS`
- [ ] Create a deterministic command registry/parser for exactly `HOME`, `SEARCH <query>`, `CHART <symbol>`, `WATCH` / `WATCHLIST`, `ANALYSIS <symbol>`, `STATUS`, and `HELP`, returning typed navigation/module actions and clear invalid-command help
- [ ] Ensure disabled modules resolve to honest unavailable states, not mock/demo data and not order-entry controls
- [ ] Add targeted source tests/assertions in `frontend-terminal-shell-command-tests.sh` for supported commands, aliases limited to `WATCH/WATCHLIST`, disabled module copy, and no natural-language parser

**Artifacts:**
- `frontend/types/terminal.ts` (new)
- `frontend/lib/terminalCommandRegistry.ts` (new)
- `frontend/lib/terminalModuleRegistry.ts` (new)
- `frontend/components/terminal/TerminalDisabledModule.tsx` (new)
- `tests/apphost/frontend-terminal-shell-command-tests.sh` (new)

### Step 2: Build the terminal application frame and module rail

- [ ] Create `ATradeTerminalApp`, `TerminalCommandInput`, `TerminalModuleRail`, `TerminalStatusStrip`, `TerminalHelpModule`, and `TerminalStatusModule` using the terminal primitives from TP-046
- [ ] Replace `frontend/app/page.tsx` with the new terminal app entry and route the symbol page through the same terminal frame instead of the old shell/back-link composition
- [ ] Make command input and module rail both first-class navigation paths; command execution must focus/open the intended module with keyboard-friendly status feedback
- [ ] Preserve paper-only/provider safety messages in the frame and status module

**Artifacts:**
- `frontend/components/terminal/ATradeTerminalApp.tsx` (new)
- `frontend/components/terminal/TerminalCommandInput.tsx` (new)
- `frontend/components/terminal/TerminalModuleRail.tsx` (new)
- `frontend/components/terminal/TerminalStatusStrip.tsx` (new)
- `frontend/components/terminal/TerminalHelpModule.tsx` (new)
- `frontend/components/terminal/TerminalStatusModule.tsx` (new)
- `frontend/app/page.tsx` (modified)
- `frontend/app/symbols/[symbol]/page.tsx` (modified)

### Step 3: Add resizable multi-panel layout and persistence

- [ ] Create `TerminalWorkspaceLayout` with resizable primary/context/monitor regions, desktop/laptop-first layout, and simplified stacked fallback for narrow screens
- [ ] Add `terminalLayoutPersistence` for basic localStorage layout persistence with versioning, bounds checks, reset behavior, and no durable backend writes
- [ ] Add terminal CSS for splitters, dense panels, status strip, rail, command header, and responsive fallbacks in `frontend/app/globals.css`
- [ ] Ensure layout persistence is desktop-wrapper-friendly and gracefully disabled during server rendering

**Artifacts:**
- `frontend/components/terminal/TerminalWorkspaceLayout.tsx` (new)
- `frontend/lib/terminalLayoutPersistence.ts` (new)
- `frontend/app/globals.css` (modified)

### Step 4: Retire the old shell primitives from active routes

- [ ] Remove active route usage of `TerminalWorkspaceShell`, `WorkspaceCommandBar`, `WorkspaceNavigation`, and `WorkspaceContextPanel`; delete them if no longer imported or leave clearly unused only if a downstream task still needs migration time
- [ ] Update frontend tests that asserted old homepage copy such as `ATrade Frontend Home` / `Next.js Bootstrap Slice` so they assert the new ATrade Terminal shell markers
- [ ] Preserve existing API clients/workflow modules for downstream modules; do not rewire market-data/search/watchlist/charts in this shell task beyond placeholders or routing hooks
- [ ] Run targeted shell/command tests and frontend build

**Artifacts:**
- `frontend/components/TerminalWorkspaceShell.tsx` (deleted or retired)
- `frontend/components/WorkspaceCommandBar.tsx` (deleted or retired)
- `frontend/components/WorkspaceNavigation.tsx` (deleted or retired)
- `frontend/components/WorkspaceContextPanel.tsx` (deleted or retired)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (modified)
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh` (modified)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run command/shell validation: `bash tests/apphost/frontend-terminal-shell-command-tests.sh`
- [ ] Run terminal shell UI validation: `bash tests/apphost/frontend-terminal-shell-ui-tests.sh`
- [ ] Run frontend bootstrap checks: `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
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
- `docs/architecture/modules.md` — document terminal app frame, module/command registry, and layout persistence ownership
- `docs/architecture/paper-trading-workspace.md` — update current frontend shell description to the new ATrade Terminal frame and paper-only status surfaces
- `README.md` — add `tests/apphost/frontend-terminal-shell-command-tests.sh` to verification entry points once created

**Check If Affected:**
- `docs/design/atrade-terminal-ui.md` — update only if implementation requires approved command/layout refinements
- `docs/architecture/provider-abstractions.md` — update only if provider/status labels change, which this task should avoid

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Home and symbol routes render through the new ATrade Terminal frame rather than the old shell
- [ ] Command input and module rail both open/focus enabled modules
- [ ] Resizable multi-panel layout with local-only persistence exists and has reset/bounds behavior
- [ ] Disabled modules are visible with honest unavailable states and no fake data/order controls
- [ ] Frontend still talks only to `ATrade.Api`

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-047): complete Step N — description`
- **Bug fixes:** `fix(TP-047): description`
- **Tests:** `test(TP-047): description`
- **Hydration:** `hydrate: TP-047 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Add natural-language command parsing, LLM command routing, or unlisted command aliases
- Copy FinceptTerminal/Bloomberg source, assets, screenshots, branding, or pixel-identical proprietary layouts
- Add market monitor or chart final module content beyond shell placeholders/routing hooks; those are TP-048 and TP-049
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
