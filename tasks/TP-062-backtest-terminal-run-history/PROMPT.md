# Task: TP-062 - Terminal backtest run, history, retry, and status streaming

**Created:** 2026-05-05
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This adds a new enabled frontend module, API client/workflow state, SignalR status streaming, local paper-capital settings UI, and run/history/retry screens. It is frontend-heavy with backend API integration and must preserve no-order/no-secret/browser-boundary guardrails.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 1, Security: 1, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-062-backtest-terminal-run-history/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Add the first user-facing Backtest terminal module. The module must let a user choose a single symbol/instrument, review/set effective paper capital, select one of the built-in strategies with editable basic parameters, create an async backtest, receive live status through SignalR, view run history/detail, cancel queued/running jobs best-effort, and retry failed/cancelled runs by creating a new saved run. It must use the first-class `/api/backtests` and `/hubs/backtests` contracts and must not expose order entry, fake results, direct provider/runtime access, or secrets.

## Dependencies

- **Task:** TP-055 (theme foundation should land before new frontend module styling)
- **Task:** TP-056 (rail icon/collapse changes should land before adding the BACKTEST rail module)
- **Task:** TP-057 (market-monitor scrollbar/layout updates should land before adding adjacent module UI)
- **Task:** TP-061 (rich backtesting strategy/result backend must exist)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/design/atrade-terminal-ui.md` — active terminal UI/module design authority
- `docs/architecture/backtesting.md` — backtesting API, SignalR, strategy, status, and result contracts
- `docs/architecture/paper-trading-workspace.md` — frontend/backend separation and no-order safety
- `docs/architecture/modules.md` — frontend module/workflow ownership map
- `docs/architecture/analysis-engines.md` — no-engine/unavailable behavior and LEAN boundary
- `README.md` — frontend/runtime verification entry points
- `PLAN.md` — active frontend direction and queued dependency context

## Environment

- **Workspace:** `frontend/`, `tests/apphost/`, active docs
- **Services required:** None for source/build checks. Live SignalR/API behavior may be tested with local fake/apphost fixtures; real IBKR/iBeam/LEAN should skip cleanly unless ignored `.env` is configured.

## File Scope

- `frontend/types/terminal.ts`
- `frontend/types/backtesting.ts` (new)
- `frontend/types/analysis.ts` (check if affected)
- `frontend/lib/terminalModuleRegistry.ts`
- `frontend/lib/backtestClient.ts` (new)
- `frontend/lib/terminalBacktestWorkflow.ts` (new)
- `frontend/lib/instrumentIdentity.ts` (check if affected)
- `frontend/components/terminal/ATradeTerminalApp.tsx`
- `frontend/components/terminal/TerminalModuleRail.tsx` (check if affected)
- `frontend/components/terminal/TerminalBacktestWorkspace.tsx` (new)
- `frontend/components/terminal/TerminalDisabledModule.tsx` (check if affected)
- `frontend/app/globals.css`
- `tests/apphost/frontend-terminal-backtest-workspace-tests.sh` (new)
- `tests/apphost/frontend-terminal-cutover-tests.sh` (check/update if affected)
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh` (check/update if affected)
- `docs/design/atrade-terminal-ui.md`
- `docs/architecture/backtesting.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Add BACKTEST module registration and typed client/workflow contracts

- [ ] Add an enabled `BACKTEST` terminal module to `frontend/types/terminal.ts` and `frontend/lib/terminalModuleRegistry.ts` without reintroducing command input or old shell/list wrappers
- [ ] Create `frontend/types/backtesting.ts` matching the backend backtesting run, status, strategy definition/parameter, capital, result, and error payloads
- [ ] Create `frontend/lib/backtestClient.ts` for `GET/PUT /api/accounts/*paper-capital*`, `POST/GET /api/backtests`, cancel, retry, and `/hubs/backtests` SignalR connection setup through `ATrade.Api` only
- [ ] Create `frontend/lib/terminalBacktestWorkflow.ts` to coordinate capital loading/updating, strategy defaults/validation state, create/cancel/retry actions, history/detail loading, and SignalR status updates with safe HTTP fallback only for initial load/reconnect

**Artifacts:**
- `frontend/types/terminal.ts` (modified)
- `frontend/types/backtesting.ts` (new)
- `frontend/lib/terminalModuleRegistry.ts` (modified)
- `frontend/lib/backtestClient.ts` (new)
- `frontend/lib/terminalBacktestWorkflow.ts` (new)

### Step 2: Build the Backtest workspace form, capital panel, and live status UI

- [ ] Create `TerminalBacktestWorkspace` with a single-symbol run form, exact identity display when opened from monitor/chart state, chart range selection, strategy selector for SMA/RSI/breakout, editable basic parameter fields, commission/slippage inputs, and create-run action
- [ ] Add a paper-capital panel that shows effective capital/source, blocks run creation when capital is unavailable, and lets the user set local paper capital through `PUT /api/accounts/local-paper-capital` without exposing IBKR account identifiers
- [ ] Render queued/running/completed/failed/cancelled status with SignalR-driven updates, cancel action, retry action, explicit no-engine/provider-unavailable errors, and no fake result placeholders
- [ ] Wire `ATradeTerminalApp` so BACKTEST can open from the rail and from exact instrument chart/market-monitor handoff state while preserving existing SEARCH/WATCHLIST/CHART/ANALYSIS behavior

**Artifacts:**
- `frontend/components/terminal/TerminalBacktestWorkspace.tsx` (new)
- `frontend/components/terminal/ATradeTerminalApp.tsx` (modified)
- `frontend/components/terminal/TerminalModuleRail.tsx` (modified if needed)
- `frontend/app/globals.css` (modified)

### Step 3: Add run history, detail, cancel, and retry views

- [ ] Render saved run history from `GET /api/backtests` with statuses, symbol, strategy, range, capital source, created/finished times, summary/error preview, and selected-run detail
- [ ] Render run detail for completed results with summary metrics, benchmark summary, simulated trades/signals list, and source metadata sufficient for TP-063 comparison work
- [ ] Add cancel and retry controls that call backend endpoints; retry must show the newly created run rather than mutating the failed/cancelled run
- [ ] Keep empty/unavailable states honest: no demo runs, fixture strategies, fake equity curves, or synthetic trades

**Artifacts:**
- `frontend/components/terminal/TerminalBacktestWorkspace.tsx` (modified)
- `frontend/lib/terminalBacktestWorkflow.ts` (modified)
- `frontend/lib/backtestClient.ts` (modified)

### Step 4: Add frontend validation coverage

- [ ] Create `tests/apphost/frontend-terminal-backtest-workspace-tests.sh` validating BACKTEST rail registration, API/hub paths, capital panel, strategy form fields, history/retry/cancel strings, SignalR status handling, no-order controls, and no direct provider/runtime/database access from frontend source
- [ ] Update existing terminal cutover/chart-analysis tests only where required so the new module does not weaken no-command, no-top-chrome, no-order, provider-boundary, or chart/analysis assertions
- [ ] Ensure validation is source/build based and does not require real IBKR/iBeam/LEAN credentials

**Artifacts:**
- `tests/apphost/frontend-terminal-backtest-workspace-tests.sh` (new)
- `tests/apphost/frontend-terminal-cutover-tests.sh` (modified if needed)
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh` (modified if needed)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run backtest workspace validation: `bash tests/apphost/frontend-terminal-backtest-workspace-tests.sh`
- [ ] Run terminal cutover validation: `bash tests/apphost/frontend-terminal-cutover-tests.sh`
- [ ] Run chart/analysis validation: `bash tests/apphost/frontend-terminal-chart-analysis-tests.sh`
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] Update active UI/docs with BACKTEST module, capital panel, strategy form, SignalR status behavior, history/retry/cancel, and no-order/no-fake-result states
- [ ] Update README/PLAN verification inventory/current frontend surface if affected
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/design/atrade-terminal-ui.md` — add BACKTEST enabled module and UI behavior
- `docs/architecture/backtesting.md` — frontend client/workflow, SignalR usage, capital panel, history/retry/cancel behavior
- `docs/architecture/paper-trading-workspace.md` — frontend backtesting surface and browser/API boundary
- `docs/architecture/modules.md` — frontend module/workflow/component ownership for backtesting
- `README.md` — current frontend/runtime surface and verification entry points if affected
- `PLAN.md` — active/follow-up direction if affected

**Check If Affected:**
- `docs/architecture/analysis-engines.md` — update only if analysis/LEAN frontend contract text changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] BACKTEST is an enabled rail module and renders a full run/history/retry/status workspace
- [ ] Users can view/set local paper capital, see IBKR/local/unavailable capital source, and cannot create a run when no capital is available
- [ ] Users can create single-symbol built-in strategy runs, receive SignalR status updates, view saved history/detail, cancel queued/running jobs best-effort, and retry failed/cancelled runs
- [ ] Frontend uses only `ATrade.Api` HTTP/SignalR clients; no direct Postgres/TimescaleDB/Redis/NATS/IBKR/iBeam/LEAN/runtime access
- [ ] No order tickets, buy/sell buttons, broker routing, fake results, demo runs, synthetic bars, or secrets/account identifiers are introduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-062): complete Step N — description`
- **Bug fixes:** `fix(TP-062): description`
- **Tests:** `test(TP-062): description`
- **Hydration:** `hydrate: TP-062 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Reintroduce command input/parser, old shell/list wrappers, app-level header, global safety strip, context/monitor/footer chrome, page-level scrolling, or fake disabled-module content
- Add comparison/equity overlay selection UI beyond detail fields needed by TP-063
- Add export, optimization, custom strategy code, multi-symbol portfolio backtests, synthetic data, direct browser bars, or fake completed runs
- Add order entry, broker execution, buy/sell controls, previews, confirmations, or live-trading behavior
- Expose secrets, account identifiers, gateway URLs, LEAN workspace paths, process command lines, tokens, or cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
