# Task: TP-059 - Backtesting domain, persistence, and API

**Created:** 2026-05-05
**Size:** M

## Review Level: 3 (Full)

**Assessment:** This creates a new backend module, Postgres schema, first-class API surface, and durable request/result contracts for saved backtests. It has broad backend blast radius, new patterns, and data-model changes, so it needs full review.
**Score:** 6/8 — Blast radius: 2, Pattern novelty: 2, Security: 0, Reversibility: 2

## Canonical Task Folder

```
tasks/TP-059-backtesting-domain-api/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Create the first-class `ATrade.Backtesting` backend module and REST API for saved asynchronous backtest runs. The API must create queued single-symbol runs, snapshot the initial capital from TP-058, persist request parameters/status/history in Postgres, list/get saved runs, cancel queued/running runs best-effort at the contract level, and retry failed/cancelled runs by creating a new run from the saved request snapshot. Execution may remain queued/pending until the runner lands in TP-060, but all public contracts and persistence must be real and test-covered.

## Dependencies

- **Task:** TP-058 (paper capital source must exist)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/paper-trading-workspace.md` — paper-only safety and API boundary contract
- `docs/architecture/modules.md` — module map and dependency direction
- `docs/architecture/analysis-engines.md` — existing analysis/LEAN provider seam reused by later execution tasks
- `docs/architecture/provider-abstractions.md` — provider-neutral payload and unavailable-state rules
- `README.md` — runtime surface and verification entry points
- `PLAN.md` — active queue and dependency context

## Environment

- **Workspace:** new `src/ATrade.Backtesting`, `src/ATrade.Api`, tests, active docs
- **Services required:** Postgres for saved runs/history. LEAN/IBKR real runtimes are not required in this task.

## File Scope

- `src/ATrade.Backtesting/*` (new)
- `src/ATrade.Backtesting/ATrade.Backtesting.csproj` (new)
- `src/ATrade.Api/Program.cs`
- `src/ATrade.Api/ATrade.Api.csproj`
- `tests/ATrade.Backtesting.Tests/*` (new)
- `tests/apphost/backtesting-api-contract-tests.sh` (new)
- `ATrade.slnx`
- `docs/architecture/backtesting.md` (new)
- `docs/INDEX.md`
- `docs/architecture/modules.md`
- `docs/architecture/paper-trading-workspace.md`
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Create provider-neutral backtesting contracts and validation

- [ ] Create `ATrade.Backtesting` with contracts for run IDs, statuses (`queued`, `running`, `completed`, `failed`, `cancelled`), single-symbol request payloads, strategy IDs (`sma-crossover`, `rsi-mean-reversion`, `breakout`), JSON parameter bag, chart range, cost model, slippage bps, benchmark mode, initial capital snapshot/source, and safe errors
- [ ] Implement provider-neutral validation for required symbol/identity, supported chart range, built-in strategy ID, parameter-bag shape, positive commission/slippage bounds, and single-symbol-only scope
- [ ] Use TP-058's paper-capital service during run creation; block creation with a clear validation error when no effective capital is available, and persist `initialCapital`, `currency`, and `capitalSource` on the run snapshot
- [ ] Add tests for validation, capital-source snapshotting, no direct browser bars, no custom strategy code, and no order-routing fields

**Artifacts:**
- `src/ATrade.Backtesting/*` (new)
- `tests/ATrade.Backtesting.Tests/*` (new)
- `ATrade.slnx` (modified)

### Step 2: Add Postgres persistence for saved backtest runs

- [ ] Add idempotent Postgres schema initialization under an `atrade_backtesting` schema or equivalent namespaced tables for run metadata, request JSON, status/error, result JSON placeholders, timestamps, and local user/workspace scope
- [ ] Implement repository methods for create queued run, list history, get by id, update status, cancel queued/running at contract level, and create retry run from a saved request snapshot
- [ ] Ensure saved run rows never contain credentials, raw gateway URLs, account ids, tokens, session cookies, or direct frontend-submitted candle arrays
- [ ] Add repository tests with fake/test database seams or deterministic SQL assertions consistent with existing Postgres module test patterns

**Artifacts:**
- `src/ATrade.Backtesting/*` (new/modified)
- `tests/ATrade.Backtesting.Tests/*` (new/modified)

### Step 3: Expose first-class backtest REST APIs

- [ ] Compose `AddBacktestingModule(...)` in `ATrade.Api` after Accounts/MarketData/Analysis dependencies are available
- [ ] Add `POST /api/backtests` to create a queued run and return the saved run envelope with `202 Accepted` or another documented success code
- [ ] Add `GET /api/backtests` and `GET /api/backtests/{id}` for history/status/result retrieval scoped to the local workspace
- [ ] Add `POST /api/backtests/{id}/cancel` and `POST /api/backtests/{id}/retry`; retry must create a new run rather than mutating the failed/cancelled run
- [ ] Add API projection tests for success, validation failures, missing capital, not-found, cancel/retry behavior, and redaction

**Artifacts:**
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.Api/ATrade.Api.csproj` (modified)
- `tests/apphost/backtesting-api-contract-tests.sh` (new)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run targeted backtesting tests: `dotnet test tests/ATrade.Backtesting.Tests/ATrade.Backtesting.Tests.csproj --nologo --verbosity minimal`
- [ ] Run API/apphost contract validation: `bash tests/apphost/backtesting-api-contract-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] Create active `docs/architecture/backtesting.md` describing the first-class backtesting module, saved run contract, statuses, capital-source snapshot, API endpoints, and no-order/no-custom-code rules
- [ ] Add the new doc to `docs/INDEX.md` and update module/workspace docs with the new backend surface
- [ ] Update README/PLAN runtime surface, verification list, and active queue text if affected
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/backtesting.md` — new authoritative backtesting contract
- `docs/INDEX.md` — add the new active doc
- `docs/architecture/modules.md` — add `ATrade.Backtesting` module and dependencies
- `docs/architecture/paper-trading-workspace.md` — add backtesting API/history/capital-source behavior
- `README.md` — current runtime surface and verification entry points if endpoints/tests are added
- `PLAN.md` — current plan and queued work if affected

**Check If Affected:**
- `docs/architecture/analysis-engines.md` — update only if this task changes analysis contracts
- `docs/architecture/provider-abstractions.md` — update only if provider-neutral payload rules change

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] `ATrade.Backtesting` exists, is in `ATrade.slnx`, and is composed by `ATrade.Api`
- [ ] REST endpoints exist for create/list/get/cancel/retry saved backtest runs
- [ ] Created runs snapshot effective initial capital/source from TP-058 and block when no capital is available
- [ ] Runs are single-symbol, built-in-strategy-only, server-market-data-only, and persisted without secrets/account identifiers/direct bars
- [ ] Retry creates a new run from the saved request snapshot

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-059): complete Step N — description`
- **Bug fixes:** `fix(TP-059): description`
- **Tests:** `test(TP-059): description`
- **Hydration:** `hydrate: TP-059 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Add frontend UI in this task
- Add user-auth, multi-symbol portfolios, export, optimization, custom code, direct browser bars, or synthetic market data
- Add order placement, broker execution, buy/sell controls, or live trading
- Persist or expose account identifiers, credentials, tokens, session cookies, gateway URLs, or LEAN workspace internals
- Make LEAN an API route name or frontend type assumption

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
