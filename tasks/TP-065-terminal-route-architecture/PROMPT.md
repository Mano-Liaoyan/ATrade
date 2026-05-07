# Task: TP-065 - Terminal route architecture and old symbol route removal

**Created:** 2026-05-07
**Size:** M

## Review Level: 1 (Plan Only)

**Assessment:** This task changes frontend routing and navigation state across the terminal shell, but it stays within Next.js frontend files and existing API-backed workflows. It adapts current route/query identity patterns and is reversible without data migration.
**Score:** 3/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-065-terminal-route-architecture/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Replace hash/state-only module navigation with real, deterministic Next.js routes for every enabled and visible-disabled terminal module. The accepted route contract is `/`, `/search`, `/watchlist`, `/chart`, `/chart/[symbol]`, `/analysis`, `/analysis/[symbol]`, `/backtest`, `/backtest/[symbol]`, `/status`, `/help`, and disabled routes `/news`, `/portfolio`, `/research`, `/screener`, `/econ`, `/ai`, `/node`, `/orders`. Remove the old `/symbols/[symbol]` route instead of keeping a redirect or alias.

## Dependencies

- **Task:** TP-064 (desktop browser visibility guardrails and project memory must be established first)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — active route/navigation and layout authority
- `docs/architecture/paper-trading-workspace.md` — frontend/API boundaries and paper-only rules
- `docs/architecture/modules.md` — frontend module/component ownership
- `README.md` — verification entry points
- `PLAN.md` — active queue and frontend direction

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, active docs
- **Services required:** None for source/static validation. Optional Next.js dev route checks may use `NEXT_PUBLIC_ATRADE_API_BASE_URL=http://127.0.0.1:1` and must not require real IBKR/iBeam/LEAN.

## File Scope

- `frontend/app/page.tsx`
- `frontend/app/search/page.tsx` (new)
- `frontend/app/watchlist/page.tsx` (new)
- `frontend/app/chart/page.tsx` (new)
- `frontend/app/chart/[symbol]/page.tsx` (new)
- `frontend/app/analysis/page.tsx` (new)
- `frontend/app/analysis/[symbol]/page.tsx` (new)
- `frontend/app/backtest/page.tsx` (new)
- `frontend/app/backtest/[symbol]/page.tsx` (new)
- `frontend/app/status/page.tsx` (new)
- `frontend/app/help/page.tsx` (new)
- `frontend/app/news/page.tsx` (new)
- `frontend/app/portfolio/page.tsx` (new)
- `frontend/app/research/page.tsx` (new)
- `frontend/app/screener/page.tsx` (new)
- `frontend/app/econ/page.tsx` (new)
- `frontend/app/ai/page.tsx` (new)
- `frontend/app/node/page.tsx` (new)
- `frontend/app/orders/page.tsx` (new)
- `frontend/app/symbols/[symbol]/page.tsx` (remove)
- `frontend/components/terminal/ATradeTerminalApp.tsx`
- `frontend/components/terminal/TerminalModuleRail.tsx`
- `frontend/lib/terminalModuleRegistry.ts`
- `frontend/lib/terminalMarketMonitorWorkflow.ts`
- `frontend/lib/instrumentIdentity.ts`
- `frontend/types/terminal.ts`
- `tests/apphost/frontend-terminal-route-architecture-tests.sh` (new)
- Existing frontend route/shell tests under `tests/apphost/frontend-*.sh` (check/update if affected)
- `docs/design/atrade-terminal-ui.md`
- `docs/architecture/paper-trading-workspace.md` (check/update if affected)
- `docs/architecture/modules.md` (check/update if affected)
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Add canonical route helpers and page entrypoints

- [ ] Add reusable route parsing/creation helpers or page wrappers so enabled module pages and symbol-specific pages initialize `ATradeTerminalApp` without duplicating fragile query parsing
- [ ] Create route entrypoints for `/`, `/search`, `/watchlist`, `/chart`, `/chart/[symbol]`, `/analysis`, `/analysis/[symbol]`, `/backtest`, `/backtest/[symbol]`, `/status`, and `/help`
- [ ] Create disabled-module route entrypoints for `/news`, `/portfolio`, `/research`, `/screener`, `/econ`, `/ai`, `/node`, and `/orders` that render honest visible-disabled states inside the same terminal shell
- [ ] Preserve exact identity query parsing (`provider`, `providerSymbolId`, `exchange`, `currency`, `assetClass`) and chart range parsing on symbol-specific routes

