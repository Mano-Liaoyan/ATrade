# Task: TP-072 - Exact Instrument Identity provider-neutral key deepening

**Created:** 2026-05-10
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This task deepens a cross-module domain seam used by market data, watchlists, chart/analysis/backtest route handoff, frontend optimistic UI, and saved backtest history. It changes canonical identity/key semantics while preserving legacy `ibkrConid`-bearing inputs as compatibility-only data, so it needs focused contract tests and careful documentation.
**Score:** 5/8 - Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 2

## Canonical Task Folder

```
tasks/TP-072-exact-instrument-identity-deepening/
├── PROMPT.md   <- This file (immutable above --- divider)
├── STATUS.md   <- Execution state (worker updates this)
├── .reviews/   <- Reviewer output (created by the orchestrator runtime)
└── .DONE       <- Created when complete
```

## Mission

Deepen the Exact Instrument Identity module so canonical ATrade identity handoff and persisted keys are provider-neutral. Canonical route/query handoff, frontend provisional keys, backend `instrumentKey` / `pinKey` values, watchlist persistence, and saved backtest run identity must use only the provider-neutral tuple: `provider`, `providerSymbolId`, `symbol`, `exchange`, `currency`, and `assetClass`.

IBKR `conid` values are IBKR-specific provider metadata and aliases for the IBKR provider symbol id. New canonical keys must not emit an `ibkrConid` segment. Legacy `ibkrConid`-bearing keys may be accepted only to normalize forward into the provider-neutral key shape.

## Dependencies

