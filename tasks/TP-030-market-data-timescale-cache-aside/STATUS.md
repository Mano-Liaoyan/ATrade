# TP-030: Serve market data through TimescaleDB cache-aside — Status

**Current Step:** Step 1: Compose a cache-aware market-data service
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 2
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Dependency preflight and data-path plan
**Status:** ✅ Complete

- [x] TP-028 completion and scanner content-length regression coverage confirmed
- [x] TP-029 completion and Timescale repository/options confirmed
- [x] Cache-aside plan for trending, candles, indicators, and unavailable states recorded

---

### Step 1: Compose a cache-aware market-data service
**Status:** ✅ Complete

- [x] Timescale module registered in `ATrade.Api` using `ConnectionStrings:timescaledb`
- [x] Cache-aware `IMarketDataService` implementation/decorator added without endpoint provider coupling
- [x] Idempotent schema initialization and storage-unavailable behavior implemented
- [x] Freshness window read via typed options from `.env`/configuration
- [x] Targeted API/market-data build/tests run

---

### Step 2: Cache-aside `/api/market-data/trending`
**Status:** ⬜ Not Started

- [ ] Fresh Timescale trending/scanner snapshot read before IBKR/iBeam call
- [ ] Fresh persisted snapshot returned with honest source metadata
- [ ] Missing/stale snapshot triggers provider fetch, persistence write, and provider response
- [ ] Provider-unavailable with fresh cache returns cache; provider-unavailable with stale-only cache returns safe error
- [ ] Tests cover hit, miss, stale refresh, write-after-fetch, and fresh-cache unavailable behavior

---

### Step 3: Cache-aside candles and indicator inputs
**Status:** ⬜ Not Started

- [ ] Candle endpoint reads fresh Timescale candles before provider call
- [ ] Missing/stale candle series fetches provider candles, persists them, and returns fresh response
- [ ] Indicator endpoint computes from cached candles when fresh
- [ ] Unsupported/timeframe/provider errors preserved without stale-as-fresh behavior
- [ ] Tests cover candle and indicator cache paths

---

### Step 4: API/frontend compatibility and observability
**Status:** ⬜ Not Started

- [ ] Existing routes and frontend clients remain stable unless minimal metadata is required
- [ ] Home page can load from fresh Timescale data after service restart
- [ ] No-fresh-cache provider errors remain safe and actionable
- [ ] Frontend tests updated only if visible source/error text changes
- [ ] Targeted endpoint/apphost tests run

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passing
- [ ] `dotnet test tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj --nologo --verbosity minimal` passing
- [ ] `bash tests/apphost/market-data-timescale-persistence-tests.sh` passing or cleanly skipped
- [ ] `bash tests/apphost/market-data-feature-tests.sh` passing
- [ ] `bash tests/apphost/ibkr-market-data-provider-tests.sh` passing
- [ ] Frontend trading workspace tests passing if frontend files changed
- [ ] FULL test suite passing: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Frontend build passing if frontend files changed
- [ ] Solution build passing: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] All failures fixed or unrelated pre-existing failures documented

---

