# Task: TP-042 - Correct chart range presets

**Created:** 2026-05-04
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This changes the browser chart controls plus the backend market-data range contract, IBKR historical-bar mapping, Timescale cache keys/reads, and verification surface. The change is reversible but crosses frontend and backend market-data seams, so it needs plan and code review.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-042-chart-range-presets/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Correct the chart workspace time controls so user-facing presets mean **lookback ranges from now**, not candle interval labels. Selecting `1D` must display approximately the past day from the current time, `1m` must mean the past one month, `6m` must mean the past six months, and the UI must expose `1min`, `5mins`, `1h`, `6h`, `1D`, `1m`, `6m`, `1y`, `5y`, and `All time`. This matters because the current chart control overloads `1m` as one-minute bars and `1D` as daily candles, which makes the workspace misleading for trading analysis.

## Dependencies

- **External:** Completed TP-041 frontend workflow modules are archived at `tasks/archive/TP-041-frontend-workspace-workflow-modules/` and should be treated as already satisfied before this task starts.

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/paper-trading-workspace.md` — chart workspace, frontend workflow, SignalR fallback, and paper-only UI contract
- `docs/architecture/provider-abstractions.md` — provider-neutral market-data payload/source contract
- `docs/architecture/modules.md` — frontend and market-data module responsibilities

## Environment

- **Workspace:** `src/ATrade.MarketData*`, `src/ATrade.Api`, and `frontend/`
- **Services required:** None for source/TypeScript/unit checks; AppHost/API shell tests must use fake/local providers or skip cleanly when real IBKR/iBeam is unavailable

## File Scope

- `src/ATrade.Api/Program.cs`
- `src/ATrade.MarketData/ChartRangePresets.cs` (new)
- `src/ATrade.MarketData/MarketDataModels.cs`
- `src/ATrade.MarketData/MarketDataProviderContracts.cs`
- `src/ATrade.MarketData/MarketDataStreamingService.cs`
- `src/ATrade.MarketData/MarketDataHub.cs`
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs`
- `src/ATrade.MarketData.Timescale/TimescaleCachedMarketDataService.cs`
- `src/ATrade.MarketData.Timescale/TimescaleMarketDataModels.cs`
- `src/ATrade.MarketData.Timescale/TimescaleMarketDataRepository.cs`
- `frontend/types/marketData.ts`
- `frontend/lib/marketDataClient.ts`
- `frontend/lib/marketDataStream.ts`
- `frontend/lib/symbolChartWorkflow.ts`
- `frontend/components/TimeframeSelector.tsx`
- `frontend/components/SymbolChartView.tsx`
- `frontend/components/AnalysisPanel.tsx` (only if selected chart range affects analysis run payloads)
- `tests/ATrade.ProviderAbstractions.Tests/ChartRangePresetContractTests.cs` (new)
- `tests/ATrade.MarketData.Ibkr.Tests/IbkrMarketDataProviderTests.cs`
- `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataCacheAsideTests.cs`
- `tests/apphost/frontend-chart-range-preset-tests.sh` (new)
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `tests/apphost/frontend-workspace-workflow-module-tests.sh`
- `tests/apphost/market-data-feature-tests.sh`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/provider-abstractions.md`
- `docs/architecture/modules.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Model chart ranges as lookbacks from now

- [ ] Create `src/ATrade.MarketData/ChartRangePresets.cs` with supported presets `1min`, `5mins`, `1h`, `6h`, `1D`, `1m`, `6m`, `1y`, `5y`, and `all`, including display labels, normalized API values, provider period/bar-size hints, and a `nowUtc`-based lookback boundary where applicable
- [ ] Update market-data models/contracts so chart reads normalize the requested range while keeping the legacy `timeframe` query name accepted as a compatibility alias if a full method rename is too disruptive
- [ ] Add `tests/ATrade.ProviderAbstractions.Tests/ChartRangePresetContractTests.cs` covering `1D` = past day, `1m` = past month, `6m` = past six months, minute presets are `1min`/`5mins`, and unsupported values produce a clear supported-values error
- [ ] Run targeted tests: `dotnet test tests/ATrade.ProviderAbstractions.Tests/ATrade.ProviderAbstractions.Tests.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.MarketData/ChartRangePresets.cs` (new)
- `src/ATrade.MarketData/MarketDataModels.cs` (modified)
- `src/ATrade.MarketData/MarketDataProviderContracts.cs` (modified)
- `tests/ATrade.ProviderAbstractions.Tests/ChartRangePresetContractTests.cs` (new)

### Step 2: Wire ranges through API, provider, stream, and cache

