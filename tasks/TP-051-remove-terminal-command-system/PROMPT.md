# Task: TP-051 - Remove terminal branding and command system

**Created:** 2026-05-05
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This task changes the current frontend shell navigation model and user-facing product copy while preserving all API-backed workspace modules. It is frontend-only and reversible, but it touches multiple active workflows, test scripts, and docs.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-051-remove-terminal-command-system/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Remove the visible ATrade Terminal branding/header copy and remove the deterministic command system from the current Next.js paper workspace. The active UI should no longer show `ATrade Terminal`, `ATrade Terminal Shell`, `Command-first paper workspace · ATrade.Api boundary · provider-truthful states`, a `Command` input, command help, or a command parser/registry. Preserve the useful API-backed modules and direct workflow actions: module rail navigation, HOME/SEARCH/WATCHLIST market-monitor content, CHART and ANALYSIS handoff, STATUS/HELP surfaces, disabled future modules, provider-truthful states, `ATrade.Api` browser boundary, and no-order safety copy.

## Dependencies

- **Task:** TP-050 (current terminal cutover baseline must be complete)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — current frontend design authority that must be revised away from command-first terminal language
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
- `frontend/components/terminal/TerminalCommandInput.tsx` (delete if unused)
- `frontend/lib/terminalCommandRegistry.ts` (delete if unused)
- `frontend/types/terminal.ts`
- `frontend/components/terminal/TerminalHelpModule.tsx`
- `frontend/components/terminal/TerminalModuleRail.tsx`
- `frontend/lib/terminalModuleRegistry.ts`
- `frontend/components/terminal/index.ts`
- `frontend/app/globals.css`
- `tests/apphost/frontend-no-command-shell-tests.sh` (new)
- `tests/apphost/frontend-terminal-shell-command-tests.sh` (delete or retire)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh`
- `tests/apphost/frontend-terminal-cutover-tests.sh`
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh`
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

### Step 1: Remove the command system from active frontend source

- [ ] Remove `<TerminalCommandInput>` from `ATradeTerminalApp` and delete `TerminalCommandInput.tsx` plus `terminalCommandRegistry.ts` if no active imports remain
- [ ] Remove `TerminalCommandParseResult`, command action/result types, command feedback state, parser-driven focus behavior, command labels/help constants, and command-specific disabled-module typed behavior from active frontend source
- [ ] Preserve non-command navigation by keeping the module rail and existing market-monitor chart/analysis actions as the way users open HOME, SEARCH, WATCHLIST, CHART, ANALYSIS, STATUS, HELP, and visible-disabled modules
- [ ] Run targeted source validation: `bash tests/apphost/frontend-no-command-shell-tests.sh` once created, or an equivalent local grep before the test exists

**Artifacts:**
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/components/terminal/TerminalCommandInput.tsx` (deleted if unused)
- `frontend/lib/terminalCommandRegistry.ts` (deleted if unused)
- `frontend/types/terminal.ts` (modified)
- `frontend/components/terminal/TerminalHelpModule.tsx` (modified)

### Step 2: Remove user-facing ATrade Terminal and command-first copy

- [ ] Replace visible header/brand copy so active pages no longer render `ATrade Terminal`, `ATrade Terminal Shell`, or `Command-first paper workspace · ATrade.Api boundary · provider-truthful states`
- [ ] Update HELP, disabled-module, status/safety, route metadata, accessible labels, and CSS/test labels only where they expose command-first or terminal-shell product language to users
- [ ] Preserve user-visible safety facts: browser-visible data flows through `ATrade.Api`, provider unavailable states are honest, exact instrument identity is preserved where available, and orders remain disabled
- [ ] Run targeted source validation for removed visible copy and preserved safety copy

**Artifacts:**
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/components/terminal/TerminalHelpModule.tsx` (modified)
- `frontend/components/terminal/TerminalModuleRail.tsx` (modified if accessible/user-visible labels change)
- `frontend/lib/terminalModuleRegistry.ts` (modified if disabled/help copy changes)
- `frontend/app/globals.css` (modified if command/header styles are removed)