### Step 6: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged with cache semantics, unavailable behavior, and future-work notes

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| TP-028 is complete and includes `IbkrScannerRequestContractTests.GetTrendingScannerResultsAsync_SendsBufferedJsonWithContentLengthAndNoChunkedTransfer`; `IbkrMarketDataClient.GetTrendingScannerResultsAsync` now sends buffered JSON with explicit positive `Content-Length` and `TransferEncodingChunked = false`. | Dependency satisfied for TP-030; cache-aside trending can rely on provider scanner transport regression coverage. | `tasks/TP-028-ibkr-scanner-content-length-fix/STATUS.md`, `tests/ATrade.MarketData.Ibkr.Tests/IbkrScannerRequestContractTests.cs`, `src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs` |
| TP-029 is complete and the Timescale module compiles/tests: `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passed 20/20. The module exposes idempotent schema initialization, repository read/upsert methods, `ConnectionStrings:timescaledb` composition, storage-unavailable exceptions, and `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` typed options with a 30-minute default. | Dependency satisfied for TP-030; implementation can compose Timescale persistence instead of creating a new storage foundation. | `tasks/TP-029-timescale-market-data-persistence-foundation/STATUS.md`, `src/ATrade.MarketData.Timescale/*`, `tests/ATrade.MarketData.Timescale.Tests/*` |
| Cache-aside plan: register `ATrade.MarketData.Timescale` in `ATrade.Api`, expose the provider-backed `MarketDataService` as a concrete inner service, and register a Timescale-backed `IMarketDataService` decorator that uses provider identity plus typed freshness options. Reads initialize schema idempotently, compute `now - CacheFreshnessPeriod`, try fresh Timescale rows first, and tolerate `TimescaleMarketDataStorageUnavailableException` by falling back to the provider path. | Implementation plan for Step 1 composition and safe storage-unavailable behavior. | `src/ATrade.Api/Program.cs`, `src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs`, `src/ATrade.MarketData.Timescale/*` |
| Trending plan: query latest fresh snapshot by provider before any provider call, allowing source-agnostic repository reads so the cache can store the original provider source (`response.Source`) and return cached responses with source like `timescale-cache:{originalSource}`. On miss/stale data, call the provider-backed service, persist the full `TrendingSymbolsResponse` into Timescale, and return the provider response. If the provider is unavailable but a fresh cache exists, return the cache; if only stale/no cache exists, surface the provider-safe error. | Implementation plan for Step 2 cache-hit, miss, write-after-fetch, and unavailable semantics. | `src/ATrade.MarketData.Timescale/*`, `src/ATrade.MarketData/MarketDataService.cs` or cache-aware equivalent |
| Candle/indicator plan: normalize supported timeframes, read fresh candle series by provider/symbol/timeframe before provider calls, return cached candles with `timescale-cache:{originalSource}` source, and on miss/stale fetch provider candles, persist them, and return the provider response. Indicators should call the cache-aware candle path and calculate with `IndicatorService`, so fresh cached candles serve indicators after restart and cache misses fetch/persist candles once. Unsupported symbol/timeframe and provider-unavailable errors remain provider-safe; stale rows are never returned as fresh after a failed refresh. | Implementation plan for Step 3 candle and indicator cache-aside semantics. | `src/ATrade.MarketData.Timescale/*`, `src/ATrade.MarketData/IndicatorService.cs` only if needed |
| Source/identity caveat: current endpoint payloads do not carry provider symbol ids for candles/trending, so TP-030 should persist provider-neutral identity using provider name, symbol, optional metadata, and original response source; richer provider-symbol identity can be future work rather than blocking cache-aside behavior. | Records future-work boundary before endpoint behavior changes. | `src/ATrade.MarketData/MarketDataModels.cs`, `src/ATrade.MarketData.Timescale/TimescaleMarketDataModels.cs` |
| `ATrade.Api` now references `ATrade.MarketData.Timescale` and calls `AddTimescaleMarketDataPersistence(builder.Configuration)`, which uses the TP-029 default `ConnectionStrings:timescaledb` guardrail. | Step 1 API registration item complete; compile verification remains in Step 1 targeted tests. | `src/ATrade.Api/ATrade.Api.csproj`, `src/ATrade.Api/Program.cs` |
| Added `TimescaleCachedMarketDataService` as a provider-neutral `IMarketDataService` decorator over the concrete provider-backed `MarketDataService`; `ATrade.Api` only resolves `IMarketDataService`, and no endpoint handler gained provider-specific database/provider logic. `dotnet build src/ATrade.Api/ATrade.Api.csproj --nologo --verbosity minimal` succeeded after registration. | Step 1 cache-aware composition item complete; route-level cache-hit semantics are covered by later Step 2/3 items. | `src/ATrade.MarketData.Timescale/TimescaleCachedMarketDataService.cs`, `src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs`, `src/ATrade.Api/Program.cs` |
| `TimescaleCachedMarketDataService` initializes schema once via a guarded semaphore before cache reads/writes, retries after failed initialization, and catches `TimescaleMarketDataStorageUnavailableException` so storage outages skip cache reads/writes while provider responses/errors continue to flow. | Step 1 schema/unavailable item complete; later tests exercise cache and fallback paths. | `src/ATrade.MarketData.Timescale/TimescaleCachedMarketDataService.cs` |
| Freshness is consumed through the typed `TimescaleMarketDataOptions` singleton created by `AddTimescaleMarketDataPersistence`; cache reads compute `timeProvider.GetUtcNow() - options.CacheFreshnessPeriod`, preserving the TP-029 `.env`/configuration override for `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`. | Step 1 freshness option item complete. | `src/ATrade.MarketData.Timescale/TimescaleMarketDataServiceCollectionExtensions.cs`, `src/ATrade.MarketData.Timescale/TimescaleCachedMarketDataService.cs` |
| Targeted Step 1 verification passed: `dotnet build src/ATrade.Api/ATrade.Api.csproj --nologo --verbosity minimal` succeeded, and `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passed 20/20. | Step 1 targeted build/tests complete. | `src/ATrade.Api/ATrade.Api.csproj`, `tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 16:30 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 16:30 | Step 0 started | Dependency preflight and data-path plan |
| 2026-04-30 16:31 | TP-028 dependency confirmed | TP-028 STATUS is complete; scanner request regression asserts POST JSON, positive content length, no chunked transfer, and safe `411` mapping. |
| 2026-04-30 16:32 | TP-029 dependency confirmed | TP-029 STATUS is complete; Timescale test project passed 20/20 and exposes schema, repository, connection, unavailable-state, and freshness option contracts. |
| 2026-04-30 16:33 | Cache-aside plan recorded | Documented Timescale-first/decorator composition, source-agnostic fresh reads, provider miss writes, indicator reuse of cached candles, storage-unavailable fallback, and stale-data rejection. |
| 2026-04-30 16:33 | Step 0 completed | Dependencies and data-path plan confirmed before endpoint behavior changes. |
| 2026-04-30 16:34 | Step 1 started | Compose Timescale module, cache-aware service, schema initialization, freshness options, and targeted composition tests. |
| 2026-04-30 16:35 | Timescale API registration added | API project references Timescale persistence module and registers it from configuration using the default `timescaledb` connection name. |
| 2026-04-30 16:38 | Cache-aware service decorator added | `TimescaleCachedMarketDataService` composes provider-backed `MarketDataService`, Timescale repository/initializer/options, and is registered as the final API `IMarketDataService`; API project build succeeded. |
| 2026-04-30 16:39 | Schema initialization/fallback implemented | Cache service now initializes Timescale schema idempotently before reads/writes and falls back to provider behavior when Timescale storage is unavailable. |
| 2026-04-30 16:39 | Freshness option wired | Cache service now uses typed Timescale options for freshness cutoffs, preserving `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` configuration. |
| 2026-04-30 16:54 | Worker iter 1 | done in 1468s, tools: 77 |
| 2026-04-30 17:04 | Step 1 targeted verification passed | API project build succeeded and Timescale market-data tests passed 20/20. |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
