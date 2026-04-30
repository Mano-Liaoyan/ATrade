# Task: TP-030 - Serve market data through TimescaleDB cache-aside

**Created:** 2026-04-30
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This wires a new persistence path into the browser-facing market-data endpoints and must preserve provider-neutral API semantics, safe IBKR unavailable behavior, and no direct frontend database access. It spans API composition, MarketData services, the Timescale module, tests, and docs, but builds on the dedicated persistence foundation from TP-029.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 2

## Canonical Task Folder

```text
tasks/TP-030-market-data-timescale-cache-aside/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Implement the requested market-data persistence flow: the frontend continues to fetch market data through `ATrade.Api`, and the API reads from TimescaleDB first. If TimescaleDB has data within the configurable freshness period (default 30 minutes from `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`), the API returns that persisted data directly; if the data is missing or stale, the API fetches from the IBKR/iBeam provider, stores the result in TimescaleDB, and returns it. No browser code may connect directly to TimescaleDB.

## Dependencies

- **Task:** TP-028 (IBKR scanner/trending request must no longer fail with 411 Length Required)
- **Task:** TP-029 (TimescaleDB market-data persistence foundation and freshness option must exist)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite. Do **not** read, print, or commit the ignored repo-root `.env` file.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/paper-trading-workspace.md` — expected frontend/API/Timescale data path
- `docs/architecture/provider-abstractions.md` — provider-neutral error/source semantics
- `docs/architecture/modules.md` — MarketData/API/Timescale module ownership
- `scripts/README.md` — freshness `.env` configuration contract from TP-029
- `src/ATrade.Api/Program.cs` — market-data endpoint and DI composition
- `src/ATrade.Api/ATrade.Api.csproj` — references to the Timescale module if needed
- `src/ATrade.MarketData/*` — compatibility service and payload shapes
- `src/ATrade.MarketData.Timescale/*` — repository/options/schema from TP-029
- `src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs` — provider behavior to wrap, not bypass
- `tests/ATrade.MarketData.Timescale.Tests/*` — foundation test patterns
- `tests/ATrade.MarketData.Ibkr.Tests/*` — provider test patterns
- `tests/apphost/market-data-feature-tests.sh` — API endpoint behavior
- `tests/apphost/ibkr-market-data-provider-tests.sh` — provider-unavailable behavior
- `tests/apphost/frontend-trading-workspace-tests.sh` — frontend source/error expectations if API response metadata changes

## Environment

- **Workspace:** Repository root
- **Services required:** Automated unit/source tests must not require real IBKR credentials. Timescale integration checks may use a Docker/Podman-compatible engine and must cleanly skip when unavailable. Optional real iBeam verification must use ignored local `.env` values and redact all sensitive output.

## File Scope

> The orchestrator uses this to avoid merge conflicts. Keep changes inside this scope unless `STATUS.md` records a discovered prerequisite.

- `src/ATrade.Api/ATrade.Api.csproj`
- `src/ATrade.Api/Program.cs`
- `src/ATrade.MarketData/MarketDataModels.cs`
- `src/ATrade.MarketData/MarketDataProviderModels.cs` (only if cache/source metadata shapes change)
- `src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs`
- `src/ATrade.MarketData/MarketDataService.cs`
- `src/ATrade.MarketData/IndicatorService.cs` (only if indicators need a cache-friendly seam)
- `src/ATrade.MarketData.Timescale/*`
- `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataCacheAsideTests.cs` (new, or equivalent new focused test file)
- `tests/ATrade.MarketData.Timescale.Tests/*`
- `tests/ATrade.MarketData.Ibkr.Tests/*` (only if provider contract fixtures need adjustment)
- `tests/apphost/market-data-timescale-persistence-tests.sh`
- `tests/apphost/market-data-feature-tests.sh`
- `tests/apphost/ibkr-market-data-provider-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh` (only if frontend-visible metadata changes)
- `frontend/lib/marketDataClient.ts` and `frontend/types/marketData.ts` (only if response JSON shape changes; avoid if source strings are sufficient)
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/provider-abstractions.md`
- `docs/architecture/modules.md`
- `README.md` (only if current runtime surface wording changes)
- `tasks/TP-030-market-data-timescale-cache-aside/STATUS.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Dependency preflight and data-path plan

