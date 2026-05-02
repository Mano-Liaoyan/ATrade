# Task: TP-038 - Deepen the async market-data read module

**Created:** 2026-05-02
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This task changes the central market-data read interface used by HTTP routes, SignalR, analysis intake, Timescale cache-aside, and the IBKR adapter. It should preserve browser-facing payloads while moving network/storage work to async end-to-end.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-038-async-market-data-read-module/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Deepen the market-data read module so callers use one async interface for trending, search, symbol lookup, candles, indicators, and latest updates. This matters because the current interface is shallow: callers must understand synchronous `Try*` methods, thrown unavailable exceptions, provider status checks, cache-aside ordering, and sync-over-async implementation details.

## Dependencies

- **Task:** TP-037 (Exact Instrument Identity must exist before reshaping the market-data read interface)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/provider-abstractions.md` — market-data provider seam rules
- `docs/architecture/modules.md` — MarketData, Timescale, Analysis, frontend module map
- `docs/architecture/paper-trading-workspace.md` — paper workspace market-data behavior

## Environment

- **Workspace:** `src/ATrade.MarketData`, `src/ATrade.MarketData.Ibkr`, `src/ATrade.MarketData.Timescale`, `src/ATrade.Api`
- **Services required:** None for unit tests; provider/runtime scripts must skip cleanly when IBKR/iBeam is unavailable

## File Scope

- `src/ATrade.MarketData/MarketDataProviderContracts.cs`
- `src/ATrade.MarketData/MarketDataModels.cs`
- `src/ATrade.MarketData/MarketDataService.cs`
- `src/ATrade.MarketData/MarketDataStreamingService.cs`
- `src/ATrade.MarketData/MarketDataHub.cs`
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs`
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs`
- `src/ATrade.MarketData.Timescale/TimescaleCachedMarketDataService.cs`
- `src/ATrade.MarketData.Timescale/*`
- `src/ATrade.Api/Program.cs`
- `src/ATrade.Analysis*/*`
- `tests/ATrade.ProviderAbstractions.Tests/AsyncMarketDataReadModuleTests.cs` (new)
- `tests/ATrade.MarketData.Ibkr.Tests/*`
- `tests/ATrade.MarketData.Timescale.Tests/*`
- `tests/apphost/market-data*`
- `tests/apphost/provider-abstraction-contract-tests.sh`
- `docs/architecture/*`

## Steps

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Define one async read-result interface

- [ ] Add or reshape the market-data read interface so callers receive one consistent result/error shape with cancellation support
- [ ] Preserve current browser-facing HTTP payloads and status codes while hiding provider status checks and cache-aside ordering behind the seam
- [ ] Add `tests/ATrade.ProviderAbstractions.Tests/AsyncMarketDataReadModuleTests.cs` or equivalent new test file for success, unavailable, invalid request, and cancellation behavior
- [ ] Run targeted provider-abstraction tests

**Artifacts:**
- `src/ATrade.MarketData/*` (modified/new)
- `tests/ATrade.ProviderAbstractions.Tests/AsyncMarketDataReadModuleTests.cs` (new)

### Step 2: Convert Timescale cache-aside and IBKR provider adapters

- [ ] Remove sync-over-async (`GetAwaiter().GetResult()`, `Wait()`) from market-data read and Timescale cache-aside paths
- [ ] Keep fresh Timescale-first behavior, provider refresh on miss/stale rows, and safe fallback when storage/provider is unavailable
- [ ] Keep IBKR/iBeam requests cancellable and safely redacted; no raw secrets in errors/logs
- [ ] Run targeted IBKR and Timescale tests

**Artifacts:**
- `src/ATrade.MarketData.Ibkr/*` (modified)
- `src/ATrade.MarketData.Timescale/*` (modified)
- `tests/ATrade.MarketData.Ibkr.Tests/*` (modified)
- `tests/ATrade.MarketData.Timescale.Tests/*` (modified)

### Step 3: Update HTTP, SignalR, and analysis callers

- [ ] Update `ATrade.Api` endpoint handlers to await the deepened market-data read interface and keep response contracts stable
- [ ] Update SignalR snapshot subscription path to use the async read seam or an async streaming seam without duplicate provider status logic
- [ ] Update analysis request construction to obtain candles through the new interface without leaking market-data implementation details into HTTP routing
- [ ] Run targeted AppHost/analysis/market-data scripts

**Artifacts:**
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.MarketData/MarketDataHub.cs` (modified)
- `src/ATrade.Analysis*/*` (modified if needed)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run integration tests if affected: `bash tests/apphost/market-data-feature-tests.sh`, `bash tests/apphost/market-data-timescale-persistence-tests.sh`, `bash tests/apphost/provider-abstraction-contract-tests.sh`, `bash tests/apphost/analysis-engine-contract-tests.sh`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/provider-abstractions.md` — async market-data read seam and cache-aside behavior
- `docs/architecture/modules.md` — MarketData/Timescale/Analysis caller shape if changed
- `docs/architecture/paper-trading-workspace.md` — market-data HTTP/SignalR behavior if changed

**Check If Affected:**
- `README.md` — endpoint/runtime summary if response behavior changes
- `docs/architecture/analysis-engines.md` — candle acquisition path for analysis if changed

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Market-data read paths are async end-to-end with no sync-over-async in provider/cache code
- [ ] HTTP payloads and existing frontend behavior remain compatible
- [ ] Cache-aside and provider-unavailable behavior remain safe and explicit

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-038): complete Step N — description`
- **Bug fixes:** `fix(TP-038): description`
- **Tests:** `test(TP-038): description`
- **Hydration:** `hydrate: TP-038 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Change browser-facing endpoints or payload fields unless backward-compatible
- Add production mock market data, direct frontend database access, real order placement, or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
