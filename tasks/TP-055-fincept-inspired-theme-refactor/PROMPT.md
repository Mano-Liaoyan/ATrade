# Task: TP-055 - Fincept-inspired terminal theme refactor

**Created:** 2026-05-05
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This is a broad frontend visual refactor across global tokens, terminal primitives, charts, and validation/documentation. It is reversible and does not touch auth or data contracts, but it affects many user-visible surfaces and needs plan plus code review.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-055-fincept-inspired-theme-refactor/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Refactor the ATrade frontend visual theme into an original, Fincept-Terminal-inspired institutional finance workstation: near-black canvas, black/graphite panels, amber/orange primary emphasis, red/green market-state colors, gray separators, compact data typography, and visible but restrained focus states. The user explicitly dislikes the current color treatment; replace the cyan/blue-gradient-heavy look with a cleaner terminal palette while preserving ATrade branding, accessibility, provider-state truthfulness, and all paper-only safety constraints.

Important guardrail: the implementation may mimic the broad public finance-terminal feel, but it must be original ATrade work. Do not copy FinceptTerminal source code, stylesheets, assets, screenshots, trademarks, component structure, exact palette values, or branding text.

## Dependencies

- **None**

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — active UI authority, clean-room guardrails, layout/visual-system rules
- `docs/architecture/paper-trading-workspace.md` — paper-only safety and browser/API boundary contract
- `docs/architecture/modules.md` — frontend module ownership map if component responsibilities change
- `README.md` — current runtime surface and verification entry points
- `PLAN.md` — active frontend direction and queued-work context

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, and active docs
- **Services required:** None for source/build checks. Real IBKR/iBeam is not required and must not be used unless ignored local `.env` values are already available; automated validation must pass with unavailable API/provider states.

## File Scope

- `frontend/app/globals.css`
- `frontend/tailwind.config.ts`
- `frontend/components/CandlestickChart.tsx`
- `frontend/components/ui/button.tsx` (check if affected)
- `frontend/components/ui/badge.tsx` (check if affected)
- `frontend/components/ui/input.tsx` (check if affected)
- `frontend/components/ui/scroll-area.tsx` (check if affected)
- `frontend/components/terminal/TerminalPanel.tsx` (check if affected)
- `frontend/components/terminal/TerminalSurface.tsx` (check if affected)
- `frontend/components/terminal/TerminalSectionHeader.tsx` (check if affected)
- `frontend/components/terminal/TerminalStatusBadge.tsx` (check if affected)
- `tests/apphost/frontend-terminal-theme-refactor-tests.sh` (new)
- `tests/apphost/frontend-terminal-ui-stack-tests.sh` (check/update if affected)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (check/update if affected)
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

### Step 1: Define the original ATrade institutional terminal palette

- [ ] Inventory current `frontend/app/globals.css` theme tokens, Tailwind terminal/status colors, terminal primitive styles, and chart colors to identify cyan/blue-gradient-heavy styling that conflicts with the requested Fincept-like terminal feel
- [ ] Define an original ATrade token set for black/graphite surfaces, amber/orange emphasis, green/red market states, yellow/warning states, gray borders/dividers, off-white text, and compact typography; do not copy exact FinceptTerminal/Bloomberg palette values or names
- [ ] Fix any token/config mismatches discovered during the inventory (for example Tailwind terminal colors referenced by components but not backed by CSS variables)
- [ ] Record palette decisions and clean-room constraints in STATUS.md discoveries before applying broad changes

**Artifacts:**
- `STATUS.md` (modified discoveries)
- `frontend/app/globals.css` (read/planned)
- `frontend/tailwind.config.ts` (read/planned)
- Terminal primitive/chart files listed in File Scope (read/planned)

### Step 2: Apply the theme refactor across the workspace shell and primitives

