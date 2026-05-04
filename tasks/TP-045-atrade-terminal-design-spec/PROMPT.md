# Task: TP-045 - Define the ATrade Terminal UI design spec

**Created:** 2026-05-04
**Size:** S

## Review Level: 1 (Plan Only)

**Assessment:** This is an active product/design architecture document that will govern a multi-task frontend rewrite and must capture clean-room visual guardrails before implementation starts. It is documentation-only and reversible, but the downstream blast radius warrants plan review.
**Score:** 2/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 0

## Canonical Task Folder

```
tasks/TP-045-atrade-terminal-design-spec/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Create the authoritative ATrade Terminal UI design spec for a full frontend reconstruction inspired by FinceptTerminal-style modern institutional terminals and Bloomberg-like command workflows. The spec must turn the user decisions from planning into implementation-ready constraints: original clean-room UI, visually close terminal density, Next.js web-first with future desktop-wrapper compatibility, resizable multi-panel workspaces, command and module navigation, current ATrade workflows as enabled modules, visible-disabled future modules, and no order-entry/live-trading behavior.

## Dependencies

- **None**

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer and active-doc rules
- `docs/architecture/paper-trading-workspace.md` — current paper-only frontend workspace, provider, search, watchlist, chart, and analysis contracts
- `docs/architecture/modules.md` — frontend/module ownership map
- `docs/architecture/provider-abstractions.md` — provider-neutral market-data/search identity labels that terminal UI must preserve
- `README.md` — current runtime surface and verification entry-point summary

## Environment

- **Workspace:** `docs/`, `tests/apphost/`, and task metadata only
- **Services required:** None

## File Scope

- `docs/design/atrade-terminal-ui.md` (new)
- `docs/INDEX.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `tests/apphost/atrade-terminal-design-spec-tests.sh` (new)
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Create the clean-room terminal design authority

- [ ] Create `docs/design/atrade-terminal-ui.md` with frontmatter marked `status: active`, a summary, and links to the active workspace/module/provider docs
- [ ] Record the clean-room rule: use FinceptTerminal/Bloomberg only as visual and workflow inspiration; do not copy source code, assets, screenshots, trademarks, branding, or pixel-identical proprietary layouts
- [ ] Capture the selected product target: full frontend replacement, Next.js web terminal first, desktop-wrapper-friendly later, desktop/laptop primary, simplified mobile fallback
- [ ] Run targeted doc validation: `bash tests/apphost/atrade-terminal-design-spec-tests.sh`

**Artifacts:**
- `docs/design/atrade-terminal-ui.md` (new)
- `tests/apphost/atrade-terminal-design-spec-tests.sh` (new)

### Step 2: Specify modules, navigation, layout, and disabled surfaces

- [ ] Define enabled first-release modules for `HOME`, `SEARCH`, `WATCHLIST`, `CHART`, `ANALYSIS`, `STATUS`, and `HELP` using only current ATrade backend/API contracts
- [ ] Define visible-disabled future modules such as `NEWS`, `PORTFOLIO`, `RESEARCH`, `SCREENER`, `ECON`, `AI`, `NODE`, and `ORDERS`, with explicit unavailable/coming-soon states and no fake data
- [ ] Specify deterministic first-release commands: `HOME`, `SEARCH <query>`, `CHART <symbol>`, `WATCH` / `WATCHLIST`, `ANALYSIS <symbol>`, `STATUS`, and `HELP`
- [ ] Specify resizable multi-panel workspace behavior, basic local layout persistence, module rail behavior, top command/header behavior, status/ticker strip behavior, and laptop fallback rules

**Artifacts:**
- `docs/design/atrade-terminal-ui.md` (modified)

### Step 3: Specify visual system and implementation constraints

- [ ] Define Fincept-style modern institutional terminal visual characteristics: dark dense panels, high-contrast data hierarchy, compact typography, grid/table density, amber/cyan/green/red accents, rectangular/resizable paneling, and non-generic shadcn styling
- [ ] Define the selected UI stack direction: shadcn/ui-style stack with Tailwind and Radix primitives, heavily restyled through original ATrade terminal components
- [ ] Define aggressive frontend replacement rules: existing frontend rendering components/CSS are disposable; preserve backend/API contracts and reusable data/workflow logic only where it fits the terminal architecture
- [ ] Preserve safety constraints: no order-entry UI in this batch, no simulated-submit workflow, no real/live orders, no direct browser access to Postgres/TimescaleDB/Redis/NATS/IBKR/iBeam/LEAN

**Artifacts:**
- `docs/design/atrade-terminal-ui.md` (modified)

### Step 4: Wire the spec into active documentation

- [ ] Add `docs/design/atrade-terminal-ui.md` to `docs/INDEX.md` as an active design document
- [ ] Update `docs/architecture/paper-trading-workspace.md` to reference the new terminal UI spec as the current frontend reconstruction authority
- [ ] Update `docs/architecture/modules.md` if needed so frontend module responsibilities point to the terminal design spec rather than the old shell as the target state
- [ ] Update `README.md` / `PLAN.md` only if their active task queue or UI direction text is stale after the spec lands

**Artifacts:**
- `docs/INDEX.md` (modified)
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified if needed)
- `README.md` (modified if needed)
- `PLAN.md` (modified if needed)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run doc validation: `bash tests/apphost/atrade-terminal-design-spec-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run frontend build to catch doc-linked package side effects: `cd frontend && npm run build`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — new active UI design authority
- `docs/INDEX.md` — add the new active design doc
- `docs/architecture/paper-trading-workspace.md` — reference the new terminal UI spec and current reconstruction direction

**Check If Affected:**
- `docs/architecture/modules.md` — update frontend module responsibilities if the spec changes module ownership language
- `README.md` — update if the active queue or runtime-surface description becomes stale
- `PLAN.md` — update if the active queue or execution order needs adjustment

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] `docs/design/atrade-terminal-ui.md` exists, is active, and is linked from `docs/INDEX.md`
- [ ] Spec captures the exact planning decisions: Fincept-style visual target, full replacement, shadcn/Tailwind/Radix stack, resizable panels, deterministic commands, enabled current modules, visible-disabled future modules, and paper-only safety
- [ ] Spec includes clean-room visual guardrails and rejects copied source/assets/branding

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `docs(TP-045): complete Step N — description`
- **Bug fixes:** `fix(TP-045): description`
- **Tests:** `test(TP-045): description`
- **Hydration:** `hydrate: TP-045 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Copy FinceptTerminal source code, assets, screenshots, icons, or branding
- Copy Bloomberg proprietary layouts, trademarks, colors, screenshots, or branding
- Add frontend implementation code in this design-spec task
- Add real order placement, simulated order-entry UI, or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