- [ ] Update `src/ATrade.Api/Program.cs`, `MarketDataHub`, and streaming service code so HTTP candle/indicator reads and SignalR subscriptions use the normalized chart range and still accept existing `timeframe` callers safely
- [ ] Update `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs` so provider period/bar-size requests support every new range and returned candles are filtered to the requested lookback window from `DateTimeOffset.UtcNow` (except `all`)
- [ ] Update Timescale cache-aside reads/writes so range keys are normalized, fresh cached candles for each range are returned only when they satisfy the requested lookback semantics, and old `1m` minute-cache assumptions do not leak into month-range reads
- [ ] Add or update targeted backend/provider/cache tests for range normalization, cache separation, and provider error messages

**Artifacts:**
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.MarketData/MarketDataHub.cs` (modified)
- `src/ATrade.MarketData/MarketDataStreamingService.cs` (modified)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs` (modified)
- `src/ATrade.MarketData.Timescale/TimescaleCachedMarketDataService.cs` (modified)
- `src/ATrade.MarketData.Timescale/TimescaleMarketDataModels.cs` (modified if needed)
- `src/ATrade.MarketData.Timescale/TimescaleMarketDataRepository.cs` (modified if needed)
- `tests/ATrade.MarketData.Ibkr.Tests/IbkrMarketDataProviderTests.cs` (modified)
- `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataCacheAsideTests.cs` (modified)

### Step 3: Update frontend chart controls and workflow copy

- [ ] Update `frontend/types/marketData.ts`, `marketDataClient.ts`, and `marketDataStream.ts` to send normalized range values (`1min`, `5mins`, `1h`, `6h`, `1D`, `1m`, `6m`, `1y`, `5y`, `all`) instead of ambiguous minute/month `timeframe` values
- [ ] Update `frontend/lib/symbolChartWorkflow.ts`, `TimeframeSelector.tsx`, and `SymbolChartView.tsx` so the control is presented as a chart range/lookback selector and `1D`/`1m`/`6m` copy clearly means past day/month/six months from now
- [ ] Preserve SignalR-to-HTTP fallback, indicator panel, analysis panel behavior, and exact instrument identity query parameters while changing only the time-range semantics
- [ ] Create `tests/apphost/frontend-chart-range-preset-tests.sh` asserting the new labels, the absence of old user-facing `5m`, the frontend client parameters, and chart page SSR markers

**Artifacts:**
- `frontend/types/marketData.ts` (modified)
- `frontend/lib/marketDataClient.ts` (modified)
- `frontend/lib/marketDataStream.ts` (modified)
- `frontend/lib/symbolChartWorkflow.ts` (modified)
- `frontend/components/TimeframeSelector.tsx` (modified)
- `frontend/components/SymbolChartView.tsx` (modified)
- `frontend/components/AnalysisPanel.tsx` (modified only if needed)
- `tests/apphost/frontend-chart-range-preset-tests.sh` (new)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run frontend checks: `cd frontend && npm run build`
- [ ] Run targeted integration/shell tests: `bash tests/apphost/frontend-chart-range-preset-tests.sh`, `bash tests/apphost/frontend-trading-workspace-tests.sh`, `bash tests/apphost/frontend-workspace-workflow-module-tests.sh`, and `bash tests/apphost/market-data-feature-tests.sh`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — chart workspace range controls now mean lookback windows from now, including the supported preset list
- `docs/architecture/provider-abstractions.md` — market-data candle/indicator read contract and range/timeframe compatibility behavior
- `docs/architecture/modules.md` — frontend/market-data module responsibilities if new range helper types are introduced
- `README.md` — verification entry point list if `frontend-chart-range-preset-tests.sh` is added

**Check If Affected:**
- `docs/architecture/analysis-engines.md` — update only if analysis runs receive chart range values or behavior changes

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Chart UI exposes `1min`, `5mins`, `1h`, `6h`, `1D`, `1m`, `6m`, `1y`, `5y`, and `All time`
- [ ] `1D` displays a past-day lookback from now, `1m` displays a past-month lookback, and `6m` displays a past-six-month lookback
- [ ] Backend API, provider, Timescale cache, frontend client, and stream code agree on normalized range values
- [ ] Old user-facing `1m` as one-minute and `5m` as five-minute labels are gone from the chart UI

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-042): complete Step N — description`
- **Bug fixes:** `fix(TP-042): description`
- **Tests:** `test(TP-042): description`
- **Hydration:** `hydrate: TP-042 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Treat user-facing `1m` as one minute; `1m` means one month for chart range controls
- Add direct frontend access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, or LEAN
- Add real order placement or live-trading behavior
- Commit secrets, IBKR credentials, account identifiers, tokens, or session cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
