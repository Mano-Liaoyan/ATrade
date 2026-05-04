# Task: TP-022 - Replace mocked market data with IBKR/iBeam provider and remove production mocks

**Created:** 2026-04-29
**Size:** L

## Review Level: 3 (Full)

**Assessment:** This removes the current production mocked market-data implementation and replaces it with real IBKR Client Portal/iBeam-backed data behind the provider abstraction. It affects backend data contracts, API behavior, SignalR, frontend labels, tests, and architecture docs, and must safely handle credential/session failures without reintroducing mocks.
**Score:** 6/8 — Blast radius: 2, Pattern novelty: 2, Security: 1, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-022-ibkr-market-data-remove-mocks/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Use the authenticated iBeam/IBKR API runtime from TP-021 to source real market data and remove the production mocked market-data code/configuration. The API and frontend should no longer claim or silently use deterministic mocked symbols, candles, trends, or streaming snapshots. Automated tests may use test-only fake HTTP handlers/fixtures, but production code must not contain a mock market-data provider or a hard-coded symbol catalog fallback.

## Dependencies

- **Task:** TP-019 (provider-neutral broker/market-data abstractions must exist first)
- **Task:** TP-021 (iBeam runtime and `.env` credential contract must exist first)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/provider-abstractions.md` — market-data provider contracts from TP-019
- `docs/architecture/paper-trading-workspace.md` — current mocked data language to replace
- `docs/architecture/modules.md` — MarketData/API/provider module boundaries
- `scripts/README.md` — iBeam `.env` startup flow from TP-021
- `src/ATrade.MarketData/*` — current mocked provider, contracts, indicators, trending, SignalR service
- `src/ATrade.Brokers.Ibkr/*` — iBeam Gateway client/options/status behavior
- `src/ATrade.Api/Program.cs` — current market-data endpoints and hub mapping
- `frontend/components/TradingWorkspace.tsx` — current mocked-data status copy
- `frontend/components/TrendingList.tsx` — current `Mocked factors` label
- `frontend/components/SymbolChartView.tsx` — chart/stream behavior
- `frontend/lib/marketDataClient.ts` — frontend endpoint client
- `tests/apphost/market-data-feature-tests.sh` — current mocked endpoint expectations to replace
- `tests/apphost/frontend-trading-workspace-tests.sh` — current frontend mocked-copy expectations to replace

## Environment

- **Workspace:** Project root plus `frontend/`
- **Services required:** Automated tests must not require real IBKR credentials. Real IBKR/iBeam verification is optional/manual and must use ignored `.env`. Tests should exercise the IBKR provider with fake HTTP handlers/test fixtures and verify API unavailable states when iBeam is not configured.

## File Scope

> This task removes production mocks and changes market-data semantics. It should serialize with search and analysis work.

- `ATrade.sln`
- `src/ATrade.MarketData/*`
- `src/ATrade.MarketData.Ibkr/*` (new or equivalent provider location)
- `src/ATrade.Brokers.Ibkr/*` (only if Gateway client extensions are needed)
- `src/ATrade.Api/ATrade.Api.csproj`
- `src/ATrade.Api/Program.cs`
- `frontend/components/TradingWorkspace.tsx`
- `frontend/components/TrendingList.tsx`
- `frontend/components/SymbolChartView.tsx`
- `frontend/lib/marketDataClient.ts`
- `frontend/types/marketData.ts`
- `tests/ATrade.MarketData.Ibkr.Tests/*` (new)
- `tests/apphost/ibkr-market-data-provider-tests.sh` (new)
- `tests/apphost/market-data-feature-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/provider-abstractions.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm TP-021 has iBeam image/env wiring and safe credential redaction
- [ ] Confirm current production market data is served by `MockMarketDataService`/`MockMarketDataStreamingService` before removing it
- [ ] Confirm tests have a plan for fake HTTP handlers/test fixtures that are not production mock providers

### Step 1: Implement the IBKR/iBeam market-data provider

- [ ] Add an IBKR market-data provider implementation (for example `src/ATrade.MarketData.Ibkr`) that implements the TP-019 market-data provider contracts
- [ ] Use the iBeam/Client Portal Gateway base URL and authenticated session from broker configuration; do not read credentials directly in market-data code
- [ ] Translate IBKR Client Portal endpoints for contract lookup, snapshots/quotes, historical bars, and scanner/trending-equivalent data into ATrade provider-neutral payloads
- [ ] Use IBKR scanner/search data rather than a hard-coded trending symbol catalog; if IBKR lacks a direct trending endpoint, document the scanner query used and expose its source metadata
- [ ] Return clear provider-unavailable/not-authenticated errors when iBeam is disabled, missing credentials, unauthenticated, or degraded
- [ ] Run targeted tests/build: `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal && dotnet build src/ATrade.MarketData.Ibkr/ATrade.MarketData.Ibkr.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.MarketData.Ibkr/ATrade.MarketData.Ibkr.csproj` (new or equivalent)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs` (new or equivalent)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs` (new or equivalent)
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataModels.cs` (new or equivalent)
- `tests/ATrade.MarketData.Ibkr.Tests/*` (new)
- `ATrade.sln` (modified)

### Step 2: Remove production mocked market-data code and configuration

- [ ] Delete or retire `src/ATrade.MarketData/MockMarketDataService.cs` and `src/ATrade.MarketData/MockMarketDataStreamingService.cs` from production build inputs
- [ ] Remove hard-coded production symbol catalogs, `mock-deterministic` source values, `Mocked factors` UI copy, and any config flag that selects mocked market data at runtime
- [ ] Update `MarketDataModuleServiceCollectionExtensions` so production DI uses the IBKR provider and returns safe unavailable responses when the provider is not configured; it must not silently fall back to fake data
- [ ] Keep test fixtures/fake HTTP handlers inside test projects only, with names that make them test-only
- [ ] Run a source audit command and record the result in STATUS.md: no production file under `src/` or `frontend/` should contain `MockMarketData`, `mock-deterministic`, or user-facing `Mocked` market-data labels

**Artifacts:**
- `src/ATrade.MarketData/MockMarketDataService.cs` (deleted or removed from build)
- `src/ATrade.MarketData/MockMarketDataStreamingService.cs` (deleted or removed from build)
- `src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs` (modified)
- `frontend/components/TradingWorkspace.tsx` (modified)
- `frontend/components/TrendingList.tsx` (modified)
- `frontend/components/SymbolChartView.tsx` (modified if user-facing source labels change)

### Step 3: Wire IBKR-backed HTTP and SignalR behavior

- [ ] Update API market-data endpoints so trending/scanner results, candles, indicators, and latest updates flow through the IBKR provider abstraction
- [ ] Update SignalR snapshot/streaming behavior to use IBKR provider snapshots or clearly return provider-unavailable when streaming cannot be established; no mocked streaming fallback
- [ ] Preserve endpoint shapes where possible so the existing frontend keeps working, but include provider/source metadata showing IBKR/iBeam as the data source
- [ ] Update frontend copy and error states so users can distinguish real IBKR data, provider unavailable, and authentication required states
- [ ] Run targeted API/frontend checks with test fixtures and no real credentials

**Artifacts:**
- `src/ATrade.Api/ATrade.Api.csproj` (modified)
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.MarketData/*` (modified)
- `src/ATrade.MarketData.Ibkr/*` (modified)
- `frontend/lib/marketDataClient.ts` (modified if error/source shape changes)
- `frontend/types/marketData.ts` (modified if source metadata is added)

### Step 4: Replace mocked-data verification with IBKR-provider verification

- [ ] Create `tests/apphost/ibkr-market-data-provider-tests.sh`
- [ ] Update or replace `tests/apphost/market-data-feature-tests.sh` so it no longer asserts AAPL/SPY hard-coded mocked symbols or mocked factor placeholders
- [ ] Verify API startup without real credentials returns safe provider-unavailable responses instead of fake data
- [ ] Verify IBKR provider mapping with fake HTTP responses for contract lookup, snapshots, historical bars, and scanner/trending-equivalent results
- [ ] Update frontend trading workspace tests so user-facing copy no longer says mocked backend/factors
- [ ] Run targeted tests: `bash tests/apphost/ibkr-market-data-provider-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh`

**Artifacts:**
- `tests/apphost/ibkr-market-data-provider-tests.sh` (new)
- `tests/apphost/market-data-feature-tests.sh` (modified)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified)

### Step 5: Update docs for real IBKR data and removed mocks

- [ ] Update `docs/architecture/paper-trading-workspace.md` to state production market data now comes from IBKR/iBeam and production mocks have been removed
- [ ] Update `docs/architecture/modules.md` so `ATrade.MarketData`, API, frontend, and any new IBKR provider module current-state notes match the implementation
- [ ] Update `docs/architecture/provider-abstractions.md` with the IBKR market-data provider implementation and how future providers plug in
- [ ] Update `README.md` only if current-status wording becomes stale

**Artifacts:**
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `docs/architecture/provider-abstractions.md` (modified)
- `README.md` (modified if affected)

### Step 6: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/ibeam-runtime-contract-tests.sh && bash tests/apphost/ibkr-market-data-provider-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/provider-abstraction-contract-tests.sh && bash tests/apphost/postgres-watchlist-persistence-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm Docker/iBeam-dependent runtime tests pass or cleanly skip without real credentials
- [ ] Fix all failures
- [ ] Source audit confirms production mocks/configuration were removed
- [ ] Frontend build passes: `cd frontend && npm run build`
- [ ] Solution build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 7: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — replace mocked-data current state with IBKR/iBeam-backed data behavior
- `docs/architecture/modules.md` — update MarketData/API/frontend/provider current-state notes
- `docs/architecture/provider-abstractions.md` — record IBKR as the first real market-data provider implementation

**Check If Affected:**
- `README.md` — update current status if mocked market-data wording exists
- `scripts/README.md` — update only if iBeam startup or env behavior changes beyond TP-021
- `docs/INDEX.md` — update only if new indexed docs are added (none expected)

## Completion Criteria

- [ ] Production market data comes from the IBKR/iBeam provider when configured
- [ ] Production mocked market-data code/configuration and user-facing mocked labels are removed
- [ ] API/SignalR/frontend handle provider unavailable/authentication-required states safely and honestly
- [ ] Automated tests use test-only fake handlers/fixtures, not production mock providers
- [ ] Active docs no longer describe mocked market data as the implemented runtime source

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-022): complete Step N — description`
- **Bug fixes:** `fix(TP-022): description`
- **Tests:** `test(TP-022): description`
- **Hydration:** `hydrate: TP-022 expand Step N checkboxes`

## Do NOT

- Keep a production mock market-data provider, hard-coded catalog fallback, or mocked runtime configuration under a new name
- Require real IBKR credentials for automated tests
- Leak IBKR credentials or account identifiers in market-data responses, logs, frontend code, or test output
- Add real order placement or live-trading UI behavior
- Remove provider abstractions in favor of direct API/controller coupling to IBKR
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