- [ ] Update `frontend/app/globals.css` and `frontend/tailwind.config.ts` so the application canvas, module rail, workspace panels, tables, forms, badges, buttons, focus rings, chart surfaces, and status colors use the new original black/graphite/amber terminal tokens
- [ ] Reduce or remove cyan/blue dominant gradients/glows where they make the UI feel generic or visually unpleasant, while keeping accessible focus and information-state contrast
- [ ] Adjust terminal primitives (`TerminalPanel`, `TerminalSurface`, `TerminalSectionHeader`, `TerminalStatusBadge`, and shadcn-style button/badge/input/scroll-area primitives if needed) so they render as crisp rectangular dense terminal controls rather than consumer dashboard cards
- [ ] Update `CandlestickChart` colors to match the new theme while preserving readable candles, volume, SMA overlays, crosshair behavior, legend, resize behavior, and truthful empty/provider-unavailable states

**Artifacts:**
- `frontend/app/globals.css` (modified)
- `frontend/tailwind.config.ts` (modified if needed)
- `frontend/components/CandlestickChart.tsx` (modified if needed)
- Primitive/component files listed in File Scope (modified if needed)

### Step 3: Add theme validation coverage

- [ ] Create `tests/apphost/frontend-terminal-theme-refactor-tests.sh` to validate the theme contract: black/graphite canvas and panels, amber primary emphasis, red/green market-state tokens, gray dividers, token/config consistency, accessible focus states, and no Fincept/Bloomberg/proprietary brand strings or copied asset references in active frontend source
- [ ] Update existing frontend terminal validation scripts only where necessary so they expect the refactored palette without weakening no-command, no-top-chrome, no-order, chart-visibility, or API-boundary assertions
- [ ] Ensure the new validation is source/build based and does not require live IBKR/iBeam credentials or provider data

**Artifacts:**
- `tests/apphost/frontend-terminal-theme-refactor-tests.sh` (new)
- `tests/apphost/frontend-terminal-ui-stack-tests.sh` (modified if needed)
- `tests/apphost/frontend-terminal-shell-ui-tests.sh` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run new theme validation: `bash tests/apphost/frontend-terminal-theme-refactor-tests.sh`
- [ ] Run UI stack validation: `bash tests/apphost/frontend-terminal-ui-stack-tests.sh`
- [ ] Run shell validation: `bash tests/apphost/frontend-terminal-shell-ui-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] Update active docs to describe the refactored original ATrade terminal palette and the clean-room Fincept-inspired visual interpretation
- [ ] Update README/PLAN verification inventory or current frontend surface text if the new theme validation script should be listed
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md, including the final token approach and any local-provider verification skipped

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — replace/clarify visual-system direction with the new original black/graphite/amber ATrade terminal palette and clean-room guardrails
- `README.md` — verification entry-point list/current frontend surface if adding the new validation script or changing frontend visual-surface summary
- `PLAN.md` — active/follow-up direction if affected by the new theme foundation

**Check If Affected:**
- `docs/architecture/paper-trading-workspace.md` — update only if frontend workspace visual/runtime contract text changes
- `docs/architecture/modules.md` — update only if primitive/component ownership changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] The UI no longer relies on the current cyan/blue-gradient-heavy look as the dominant theme
- [ ] The application reads as an original ATrade black/graphite/amber institutional finance terminal, visibly closer to the requested Fincept-Terminal-like feel without copied third-party assets/source/styles/branding
- [ ] Tables, panels, forms, badges, focus states, and charts remain readable and accessible
- [ ] Provider-unavailable, no-engine, disabled-module, and no-order safety states remain explicit and truthful

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-055): complete Step N — description`
- **Bug fixes:** `fix(TP-055): description`
- **Tests:** `test(TP-055): description`
- **Hydration:** `hydrate: TP-055 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Copy FinceptTerminal source code, CSS, assets, screenshots, component structure, exact palette values, trademarks, branding, names, or proprietary copy
- Copy Bloomberg Terminal proprietary layouts, screenshots, trademarks, brand colors, fonts, iconography, or command taxonomies
- Reintroduce the removed command system, old shell/list route wrappers, context/monitor/footer chrome, top app brand header, or visible global safety strip
- Add fake market data, fake chart candles, placeholder news/research/AI content, or invented provider responses
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
