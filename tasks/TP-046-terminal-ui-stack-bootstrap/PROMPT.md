# Task: TP-046 - Bootstrap the terminal UI stack

**Created:** 2026-05-04
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This introduces the frontend styling/component foundation for the replacement UI by changing package dependencies, Tailwind/shadcn configuration, global CSS tokens, and shared UI primitives. It is contained to `frontend/` and tests, with no auth or durable data changes, but adds new patterns that downstream tasks depend on.
**Score:** 4/8 — Blast radius: 1, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-046-terminal-ui-stack-bootstrap/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Bootstrap a shadcn/ui-style frontend foundation for the ATrade Terminal reconstruction. Add Tailwind/Radix-compatible configuration, terminal-specific design tokens, and original ATrade UI primitives so later tasks can build a Fincept-inspired dense terminal without copying Fincept/Bloomberg assets or defaulting to a generic SaaS look.

## Dependencies

- **Task:** TP-045 (ATrade Terminal UI design spec must define the visual and implementation constraints)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — terminal visual system, module, command, layout, and clean-room guardrails
- `docs/architecture/paper-trading-workspace.md` — frontend safety and API-boundary constraints
- `docs/architecture/modules.md` — frontend module ownership and rendering/workflow boundaries

## Environment

- **Workspace:** `frontend/`
- **Services required:** None

## File Scope

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/tailwind.config.ts` (new if required by the selected Tailwind/shadcn setup)
- `frontend/postcss.config.mjs` (new or modified)
- `frontend/components.json` (new)
- `frontend/lib/utils.ts` (new)
- `frontend/app/globals.css`
- `frontend/components/ui/*` (new)
- `frontend/components/terminal/*` (new foundation components only)
- `tests/apphost/frontend-terminal-ui-stack-tests.sh` (new)
- `README.md`
- `docs/architecture/modules.md`
- `docs/architecture/paper-trading-workspace.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Add Tailwind/shadcn-compatible configuration

- [ ] Add Tailwind, PostCSS, shadcn-style helper dependencies, and Radix primitives needed for initial terminal controls using versions compatible with the current Next.js/React stack
- [ ] Create or update `tailwind.config.ts`, `postcss.config.mjs`, `components.json`, and `frontend/lib/utils.ts` using repository-local aliases and no copied external project assets
- [ ] Ensure `npm run build` succeeds after dependency/config changes and `package-lock.json` is updated deterministically
- [ ] Run targeted frontend stack validation: `bash tests/apphost/frontend-terminal-ui-stack-tests.sh`

**Artifacts:**
- `frontend/package.json` (modified)
- `frontend/package-lock.json` (modified)
- `frontend/tailwind.config.ts` (new if required)
- `frontend/postcss.config.mjs` (new or modified)
- `frontend/components.json` (new)
- `frontend/lib/utils.ts` (new)
- `tests/apphost/frontend-terminal-ui-stack-tests.sh` (new)

### Step 2: Establish terminal design tokens and base CSS

- [ ] Replace/reshape `frontend/app/globals.css` around terminal variables for dense dark surfaces, foreground/muted text, amber/cyan/green/red accents, grid lines, focus rings, splitters, tables, and status states
- [ ] Add Tailwind layer definitions or CSS variables that make shadcn-style components inherit the ATrade Terminal theme rather than generic shadcn defaults
- [ ] Preserve global accessibility basics: focus-visible states, color contrast intent, reduced-motion friendliness, and desktop/laptop-first responsive breakpoints
- [ ] Keep body/app shell styling web-first and desktop-wrapper-friendly without assuming direct Electron/Tauri APIs

**Artifacts:**
- `frontend/app/globals.css` (modified)

### Step 3: Create original terminal primitive components

- [ ] Add minimal shadcn-style UI primitives under `frontend/components/ui/` needed by the next tasks, such as button, input, tabs, dialog/sheet or popover, scroll area, separator, tooltip, and badge/status primitives
- [ ] Add original ATrade terminal foundation components under `frontend/components/terminal/` such as `TerminalPanel`, `TerminalSurface`, `TerminalSectionHeader`, and `TerminalStatusBadge`
- [ ] Ensure primitives are unopinionated enough for module tasks and do not encode current legacy shell layout assumptions
- [ ] Add source assertions that primitives exist, use local utilities, and do not reference Fincept/Bloomberg copied assets or branding

**Artifacts:**
- `frontend/components/ui/*` (new)
- `frontend/components/terminal/*` (new)
- `tests/apphost/frontend-terminal-ui-stack-tests.sh` (new)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run frontend stack validation: `bash tests/apphost/frontend-terminal-ui-stack-tests.sh`
- [ ] Run frontend checks: `cd frontend && npm run build`
- [ ] Run existing frontend shell checks: `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/modules.md` — record the new frontend UI-stack foundation and primitive/component boundaries
- `README.md` — add `tests/apphost/frontend-terminal-ui-stack-tests.sh` to verification entry points once created

**Check If Affected:**
- `docs/design/atrade-terminal-ui.md` — update only if the implementation requires an approved stack adjustment
- `docs/architecture/paper-trading-workspace.md` — update only if frontend shell/runtime boundaries change

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Tailwind/shadcn-style configuration is present and compatible with `npm run build`
- [ ] ATrade terminal tokens and primitive components exist for downstream shell/module tasks
- [ ] UI foundation is original ATrade code and does not copy Fincept/Bloomberg source, assets, branding, or pixel-identical proprietary styling

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-046): complete Step N — description`
- **Bug fixes:** `fix(TP-046): description`
- **Tests:** `test(TP-046): description`
- **Hydration:** `hydrate: TP-046 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Copy or vendor FinceptTerminal code/assets/screenshots/icons/branding
- Copy Bloomberg proprietary layouts/assets/trademarks/branding
- Build a generic shadcn SaaS UI; primitives must be restyled for ATrade Terminal
- Rewrite app routes or module behavior in this stack-bootstrap task
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