### Step 3: Update and add frontend validation scripts

- [ ] Create `tests/apphost/frontend-no-command-shell-tests.sh` to assert active frontend source has no command input component, no command registry/parser, no command data-testid, no command help grammar, no visible `ATrade Terminal Shell`/command-first copy, and no stale command route assertions
- [ ] Delete or retire `tests/apphost/frontend-terminal-shell-command-tests.sh`; update `README.md` and other test scripts so no active verification command expects the old command system
- [ ] Update `frontend-terminal-shell-ui-tests.sh`, `frontend-terminal-cutover-tests.sh`, and `frontend-terminal-chart-analysis-tests.sh` so they assert module-rail/workflow reachability instead of command input/command parser behavior
- [ ] Keep tests that enforce `ATrade.Api` browser boundaries, clean-room/no proprietary branding, no order entry, no secrets, disabled future modules, and chart/analysis identity handoff

**Artifacts:**
- `tests/apphost/frontend-no-command-shell-tests.sh` (new)
- `tests/apphost/frontend-terminal-shell-command-tests.sh` (deleted or retired)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (modified)
- `tests/apphost/frontend-terminal-cutover-tests.sh` (modified)
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh` (modified)

### Step 4: Update active documentation and plan state

- [ ] Update the frontend design doc so it no longer describes the current UI as command-first or requires a command grammar/input
- [ ] Update paper workspace and module docs to describe the current frontend as a direct module/workflow paper workspace instead of an ATrade Terminal command shell
- [ ] Update README verification inventory to replace the command-shell test with the new no-command validation
- [ ] Update PLAN follow-up direction so future work builds on module/workflow navigation without reintroducing a command system

**Artifacts:**
- `docs/design/atrade-terminal-ui.md` (modified)
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `README.md` (modified)
- `PLAN.md` (modified)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run no-command validation: `bash tests/apphost/frontend-no-command-shell-tests.sh`
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
- `docs/design/atrade-terminal-ui.md` — remove/update command-first terminal product requirements and visible ATrade Terminal branding direction
- `docs/architecture/paper-trading-workspace.md` — current frontend shell/navigation description without command input or command parser
- `docs/architecture/modules.md` — frontend component/workflow ownership after command registry/input removal
- `README.md` — verification entry-point list and current runtime frontend surface
- `PLAN.md` — active follow-up direction and new no-command task state

**Check If Affected:**
- `docs/architecture/provider-abstractions.md` — update only if provider/source label behavior changes, which this task should avoid
- `docs/architecture/analysis-engines.md` — update only if analysis user-facing states change, which this task should avoid

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Active UI no longer renders `ATrade Terminal`, `ATrade Terminal Shell`, `Command-first paper workspace`, a `Command` input, command grammar, or command help
- [ ] `TerminalCommandInput` and `terminalCommandRegistry` are removed from active source, or demonstrably absent from the active bundle if a file is retained temporarily for deletion in a follow-up
- [ ] HOME, SEARCH, WATCHLIST, CHART, ANALYSIS, STATUS, HELP, and disabled future module surfaces remain reachable without a command system
- [ ] Market monitor search/watchlist/trending, chart handoff, analysis handoff, provider diagnostics, disabled modules, and no-order safety remain intact
- [ ] Frontend still talks only to `ATrade.Api`

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-051): complete Step N — description`
- **Bug fixes:** `fix(TP-051): description`
- **Tests:** `test(TP-051): description`
- **Hydration:** `hydrate: TP-051 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Reintroduce a command input, command palette, natural-language router, fuzzy command parser, backend AI command route, or broker command surface under another name
- Remove the module rail or API-backed HOME/SEARCH/WATCHLIST/CHART/ANALYSIS/STATUS/HELP module behavior
- Remove the dense `TerminalMarketMonitor` module content from HOME/SEARCH/WATCHLIST; this task only removes the command system and visible terminal-shell branding
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