- **None** - can start immediately.

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` - documentation discovery layer
- `docs/architecture/provider-abstractions.md` - provider-neutral broker/market-data contract
- `docs/architecture/modules.md` - module map and Exact Instrument Identity/watchlist/backtest wording
- `docs/architecture/backtesting.md` - saved backtest run identity/history contract
- `docs/architecture/paper-trading-workspace.md` - frontend/backend paper workspace guardrails
- `src/ATrade.MarketData/ExactInstrumentIdentity.cs` - current identity normalization/key implementation
- `src/ATrade.MarketData/MarketDataProviderModels.cs` - provider-neutral market-data identity records
- `src/ATrade.Workspaces/*Watchlist*` - watchlist intake, key, persistence, SQL
- `src/ATrade.Backtesting/*` - saved run contracts, validation, persistence, execution
- `src/ATrade.Api/Program.cs` - route adapters for market data, backtests, and watchlists
- `frontend/lib/instrumentIdentity.ts` - frontend provisional identity/key helpers
- `frontend/lib/*Workflow.ts` and `frontend/types/*` identity consumers

## Environment

- **Workspace:** Exact Instrument Identity, Workspaces watchlist, Backtesting saved runs, API route adapters, frontend identity handoff, active docs
- **Services required:** Source/unit/static tests only. Real IBKR/iBeam, LEAN, Postgres, and TimescaleDB runtime services are not required; runtime scripts must skip clearly when optional infrastructure is unavailable.

## File Scope

- `src/ATrade.MarketData/ExactInstrumentIdentity.cs`
- `src/ATrade.MarketData/MarketDataProviderModels.cs`
- `src/ATrade.Workspaces/WorkspaceWatchlistInstrumentKey.cs`
- `src/ATrade.Workspaces/WorkspaceWatchlistNormalizer.cs`
- `src/ATrade.Workspaces/PostgresWorkspaceWatchlistRepository.cs`
- `src/ATrade.Workspaces/PostgresWorkspaceWatchlistSql.cs`
- `src/ATrade.Backtesting/BacktestingContracts.cs`
- `src/ATrade.Backtesting/BacktestRequestValidation.cs`
- `src/ATrade.Backtesting/BacktestRunRepository.cs`
- `src/ATrade.Backtesting/PostgresBacktestRunSql.cs`
- `src/ATrade.Api/Program.cs`
- `frontend/lib/instrumentIdentity.ts`
- `frontend/lib/marketDataClient.ts`
- `frontend/lib/watchlistClient.ts`
- `frontend/lib/watchlistWorkflow.ts`
- `frontend/lib/terminalMarketMonitorWorkflow.ts`
- `frontend/lib/terminalBacktestWorkflow.ts`
- `frontend/types/marketData.ts`
- `frontend/types/backtesting.ts`
- `tests/ATrade.ProviderAbstractions.Tests/ExactInstrumentIdentityContractTests.cs`
- `tests/ATrade.Workspaces.Tests/WorkspaceWatchlistIntakeTests.cs`
- `tests/ATrade.Backtesting.Tests/*`
- `tests/apphost/*frontend*` identity/route/watchlist/backtest contract tests, if affected
- `docs/architecture/provider-abstractions.md`
- `docs/architecture/modules.md`
- `docs/architecture/backtesting.md`
- `docs/architecture/paper-trading-workspace.md` (check/update if affected)
- `tasks/CONTEXT.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Current Exact Instrument Identity decisions in `tasks/CONTEXT.md` understood

### Step 1: Pin provider-neutral identity/key contract tests first

- [ ] Add/update backend contract tests proving canonical `instrumentKey` output excludes `ibkrConid` and derives only from provider, provider symbol id, symbol, exchange, currency, and asset class
- [ ] Add/update compatibility tests proving legacy `ibkrConid`-bearing keys are accepted only to normalize to the provider-neutral key shape
- [ ] Add/update frontend identity tests or existing apphost/source checks so provisional keys match provider-neutral canonical shape without emitting `ibkrConid`
- [ ] Add/update saved backtest tests proving saved runs persist/display the full provider-neutral Exact Instrument Identity tuple

**Artifacts:**
- `tests/ATrade.ProviderAbstractions.Tests/ExactInstrumentIdentityContractTests.cs` (modified)
- `tests/ATrade.Workspaces.Tests/WorkspaceWatchlistIntakeTests.cs` (modified if affected)
- `tests/ATrade.Backtesting.Tests/*` (modified if affected)
- Frontend/apphost identity contract tests (modified if affected)

### Step 2: Deepen backend Exact Instrument Identity implementation

- [ ] Make the canonical Exact Instrument Identity key implementation provider-neutral and remove `ibkrConid` from new key emission
- [ ] Keep IBKR `conid` alias handling inside the implementation or IBKR adapter path, not as a provider-neutral identity dimension
- [ ] Provide a single runtime implementation path for canonical key construction; runtime SQL/repository code must not manually rebuild canonical key strings
- [ ] Preserve legacy input normalization for existing `ibkrConid`-bearing keys without creating new canonical `ibkrConid` segments

**Artifacts:**
- `src/ATrade.MarketData/ExactInstrumentIdentity.cs` (modified)
- `src/ATrade.MarketData/MarketDataProviderModels.cs` (modified if needed)
- `src/ATrade.Workspaces/*` (modified if needed)

### Step 3: Update adapters and persistence consumers

- [ ] Keep route/query parsing in API/frontend adapters; translate request shape into the provider-neutral identity tuple before crossing the Exact Instrument Identity module seam
- [ ] Update market-data candle/indicator route adapters to stop treating `ibkrConid` as canonical handoff
- [ ] Update watchlist persistence and any legacy repair/backfill paths so runtime key construction goes through Exact Instrument Identity
- [ ] Update saved backtest request, persistence, history, and retry behavior so runs carry the full provider-neutral tuple

**Artifacts:**
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.Workspaces/*` (modified)
- `src/ATrade.Backtesting/*` (modified)

### Step 4: Update frontend identity handoff

- [ ] Update frontend provisional key creation to use provider-neutral tuple only
- [ ] Update chart/analysis/backtest/watchlist navigation/query helpers so canonical handoff uses `provider`, `providerSymbolId`, `symbol`, `exchange`, `currency`, and `assetClass`
- [ ] Remove or isolate `ibkrConid` from public frontend route/query/key behavior; it may remain only as an IBKR-specific adapter alias when converting provider data
- [ ] Preserve backend-returned `instrumentKey` / `pinKey` authority over optimistic client state

**Artifacts:**
- `frontend/lib/instrumentIdentity.ts` (modified)
- `frontend/lib/marketDataClient.ts` (modified if affected)
- `frontend/lib/watchlistClient.ts` (modified if affected)
- `frontend/lib/*Workflow.ts` (modified if affected)
- `frontend/types/*` (modified if affected)

### Step 5: Documentation and durable memory update

- [ ] Update active architecture docs so Exact Instrument Identity is described as provider-neutral and `ibkrConid` is IBKR-specific provider metadata only
- [ ] Update saved backtest docs to state runs persist/display the full provider-neutral tuple
- [ ] Update watchlist docs to state canonical `instrumentKey` / `pinKey` values exclude `ibkrConid`
- [ ] Update `tasks/CONTEXT.md` with discoveries, next task state, and any deferred follow-up work

**Artifacts:**
- `docs/architecture/provider-abstractions.md` (modified)
- `docs/architecture/modules.md` (modified)
- `docs/architecture/backtesting.md` (modified)
- `docs/architecture/paper-trading-workspace.md` (modified if affected)
- `tasks/CONTEXT.md` (modified)

### Step 6: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run Exact Instrument Identity contract tests: `dotnet test tests/ATrade.ProviderAbstractions.Tests/ATrade.ProviderAbstractions.Tests.csproj --nologo --verbosity minimal`
- [ ] Run Workspaces watchlist tests: `dotnet test tests/ATrade.Workspaces.Tests/ATrade.Workspaces.Tests.csproj --nologo --verbosity minimal`
- [ ] Run Backtesting tests: `dotnet test tests/ATrade.Backtesting.Tests/ATrade.Backtesting.Tests.csproj --nologo --verbosity minimal`
- [ ] Run affected frontend/apphost route/watchlist/backtest identity contract tests
- [ ] Run frontend build if frontend identity code changes: `cd frontend && npm run build`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 7: Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/provider-abstractions.md` - provider-neutral identity/key semantics and IBKR `conid` alias stance
- `docs/architecture/modules.md` - module map and Exact Instrument Identity/watchlist/backtest wording
- `docs/architecture/backtesting.md` - saved run full identity tuple behavior
- `tasks/CONTEXT.md` - durable Taskplane memory and next task state

**Check If Affected:**
- `docs/architecture/paper-trading-workspace.md` - frontend route/query/watchlist identity wording
- `README.md` / `PLAN.md` - update only if public runtime/current-surface wording becomes stale
- `docs/INDEX.md` - update only if a new doc/ADR is added

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Canonical `instrumentKey` / `pinKey` emission uses only the provider-neutral identity tuple
- [ ] New canonical keys do not include an `ibkrConid` segment
- [ ] Legacy `ibkrConid`-bearing keys normalize forward without becoming the canonical shape
- [ ] Route/query parsing remains an adapter concern and canonical handoff uses provider-neutral fields
- [ ] Frontend provisional keys use provider-neutral fields only and remain non-authoritative
- [ ] Saved backtest runs persist and display full provider-neutral Exact Instrument Identity
- [ ] Runtime repositories/SQL do not manually reconstruct canonical keys except for unavoidable one-off legacy repair

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-072): complete Step N - description`
- **Bug fixes:** `fix(TP-072): description`
- **Tests:** `test(TP-072): description`
- **Hydration:** `hydrate: TP-072 expand Step N checkboxes`

## Do NOT

- Expand task scope - add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Treat `ibkrConid` as a separate provider-neutral identity dimension
- Emit new canonical `instrumentKey` / `pinKey` values with an `ibkrConid` segment
- Add direct frontend database/provider access
- Add live-trading behavior, order placement, or broker order-routing fields
- Commit real broker credentials, account identifiers, tokens, cookies, gateway session data, or local secret values

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N - YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
