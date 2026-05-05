# Task: TP-060 - Backtesting async runner and SignalR updates

**Created:** 2026-05-05
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This adds asynchronous execution, cancellation, startup recovery, SignalR streaming, and LEAN/analysis invocation behind the backtesting module. It spans multiple backend services and runtime states, but it reuses existing provider-neutral analysis and market-data seams.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-060-backtesting-async-signalr-runner/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Turn saved queued backtests from TP-059 into durable asynchronous jobs executed by an in-process API hosted service. The runner must recover cleanly after API restarts, fetch market data server-side through `IMarketDataService`, invoke the configured provider-neutral analysis/LEAN engine, persist status/result/error transitions, support best-effort cancellation for queued and running jobs, and broadcast job updates through a browser-facing SignalR hub.

## Dependencies

- **Task:** TP-059 (backtesting domain, persistence, and API must exist)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/backtesting.md` — backtesting domain/API contract from TP-059
- `docs/architecture/analysis-engines.md` — provider-neutral analysis and LEAN unavailable behavior
- `docs/architecture/provider-abstractions.md` — market-data/provider error rules
- `docs/architecture/paper-trading-workspace.md` — paper-only/no-order/browser-boundary rules
- `docs/architecture/modules.md` — module dependency direction and SignalR/API ownership
- `README.md` — verification entry points
- `PLAN.md` — active queue and dependencies

## Environment

- **Workspace:** `src/ATrade.Backtesting`, `src/ATrade.Api`, `tests/`
- **Services required:** Postgres for job state. LEAN/IBKR real runtimes are optional; automated tests must use fake market data/engines and verify safe unavailable behavior when runtimes are absent.

## File Scope

- `src/ATrade.Backtesting/*`
- `src/ATrade.Api/Program.cs`
- `src/ATrade.Api/ATrade.Api.csproj`
- `tests/ATrade.Backtesting.Tests/*`
- `tests/apphost/backtesting-runner-signalr-tests.sh` (new)
- `docs/architecture/backtesting.md`
- `docs/architecture/analysis-engines.md` (check if affected)
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

### Step 1: Add durable async job runner and restart recovery

- [ ] Add an in-process hosted service/queue coordinator that claims queued runs from Postgres, marks them `running`, and records started/finished timestamps without losing rows on API restart
- [ ] On startup, reset interrupted `running` jobs to `failed` with a safe restart/interruption message, while leaving queued jobs runnable
- [ ] Implement repository/runner concurrency safeguards so a run is not executed twice by overlapping service ticks/instances in local development
- [ ] Add tests for queued-to-running, completed, failed, restart recovery, and duplicate-claim prevention

**Artifacts:**
- `src/ATrade.Backtesting/*` (modified/new)
- `tests/ATrade.Backtesting.Tests/*` (modified/new)

### Step 2: Execute runs through market data and analysis/LEAN seams

- [ ] Build a runner pipeline that fetches candles server-side using `IMarketDataService` from the saved symbol/identity/chart range; direct browser bars remain unsupported
- [ ] Invoke `IAnalysisEngineRegistry` with the saved engine/strategy metadata and cancellation token; no fake success when LEAN/no engine is unavailable
- [ ] Map market-data failures and `analysis-engine-not-configured` / `analysis-engine-unavailable` results to failed backtest runs with persisted safe error codes/messages
- [ ] Persist completed result envelopes using the TP-059 result placeholder shape, even if TP-061 later enriches result details

**Artifacts:**
- `src/ATrade.Backtesting/*` (modified/new)
- `tests/ATrade.Backtesting.Tests/*` (modified/new)

### Step 3: Add best-effort cancellation and SignalR job updates

- [ ] Implement `POST /api/backtests/{id}/cancel` behavior for queued jobs and best-effort cancellation of currently running jobs through runner-owned cancellation tokens
- [ ] Add a browser-facing SignalR hub, for example `/hubs/backtests`, that broadcasts run-created/status/result/error/cancelled updates scoped to safe run payloads
- [ ] Ensure updates never include secrets, account identifiers, gateway URLs, LEAN workspace paths, raw process command lines, tokens, or cookies
- [ ] Add tests/source validation for hub mapping, update payload shape, cancellation transitions, and fallback-safe behavior when no clients are connected

**Artifacts:**
- `src/ATrade.Backtesting/*` (modified/new)
- `src/ATrade.Api/Program.cs` (modified)
- `tests/apphost/backtesting-runner-signalr-tests.sh` (new)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run targeted backtesting tests: `dotnet test tests/ATrade.Backtesting.Tests/ATrade.Backtesting.Tests.csproj --nologo --verbosity minimal`
- [ ] Run SignalR/runner apphost validation: `bash tests/apphost/backtesting-runner-signalr-tests.sh`
- [ ] Run existing analysis tests: `dotnet test tests/ATrade.Analysis.Tests/ATrade.Analysis.Tests.csproj --nologo --verbosity minimal`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] Update active docs with async job lifecycle, restart recovery, cancellation behavior, SignalR hub path/events, and no-fake-result provider handling
- [ ] Update README/PLAN verification inventory/current runtime surface if adding the hub/test script
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md, including any LEAN-runtime smoke skipped due local configuration

## Documentation Requirements

**Must Update:**
- `docs/architecture/backtesting.md` — async runner, statuses, cancellation, restart recovery, SignalR updates
- `docs/architecture/modules.md` — API/backtesting/SignalR responsibilities if changed
- `docs/architecture/paper-trading-workspace.md` — browser-facing backtest status streaming and no-order/no-secret guardrails
- `README.md` — runtime surface and verification entry points if affected
- `PLAN.md` — active queue/current direction if affected

**Check If Affected:**
- `docs/architecture/analysis-engines.md` — update if analysis/LEAN contracts or unavailable behavior change
- `docs/architecture/provider-abstractions.md` — update if market-data error mapping changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Queued backtests execute asynchronously in the API hosted service and survive API restart semantics as documented
- [ ] Running jobs can be cancelled best-effort; queued jobs cancel deterministically
- [ ] Completed/failed/cancelled status and result/error payloads persist in Postgres
- [ ] SignalR hub broadcasts safe backtest status/result updates
- [ ] LEAN/no-engine/unavailable states fail explicitly without fake signals, metrics, equity curves, or trades

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-060): complete Step N — description`
- **Bug fixes:** `fix(TP-060): description`
- **Tests:** `test(TP-060): description`
- **Hydration:** `hydrate: TP-060 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Add a separate worker process, NATS dispatch, optimization, export, multi-symbol portfolios, custom strategy code, or frontend UI in this task
- Add synthetic candles or fake successful backtests when market data or LEAN is unavailable
- Expose secrets, account identifiers, gateway URLs, LEAN workspace paths, process command lines, tokens, or cookies over API/SignalR/logs
- Add real order placement, broker execution, buy/sell controls, or live-trading behavior

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
