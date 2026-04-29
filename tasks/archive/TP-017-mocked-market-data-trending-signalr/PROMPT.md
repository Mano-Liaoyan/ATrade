# Task: TP-017 - Implement mocked market data, trending stocks/ETFs, and SignalR streaming

**Created:** 2026-04-29
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This turns the current MarketData shell into the first usable mocked data backend and adds streaming API behavior. It affects the API host, MarketData module, tests, and architecture docs, but avoids secrets, broker trading, persistence, and external providers.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-017-mocked-market-data-trending-signalr/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Implement the backend data layer needed by the TradingView-like frontend MVP. `ATrade.MarketData` should expose deterministic mocked stocks/ETFs, OHLC candle series for common timeframes, simple indicators, and a trending score that starts with volume spikes, price momentum, volatility, and a placeholder for future news sentiment. `ATrade.Api` should expose the data over HTTP and SignalR so the frontend can render charts and receive real-time updates without requiring Polygon, IBKR, LEAN, databases, or external services.

## Dependencies

- **Task:** TP-015 (paper-trading workspace architecture and data-flow contract must exist first)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/paper-trading-workspace.md` — data-flow, trending, SignalR, and future LEAN seam contract
- `docs/architecture/modules.md` — MarketData/API module boundaries
- `docs/architecture/overview.md` — runtime and infrastructure topology
- `src/ATrade.MarketData/ATrade.MarketData.csproj` — current MarketData project shell
- `src/ATrade.MarketData/MarketDataAssemblyMarker.cs` — current marker-only implementation
- `src/ATrade.Api/ATrade.Api.csproj` — API project references
- `src/ATrade.Api/Program.cs` — current endpoint registration style
- `tests/apphost/accounts-feature-bootstrap-tests.sh` — direct API feature-test pattern
- `scripts/local-env.sh` — local port contract helper used by shell tests

## Environment

- **Workspace:** Project root
- **Services required:** None. This slice must run without Postgres, TimescaleDB, Redis, NATS, IBKR, Polygon, LEAN, or paid data/news APIs.

## File Scope

> This task overlaps `src/ATrade.Api/*` with TP-016. Dependencies and lane affinity should prevent unsafe parallel edits.

- `src/ATrade.MarketData/*`
- `src/ATrade.Api/ATrade.Api.csproj`
- `src/ATrade.Api/Program.cs`
- `tests/apphost/market-data-feature-tests.sh` (new)
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm `ATrade.MarketData` currently contains only marker/shell behavior
- [ ] Confirm no external market-data provider credentials or runtime services are required

### Step 1: Implement deterministic mocked market-data contracts and services

- [ ] Add MarketData response types for symbols, OHLC candles, timeframes (`1m`, `5m`, `1h`, `1D`), indicators, and trending scores
- [ ] Implement a deterministic mock symbol catalog that includes both stocks and ETFs
- [ ] Implement candle generation that returns stable OHLCV values per symbol/timeframe for tests while still looking realistic enough for charting
- [ ] Implement simple indicator calculations or payloads for moving averages, RSI, and MACD
- [ ] Implement a trending score that combines volume spike, price momentum, volatility, and a documented news-sentiment placeholder without calling external services
- [ ] Run targeted build: `dotnet build src/ATrade.MarketData/ATrade.MarketData.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.MarketData/MarketDataAssemblyMarker.cs` (modified or preserved)
- `src/ATrade.MarketData/MarketDataModels.cs` (new or equivalent)
- `src/ATrade.MarketData/MockMarketDataService.cs` (new or equivalent)
- `src/ATrade.MarketData/IndicatorService.cs` (new or equivalent)
- `src/ATrade.MarketData/TrendingService.cs` (new or equivalent)
- `src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs` (new or equivalent)

### Step 2: Expose MarketData HTTP endpoints through the API

- [ ] Add a project reference from `src/ATrade.Api/ATrade.Api.csproj` to `src/ATrade.MarketData/ATrade.MarketData.csproj` if missing
- [ ] Register MarketData services during API startup in `src/ATrade.Api/Program.cs`
- [ ] Map `GET /api/market-data/trending` for trending stocks/ETFs with reason fields for score components
- [ ] Map `GET /api/market-data/{symbol}/candles?timeframe=...` for OHLCV candles and validate unsupported symbols/timeframes
- [ ] Map `GET /api/market-data/{symbol}/indicators?timeframe=...` or include indicators in the candle response using a documented shape
- [ ] Preserve existing `GET /health`, `GET /api/accounts/overview`, and any TP-016 endpoints exactly
- [ ] Run targeted API smoke checks for health, trending, candles, indicators, and invalid timeframe behavior

**Artifacts:**
- `src/ATrade.Api/ATrade.Api.csproj` (modified)
- `src/ATrade.Api/Program.cs` (modified)

### Step 3: Add SignalR real-time market-data streaming

- [ ] Add a SignalR hub such as `/hubs/market-data` that supports symbol/timeframe subscription semantics suitable for the frontend
- [ ] Publish deterministic mocked candle/tick updates from an in-process service without requiring NATS or external streams
- [ ] Ensure clients can receive updates without breaking plain HTTP endpoint usage
- [ ] Keep the design compatible with future NATS/TimescaleDB/LEAN-backed real signals documented in TP-015
- [ ] Run targeted build and any hub smoke checks added in this task

**Artifacts:**
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.MarketData/MarketDataHub.cs` (new or equivalent)
- `src/ATrade.MarketData/MockMarketDataStreamingService.cs` (new or equivalent)

### Step 4: Add market-data feature verification

- [ ] Create `tests/apphost/market-data-feature-tests.sh`
- [ ] Verify `ATrade.Api` references `ATrade.MarketData` and the solution builds
- [ ] Start `ATrade.Api` using the repo local-port contract and assert `/health` still returns `ok`
- [ ] Assert `GET /api/market-data/trending` returns stocks and ETFs with deterministic score components
- [ ] Assert candle and indicator endpoints support `1m`, `5m`, `1h`, and `1D` and reject invalid values
- [ ] Assert SignalR hub registration is present in API startup and does not require external services for startup
- [ ] Run targeted test: `bash tests/apphost/market-data-feature-tests.sh`

**Artifacts:**
- `tests/apphost/market-data-feature-tests.sh` (new)

### Step 5: Update docs for mocked data and future real signals

- [ ] Update `docs/architecture/paper-trading-workspace.md` with implemented endpoints, SignalR hub shape, mocked trending logic, and the future LEAN signal handoff seam
- [ ] Update `docs/architecture/modules.md` so `ATrade.MarketData` and `ATrade.Api` current-state notes describe the mocked market-data slice without overstating Polygon, TimescaleDB, NATS, or LEAN integration
- [ ] Update `docs/architecture/overview.md` only if the current runtime surface description changes
- [ ] Update `README.md` only if current-status text would otherwise be stale

**Artifacts:**
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `docs/architecture/overview.md` (modified if affected)
- `README.md` (modified if affected)

### Step 6: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet build ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm `apphost-infrastructure-runtime-tests.sh` passes or cleanly skips when no Docker-compatible engine is available
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 7: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — record endpoint/hub shape, mocked trending factors, and future LEAN handoff seam
- `docs/architecture/modules.md` — update MarketData/API current-state notes for mocked HTTP + SignalR behavior

**Check If Affected:**
- `docs/architecture/overview.md` — update if runtime surface changes materially
- `README.md` — update if current-status wording becomes stale
- `docs/INDEX.md` — update only if new indexed docs are added (none expected)

## Completion Criteria

- [ ] `ATrade.MarketData` contains deterministic mocked market-data behavior, not only a marker type
- [ ] API exposes trending, candles, indicators, and SignalR market-data streaming without external services
- [ ] Trending results include stocks and ETFs with explainable score components
- [ ] Common timeframes (`1m`, `5m`, `1h`, `1D`) work and invalid values are rejected
- [ ] Tests prove the endpoints and startup behavior are stable without Polygon, IBKR, LEAN, TimescaleDB, Redis, or NATS
- [ ] Active docs accurately describe mocked data now and real-signal integration later

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-017): complete Step N — description`
- **Bug fixes:** `fix(TP-017): description`
- **Tests:** `test(TP-017): description`
- **Hydration:** `hydrate: TP-017 expand Step N checkboxes`

## Do NOT

- Add Polygon, LEAN, news, broker, or paid market-data integrations in this mocked-data task
- Add database schemas, migrations, TimescaleDB writes, Redis caches, or NATS consumers/producers yet
- Generate non-deterministic test data that makes shell/API assertions flaky
- Break existing health, Accounts, or TP-016 broker/order endpoints
- Expose secrets, real brokerage account information, or real trading behavior
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