- [ ] Confirm TP-028 is complete and scanner/trending requests have regression coverage for explicit content length
- [ ] Confirm TP-029 is complete and the Timescale schema/repository/options compile and expose `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`
- [ ] Record in `STATUS.md` the cache-aside plan for trending, candles, indicators, and provider-unavailable edge cases before modifying endpoint behavior

**Artifacts:**
- `tasks/TP-030-market-data-timescale-cache-aside/STATUS.md` (modified)

### Step 1: Compose a cache-aware market-data service

- [ ] Register the Timescale module in `ATrade.Api` using the AppHost-provided `ConnectionStrings:timescaledb`
- [ ] Add a cache-aware `IMarketDataService` implementation/decorator that composes the existing provider-backed market-data service and the Timescale repository without making endpoint handlers provider-specific
- [ ] Ensure schema initialization happens idempotently before cache reads/writes, with safe storage-unavailable behavior when TimescaleDB is unreachable
- [ ] Ensure the configured freshness window is read once through typed options and can be overridden from ignored `.env`
- [ ] Run targeted build/tests for API and market-data composition

**Artifacts:**
- `src/ATrade.Api/ATrade.Api.csproj` (modified)
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs` (modified if DI changes there)
- `src/ATrade.MarketData.Timescale/*` (modified)

### Step 2: Cache-aside `/api/market-data/trending`

- [ ] Before calling IBKR/iBeam, read the most recent Timescale trending/scanner snapshot that is newer than `now - freshnessWindow`
- [ ] When a fresh persisted snapshot exists, return it directly with source metadata that honestly identifies the persisted/provider source (for example `timescale-cache` plus the original provider source)
- [ ] When no fresh snapshot exists, fetch the provider-backed trending response, persist the full response needed to reconstruct frontend-compatible `TrendingSymbolsResponse`, and return the provider response
- [ ] If the provider is unavailable but a fresh Timescale snapshot exists, return the fresh persisted snapshot; if only stale data exists, return the safe provider error instead of pretending stale data is current
- [ ] Add tests for fresh hit, stale miss/provider refresh, write-after-provider-fetch, and provider-unavailable-with-fresh-cache behavior

**Artifacts:**
- `src/ATrade.MarketData.Timescale/*` (modified)
- `src/ATrade.MarketData/MarketDataService.cs` or cache-aware equivalent (modified/new)
- `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataCacheAsideTests.cs` (new)
- `tests/apphost/market-data-feature-tests.sh` (modified)

### Step 3: Cache-aside candles and indicator inputs

- [ ] For `GET /api/market-data/{symbol}/candles`, read fresh Timescale candle rows for the symbol/timeframe/provider identity before calling IBKR/iBeam
- [ ] On a cache miss or stale candle series, fetch provider candles, persist them to TimescaleDB, and return the fresh provider response
- [ ] Make `GET /api/market-data/{symbol}/indicators` compute indicators from cached candles when candles are fresh, and fetch/persist provider candles only when the candle cache is missing or stale
- [ ] Preserve unsupported-symbol/timeframe and provider-unavailable error behavior; do not turn stale data into successful fresh data without explicit metadata and tests
- [ ] Add tests for candle hit/miss/stale paths and indicator reuse of cached candles

**Artifacts:**
- `src/ATrade.MarketData.Timescale/*` (modified)
- `src/ATrade.MarketData/MarketDataService.cs` or cache-aware equivalent (modified/new)
- `src/ATrade.MarketData/IndicatorService.cs` (modified only if needed)
- `tests/ATrade.MarketData.Timescale.Tests/*` (modified/new)
- `tests/apphost/market-data-feature-tests.sh` (modified)

### Step 4: API/frontend compatibility and observability

- [ ] Keep existing API routes and frontend fetch clients stable unless a minimal optional cache-source field is needed; direct frontend-to-Timescale access is forbidden
- [ ] Ensure the home page can load from fresh Timescale data after an API/service restart without needing a live IBKR fetch within the freshness period
- [ ] Ensure API errors still explain provider-not-configured/provider-unavailable/authentication-required states safely when no fresh cache is available
- [ ] Update frontend tests only if response source text or user-facing copy changes
- [ ] Run targeted endpoint/apphost tests

**Artifacts:**
- `src/ATrade.Api/Program.cs` (modified if endpoint error/source mapping changes)
- `frontend/types/marketData.ts` (modified only if response shape changes)
- `frontend/lib/marketDataClient.ts` (modified only if response shape changes)
- `tests/apphost/market-data-feature-tests.sh` (modified)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified only if frontend-visible text changes)

### Step 5: Testing & Verification

> ZERO unexpected test failures allowed. Runtime-dependent checks must pass or cleanly skip according to existing contracts.

- [ ] Run `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal`
- [ ] Run `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal`
- [ ] Run `bash tests/apphost/market-data-timescale-persistence-tests.sh`
- [ ] Run `bash tests/apphost/market-data-feature-tests.sh`
- [ ] Run `bash tests/apphost/ibkr-market-data-provider-tests.sh`
- [ ] If frontend files changed, run `bash tests/apphost/frontend-trading-workspace-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] If frontend files changed, run frontend build: `cd frontend && npm run build`
- [ ] Run solution build: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures or record pre-existing unrelated failures with evidence in `STATUS.md`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs describe the implemented Timescale-first/cache-aside market-data path and freshness behavior
- [ ] "Check If Affected" docs reviewed and updated only where relevant
- [ ] `STATUS.md` Discoveries record cache-hit/miss semantics, provider-unavailable behavior, and any future work for richer symbol identity caching

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — document the Timescale-first market-data read path and freshness behavior
- `docs/architecture/provider-abstractions.md` — document cache/source metadata and provider-unavailable semantics when fresh persisted data exists
- `docs/architecture/modules.md` — update API/MarketData/Timescale responsibilities after endpoint integration

**Check If Affected:**
- `scripts/README.md` — update if freshness configuration wording from TP-029 changes
- `README.md` — update if current runtime surface now includes Timescale-backed market-data persistence
- `docs/architecture/overview.md` — update if the high-level architecture summary changes
- `docs/INDEX.md` — update only if new active docs are introduced

## Completion Criteria

- [ ] Market-data endpoints read from TimescaleDB first when data is fresh according to `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`
- [ ] Missing/stale data triggers provider fetch, Timescale persistence, and return of the fresh provider response
- [ ] Fresh persisted data can serve `/api/market-data/trending` and candle/indicator paths after an API/service restart
- [ ] Stale data is not silently presented as current when provider refresh fails
- [ ] Tests cover cache hits, misses, stale refreshes, persistence writes, and safe unavailable states
- [ ] The frontend still goes through `ATrade.Api`; it never connects directly to TimescaleDB

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-030): complete Step N — description`
- **Bug fixes:** `fix(TP-030): description`
- **Tests:** `test(TP-030): description`
- **Hydration:** `hydrate: TP-030 expand Step N checkboxes`

## Do NOT

- Start before TP-028 and TP-029 are complete
- Read, print, or commit ignored `.env` values, broker credentials, account ids, session cookies, or tokens
- Let the frontend connect directly to TimescaleDB
- Serve stale Timescale data as if it were fresh when provider refresh fails
- Reintroduce production mock market data or hard-coded production symbol catalogs
- Skip tests or commit without the task ID prefix

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