**Artifacts:**
- `frontend/app/*/page.tsx` route files (new/modified)
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- Route helper file(s) under `frontend/lib/` or `frontend/components/terminal/` (new if useful)

### Step 2: Wire rail and workflow navigation to real routes

- [ ] Update `terminalModuleRegistry` route metadata to the accepted canonical routes instead of hash anchors
- [ ] Update module rail clicks so enabled and disabled module selections push their real URLs and keep active/disabled state, focus, and status text accessible
- [ ] Update market-monitor chart/analysis/backtest hrefs and navigation intents to `/chart/[symbol]`, `/analysis/[symbol]`, and `/backtest/[symbol]` while preserving exact identity query metadata
- [ ] Keep browser back/forward behavior compatible with route-derived initial state; avoid a hidden command parser or hash-only routing fallback

**Artifacts:**
- `frontend/lib/terminalModuleRegistry.ts` (modified)
- `frontend/components/terminal/TerminalModuleRail.tsx` (modified if needed)
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/lib/terminalMarketMonitorWorkflow.ts` (modified)
- `frontend/lib/instrumentIdentity.ts` (modified)
- `frontend/types/terminal.ts` (modified if needed)

### Step 3: Remove old `/symbols/[symbol]` route without aliasing

- [ ] Delete `frontend/app/symbols/[symbol]/page.tsx` and remove tests/docs that expect `/symbols/[symbol]` to work
- [ ] Update all frontend source/tests/docs references to use `/chart/[symbol]`, `/analysis/[symbol]`, or `/backtest/[symbol]` as appropriate
- [ ] Ensure no redirect, alias, compatibility route, or route helper keeps `/symbols/[symbol]` alive

**Artifacts:**
- `frontend/app/symbols/[symbol]/page.tsx` (removed)
- Existing tests/docs/source references (modified as needed)

### Step 4: Add route architecture validation

- [ ] Create `tests/apphost/frontend-terminal-route-architecture-tests.sh` validating canonical route files, rail registry routes, workflow hrefs, disabled-module routes, exact identity query preservation, and `/symbols/[symbol]` removal
- [ ] Update existing shell/chart/backtest/search tests to expect new routes where they perform route assertions
- [ ] Ensure route validation remains provider/runtime independent and does not require real credentials

**Artifacts:**
- `tests/apphost/frontend-terminal-route-architecture-tests.sh` (new)
- Existing route-sensitive frontend tests (modified if affected)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run route architecture validation: `bash tests/apphost/frontend-terminal-route-architecture-tests.sh`
- [ ] Run terminal chart/analysis validation: `bash tests/apphost/frontend-terminal-chart-analysis-tests.sh`
- [ ] Run trading workspace validation: `bash tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Run Next.js bootstrap validation: `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] Update active docs to describe canonical enabled and disabled routes and the removal of `/symbols/[symbol]`
- [ ] Update README/PLAN verification inventory/current frontend surface if new validation scripts are added
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — canonical route scheme and disabled route behavior
- `README.md` — route/current surface and verification inventory if affected
- `PLAN.md` — active frontend route direction if affected

**Check If Affected:**
- `docs/architecture/paper-trading-workspace.md` — update only if frontend route contract section changes
- `docs/architecture/modules.md` — update only if frontend module ownership/component paths change

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Enabled module rail clicks update the URL to `/`, `/search`, `/watchlist`, `/chart`, `/analysis`, `/backtest`, `/status`, and `/help` as appropriate
- [ ] Symbol workflow actions route to `/chart/[symbol]`, `/analysis/[symbol]`, and `/backtest/[symbol]` with exact identity query metadata preserved
- [ ] Disabled rail entries route to `/news`, `/portfolio`, `/research`, `/screener`, `/econ`, `/ai`, `/node`, and `/orders` with honest unavailable states
- [ ] `/symbols/[symbol]` is removed and not redirected/aliased
- [ ] No command parser, hash-only module routing, fake data, direct provider/database access, order controls, mobile optimization scope, or secrets are introduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-065): complete Step N — description`
- **Bug fixes:** `fix(TP-065): description`
- **Tests:** `test(TP-065): description`
- **Hydration:** `hydrate: TP-065 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Keep `/symbols/[symbol]` as a redirect, alias, or compatibility route
- Reintroduce hash-only module routing as the primary route contract
- Add fake market data, direct provider/runtime/database access, backend endpoints, or new persistence
- Add order entry, buy/sell controls, broker execution, or live-trading behavior
- Expose secrets, account identifiers, gateway URLs, LEAN workspace paths, process command lines, tokens, or cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
