# Task: TP-050 - Complete terminal cutover, cleanup, and verification

**Created:** 2026-05-04
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This is the final integration/cutover task for the frontend reconstruction. It removes obsolete UI paths, aligns tests/docs with the new terminal product, verifies current workflows end-to-end, and ensures safety/clean-room constraints hold across the full UI surface.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 2

## Canonical Task Folder

```
tasks/TP-050-terminal-cutover-verification/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Finish the full ATrade Terminal frontend replacement. Remove or retire obsolete legacy UI components/CSS/tests, ensure every current user workflow lives inside the new Fincept-style terminal shell, validate visual/functional acceptance criteria, and update active documentation so the repository describes the terminal as the current frontend. This task is the quality gate for the user's acceptance target: old UI fully retired; home/chart/search/watchlist/analysis/status in the new terminal shell; resizable panels and command navigation working; unsupported modules visible-disabled; docs/tests updated.

## Dependencies

- **Task:** TP-048 (terminal market monitor must be complete)
- **Task:** TP-049 (terminal chart and analysis workspaces must be complete)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — full replacement acceptance criteria and clean-room guardrails
- `docs/architecture/paper-trading-workspace.md` — authoritative frontend/workspace behavior and safety contract
- `docs/architecture/modules.md` — module/component ownership map
- `docs/architecture/provider-abstractions.md` — provider identity/source label contracts
- `docs/architecture/analysis-engines.md` — analysis UI behavior and no-order-routing constraints
- `README.md` — runtime surface and verification entry points
- `PLAN.md` — active queue and next-step state

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, and active docs
- **Services required:** None for source/build checks; optional IBKR/iBeam/LEAN runtime checks must use ignored local `.env` and skip cleanly if unavailable

## File Scope

- `frontend/app/page.tsx`
- `frontend/app/symbols/[symbol]/page.tsx`
- `frontend/app/layout.tsx`
- `frontend/app/globals.css`
- `frontend/components/*`
- `frontend/components/terminal/*`
- `frontend/components/ui/*`
- `frontend/lib/*`
- `frontend/types/*`
- `tests/apphost/frontend-terminal-cutover-tests.sh` (new)
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `tests/apphost/frontend-terminal-ui-stack-tests.sh`
- `tests/apphost/frontend-terminal-shell-command-tests.sh`
- `tests/apphost/frontend-terminal-shell-ui-tests.sh`
- `tests/apphost/frontend-terminal-market-monitor-tests.sh`
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh`
- `tests/apphost/frontend-symbol-search-exploration-tests.sh`
- `tests/apphost/frontend-chart-range-preset-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `tests/apphost/frontend-workspace-workflow-module-tests.sh`
- `docs/design/atrade-terminal-ui.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/analysis-engines.md`
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Audit active frontend routes and legacy leftovers

- [ ] Verify home and symbol routes render only through the new ATrade Terminal app frame and no old shell/back-link/list page remains as an active user path
- [ ] Identify legacy rendering components/CSS that are no longer imported after TP-048/TP-049 and delete them; keep reusable low-level data clients, workflows, types, or chart primitives only if actively used by terminal modules
- [ ] Remove stale old copy/test markers such as `Next.js Bootstrap Slice`, `ATrade Frontend Home`, or old shell navigation labels unless retained only in archived task docs
- [ ] Add `frontend-terminal-cutover-tests.sh` assertions for no active old-shell imports, no obsolete route copy, and terminal route markers present

**Artifacts:**
- `frontend/components/*` (deleted/modified as needed)
- `frontend/app/page.tsx` (modified if needed)
- `frontend/app/symbols/[symbol]/page.tsx` (modified if needed)
- `frontend/app/globals.css` (modified)
- `tests/apphost/frontend-terminal-cutover-tests.sh` (new)

### Step 2: Verify full functional replacement behavior

- [ ] Ensure `HOME`, `SEARCH <query>`, `WATCH` / `WATCHLIST`, `CHART <symbol>`, `ANALYSIS <symbol>`, `STATUS`, and `HELP` all open/focus the correct terminal modules with deterministic behavior
- [ ] Ensure market monitor, search, watchlist pin/unpin, chart route, range controls, SignalR/HTTP fallback, analysis discovery/run states, provider diagnostics, and disabled future modules all remain reachable inside the terminal UI
- [ ] Ensure disabled `NEWS`, `PORTFOLIO`, `RESEARCH`, `SCREENER`, `ECON`, `AI`, `NODE`, and `ORDERS` modules show honest unavailable/coming-soon states with no fake data and no order controls
- [ ] Ensure resizable layout persistence has safe reset/bounds behavior and narrow screens have a usable stacked fallback

**Artifacts:**
- `frontend/components/terminal/*` (modified if gaps found)
- `frontend/lib/*` (modified if gaps found)
- `tests/apphost/frontend-terminal-cutover-tests.sh` (new/modified)

### Step 3: Enforce clean-room, safety, and browser-boundary guardrails

- [ ] Add or update source tests to assert no Fincept/Bloomberg copied assets/branding references are present in active frontend code
- [ ] Add or update source tests to assert no live-trading/order-entry UI, no simulated order ticket submit flow, and no direct browser access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, or LEAN
- [ ] Verify frontend still uses `ATrade.Api` clients for market data, watchlist, broker status, and analysis behavior
- [ ] Verify secrets/account identifiers/tokens/session cookies are not introduced in frontend config, tests, or docs

**Artifacts:**
- `tests/apphost/frontend-terminal-cutover-tests.sh` (modified)
- `tests/apphost/frontend-terminal-shell-command-tests.sh` (modified if needed)
- `tests/apphost/frontend-terminal-market-monitor-tests.sh` (modified if needed)
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh` (modified if needed)

### Step 4: Update docs, plan, and verification inventory

- [ ] Update `docs/architecture/paper-trading-workspace.md` so it describes the terminal UI as the current frontend surface, including enabled modules, disabled modules, command navigation, resizable layout, market monitor, chart/analysis workspace, provider diagnostics, and safety constraints
- [ ] Update `docs/architecture/modules.md` so frontend module/component/workflow ownership matches the terminal implementation and old shell components are no longer described as current
- [ ] Update `docs/architecture/analysis-engines.md` only if terminal analysis behavior changes user-facing engine discovery/run states
- [ ] Update `README.md` verification entry points with all new terminal tests and update `PLAN.md` to mark the terminal reconstruction queue complete/follow-up-ready

**Artifacts:**
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `docs/architecture/analysis-engines.md` (modified if needed)
- `README.md` (modified)
- `PLAN.md` (modified)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run cutover validation: `bash tests/apphost/frontend-terminal-cutover-tests.sh`
- [ ] Run all terminal frontend validations: `bash tests/apphost/frontend-terminal-ui-stack-tests.sh`, `bash tests/apphost/frontend-terminal-shell-command-tests.sh`, `bash tests/apphost/frontend-terminal-shell-ui-tests.sh`, `bash tests/apphost/frontend-terminal-market-monitor-tests.sh`, and `bash tests/apphost/frontend-terminal-chart-analysis-tests.sh`
- [ ] Run existing frontend validations: `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`, `bash tests/apphost/frontend-symbol-search-exploration-tests.sh`, `bash tests/apphost/frontend-chart-range-preset-tests.sh`, `bash tests/apphost/frontend-trading-workspace-tests.sh`, and `bash tests/apphost/frontend-workspace-workflow-module-tests.sh`
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
- `docs/architecture/paper-trading-workspace.md` — current frontend terminal behavior and safety contract
- `docs/architecture/modules.md` — frontend terminal module/component/workflow ownership
- `README.md` — verification entry-point list and current runtime frontend surface
- `PLAN.md` — active queue/completion state after terminal reconstruction

**Check If Affected:**
- `docs/design/atrade-terminal-ui.md` — update if final implementation intentionally diverges from the design spec
- `docs/architecture/analysis-engines.md` — update if terminal analysis behavior changes user-facing engine states
- `docs/architecture/provider-abstractions.md` — update only if identity/source label interpretation changes, which this task should avoid

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Old frontend shell/list/page UI is retired from active routes
- [ ] Home/chart/search/watchlist/analysis/status/help all live inside the new ATrade Terminal shell
- [ ] Command navigation and module rail both work for supported commands/modules
- [ ] Resizable panels and local layout persistence work with reset/bounds behavior
- [ ] Unsupported modules are visible-disabled with honest no-data/no-order states
- [ ] Clean-room and paper-only safety guardrails pass source tests
- [ ] Frontend still talks only to `ATrade.Api`

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-050): complete Step N — description`
- **Bug fixes:** `fix(TP-050): description`
- **Tests:** `test(TP-050): description`
- **Hydration:** `hydrate: TP-050 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Leave old UI as an active fallback route after equivalent terminal behavior exists
- Copy FinceptTerminal/Bloomberg source, assets, screenshots, branding, or pixel-identical proprietary layouts
- Add advanced charting beyond the already implemented terminal chart workspace
- Add fake news/portfolio/research/screener/economic/AI/node/order data
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
