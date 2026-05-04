# TP-035: Persist TimescaleDB cache across application reboot and honor freshness — Status

**Current Step:** Step 6: Documentation & Delivery
**Status:** ✅ Complete
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Confirm cache persistence gap and freshness contract
**Status:** ✅ Complete

- [x] TP-034 completion and storage/test isolation pattern reviewed
- [x] Current AppHost TimescaleDB storage inspected
- [x] Existing cache-aside tests reviewed for fresh-hit/no-provider coverage
- [x] Required cross-reboot freshness behavior recorded

---

### Step 1: Add durable TimescaleDB storage to AppHost
**Status:** ✅ Complete

- [x] Persistent AppHost data volume added for `timescaledb`
- [x] Optional non-secret Timescale volume-name setting added and parsed if applicable
- [x] Stable Timescale password parameter added so a reused data volume remains accessible after full AppHost restart
- [x] Isolated test volume strategy implemented without touching developer default volume
- [x] Existing `ConnectionStrings:timescaledb` API reference preserved
- [x] Manifest assertions verify non-read-only Timescale volume mount

---

### Step 2: Add real Timescale cache persistence/freshness regression tests
**Status:** ✅ Complete

- [x] New focused Timescale persistence test proves fresh cache survives repository/service recreation
- [x] Trending and candle/indicator persistence paths covered where practical
- [x] Stale-data/provider-unavailable case covered
- [x] Fake time/provider call counters prevent real IBKR/iBeam calls
- [x] Container-backed integration script updated if needed and skips cleanly

---

### Step 3: Add full AppHost Timescale cache reboot coverage
**Status:** ✅ Complete

- [x] New AppHost Timescale cache volume test starts with isolated temp ports/volume
- [x] Test seeds or obtains cache row, restarts full AppHost, and verifies `timescale-cache:*` API response
- [x] Test proves no live IBKR/iBeam credential dependency and no stale-as-fresh success
- [x] Test cleanup touches only temporary resources
- [x] Targeted AppHost/Timescale tests run

---

### Step 4: Preserve cache-aside semantics and API compatibility
**Status:** ✅ Complete

- [x] Fresh cache hits keep honest `timescale-cache:{source}` metadata
- [x] Missing/stale rows still refresh provider and persist when provider available
- [x] Stale rows are not served as current when provider refresh fails
- [x] Frontend remains behind `ATrade.Api` only
- [x] Frontend tests updated only if user-facing copy changes

---

### Step 5: Testing & Verification
**Status:** ✅ Complete

- [x] `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passing
- [x] `bash tests/apphost/market-data-timescale-persistence-tests.sh` passing or cleanly skipped
- [x] `bash tests/apphost/apphost-timescale-cache-volume-tests.sh` passing or cleanly skipped
- [x] `bash tests/apphost/market-data-feature-tests.sh` passing
- [x] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` passing
- [x] `bash tests/apphost/apphost-infrastructure-runtime-tests.sh` passing or cleanly skipped
- [x] `bash tests/apphost/paper-trading-config-contract-tests.sh` passing if `.env.template` changes
- [x] FULL test suite passing: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [x] Solution build passing: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [x] All failures fixed or unrelated pre-existing failures documented

---

### Step 6: Documentation & Delivery
**Status:** ✅ Complete

- [x] "Must Update" docs modified
- [x] "Check If Affected" docs reviewed
- [x] Discoveries logged with root cause, volume name/override behavior, freshness semantics, and cleanup caveats

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| TP-034 has a `.DONE` marker and all Status step checkboxes complete; its AppHost storage pattern adds `WithDataVolume(storageContract.PostgresDataVolumeName, isReadOnly: false)` to Postgres, parses `ATRADE_POSTGRES_DATA_VOLUME` via `AppHostStorageContract`, preserves stable `ATRADE_POSTGRES_PASSWORD`, and uses isolated `atrade-postgres-*-test-*` volumes in manifest/runtime reboot scripts with cleanup limited to those temporary volumes. | Reuse the same configurable named-volume/test-isolation approach for TimescaleDB and avoid touching developer default volumes. | `tasks/TP-034-apphost-postgres-watchlist-persistence/.DONE`, `src/ATrade.AppHost/AppHostStorageContract.cs`, `tests/apphost/apphost-postgres-watchlist-volume-tests.sh` |
| AppHost currently declares `timescaledb` as `builder.AddPostgres("timescaledb").WithImage("timescale/timescaledb", "latest-pg17").WithContainerRuntimeArgs("--pids-limit", safeInfraContainerPidsLimit).WithEnvironment("TS_TUNE_MEMORY", "512MB").WithEnvironment("TS_TUNE_NUM_CPUS", "2")`; unlike Postgres, it has no `WithDataVolume(...)`, bind mount, or configurable stable password. | Confirms the Timescale cache reboot persistence gap and drives Step 1 storage contract changes. | `src/ATrade.AppHost/Program.cs` |
| Existing cache-aside unit tests prove fresh trending snapshots/candles/indicator reads call the fake repository before the provider and keep provider call counters at zero; they also cover fake in-memory service-instance recreation for trending. Existing container integration only round-trips repository rows and does not recreate the real repository/cache service or reboot AppHost. | Step 2 should add real Timescale repository/service recreation coverage for trending and candles, including stale/provider-unavailable behavior. | `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataCacheAsideTests.cs`, `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataIntegrationTests.cs` |
| Required TP-035 behavior: Timescale rows for trending snapshots and candle series must be durable across full `start run`/AppHost stop-start cycles. If `generated_at >= now - ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` (default `30`, positive minutes only), API reads must return provider-neutral `timescale-cache:{originalSource}` payloads without invoking IBKR/iBeam; once rows are stale or missing, the provider refresh path must run and persist successful responses, while provider-not-configured/unavailable/authentication-required failures must not serve stale rows as current. | Implementation and tests must verify post-reboot fresh hits, provider call avoidance, stale miss behavior, and frontend access through `ATrade.Api` only. | `docs/architecture/paper-trading-workspace.md`, `docs/architecture/provider-abstractions.md`, `src/ATrade.MarketData.Timescale/TimescaleMarketDataOptions.cs` |
| Primary AppHost `timescaledb` now uses an explicit writable Aspire data volume before preserving the existing `--pids-limit` runtime arg and `TS_TUNE_*` safeguards. | Implemented in Step 1. | `src/ATrade.AppHost/Program.cs` |
| Added non-secret `ATRADE_TIMESCALEDB_DATA_VOLUME` storage contract parsing with default `atrade-timescaledb-data`; environment variables override `.env`/`.env.template`, and invalid Timescale volume names fail fast with the Timescale variable name. | Enables developer override and isolated AppHost reboot tests without touching the default Timescale cache volume. | `.env.template`, `src/ATrade.AppHost/AppHostStorageContract.cs` |
| Added stable secret `timescaledb-password` parameter loaded from `ATRADE_TIMESCALEDB_PASSWORD` (fake template default `ATRADE_TIMESCALEDB_PASSWORD`) because a persisted Postgres/Timescale data directory rejects a newly generated password after a full AppHost restart. | Mirrors the TP-034 Postgres persistence lesson and prevents durable cache volumes from becoming inaccessible across restarts. | `.env.template`, `src/ATrade.AppHost/Program.cs`, `src/ATrade.AppHost/AppHostStorageContract.cs` |
| Manifest and runtime infrastructure tests now override AppHost TimescaleDB to isolated `atrade-timescaledb-manifest-test-*` or `atrade-timescaledb-runtime-test-*` volume/password values and runtime cleanup removes only those temporary volumes. | Tests can verify durable Timescale mounts without deleting or modifying the developer default `atrade-timescaledb-data` volume. | `tests/apphost/apphost-infrastructure-manifest-tests.sh`, `tests/apphost/apphost-infrastructure-runtime-tests.sh` |
| The API still receives the same Aspire `timescaledb` resource reference, so the manifest contract remains `ConnectionStrings__timescaledb={timescaledb.connectionString}` and downstream configuration remains `ConnectionStrings:timescaledb`. | Preserves API/Timescale data-source compatibility while adding storage. | `src/ATrade.AppHost/Program.cs`, `tests/apphost/apphost-infrastructure-manifest-tests.sh` |
| AppHost manifest assertions now parse the published JSON and verify both `postgres` and `timescaledb` mount their configured named volumes at `/var/lib/postgresql/data` with `readOnly: false`; `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` passed after the change. | Guards the durable Timescale cache volume contract at the manifest level. | `tests/apphost/apphost-infrastructure-manifest-tests.sh` |
| Added `TimescaleMarketDataRebootPersistenceTests` using the real `TimescaleMarketDataRepository`/schema initializer against `ATRADE_MARKET_DATA_TIMESCALE_TEST_CONNECTION_STRING`; fresh trending cache is written by one service/data-source provider and read as `timescale-cache:*` by a recreated service/data-source provider with the provider unavailable and call counter still zero. | Provides real Timescale persistence regression coverage for service/repository recreation. | `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataRebootPersistenceTests.cs` |
| Real Timescale reboot persistence tests cover a fresh trending snapshot path and a fresh candle path; the candle test also calls indicators after recreation so indicator inputs reuse the fresh persisted candle series without a provider call. | Satisfies trending and candle/indicator persistence coverage for Step 2. | `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataRebootPersistenceTests.cs` |
| Real Timescale stale regression writes a trending row older than the configured 5-minute freshness window, recreates the service/repository with the provider unavailable, and asserts `MarketDataProviderUnavailableException` instead of a `timescale-cache:*` success. | Guards against serving stale persisted data as fresh after reboot. | `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataRebootPersistenceTests.cs` |
| Reboot persistence tests use fixed `TimeProvider` instances and a local `RecordingMarketDataProvider` with call counters/throw-on-call flags; no IBKR/iBeam credentials, gateway URL, or network provider is used. `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passed with tests skipping when the Timescale connection string is absent. | Keeps tests deterministic and provider-local. | `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataRebootPersistenceTests.cs` |
| `market-data-timescale-persistence-tests.sh` now runs the full Timescale test project against its disposable Timescale container instead of filtering only the original integration class, so the real repository/service recreation tests execute when Docker/Podman is available and the script still skips cleanly when no engine is reachable. The script passed on this host. | Container-backed Step 2 regression entrypoint updated. | `tests/apphost/market-data-timescale-persistence-tests.sh` |
| Added `apphost-timescale-cache-volume-tests.sh` with unique loopback API/frontend ports plus isolated `ATRADE_POSTGRES_DATA_VOLUME` and `ATRADE_TIMESCALEDB_DATA_VOLUME` settings/passwords for full AppHost sessions. | Implements Step 3 AppHost runtime entrypoint without using developer default volumes or fixed ports. | `tests/apphost/apphost-timescale-cache-volume-tests.sh` |
| Full AppHost Timescale test initializes the API-owned market-data schema, seeds fresh trending and candle rows directly into the AppHost-managed TimescaleDB container, stops the full AppHost session while keeping the isolated Timescale volume, restarts with the same volume, and verifies `/api/market-data/trending` plus `/api/market-data/TPV035/candles?timeframe=1D` return `timescale-cache:*` responses. | Proves cache rows survive full AppHost/container restart and are served through `ATrade.Api`. | `tests/apphost/apphost-timescale-cache-volume-tests.sh` |
| The full AppHost test runs with `ATRADE_BROKER_INTEGRATION_ENABLED=false` and fake IBKR placeholders, first observes `provider-not-configured`, then verifies fresh seeded cache rows still serve while a deliberately stale candle row for `TPS035` returns 503 `provider-not-configured` rather than a cache success before and after reboot. | Proves no live IBKR/iBeam dependency and prevents stale-as-fresh false positives. | `tests/apphost/apphost-timescale-cache-volume-tests.sh` |
| AppHost Timescale cache volume cleanup kills only the current AppHost process, removes only containers observed after each test session starts, and removes only unique `atrade-postgres-timescale-cache-test-*` / `atrade-timescaledb-cache-volume-test-*` volumes allocated by the script. | Avoids deleting or truncating developer default Timescale cache data. | `tests/apphost/apphost-timescale-cache-volume-tests.sh` |
| Targeted Step 3 runtime check `bash tests/apphost/apphost-timescale-cache-volume-tests.sh` passed on this host and printed the isolated Timescale cache volume used. | Verifies full AppHost Timescale cache reboot coverage. | `tests/apphost/apphost-timescale-cache-volume-tests.sh` |
| Final TP-035 delivery summary: root cause was an AppHost `timescaledb` resource without a persistent data directory or stable password, so Timescale cache rows could be lost or become inaccessible across full AppHost/container restart. The fix uses `ATRADE_TIMESCALEDB_DATA_VOLUME` default `atrade-timescaledb-data` plus stable `ATRADE_TIMESCALEDB_PASSWORD`; environment variables override `.env.template`/`.env` for developer or isolated-test volumes. Fresh rows remain valid only while inside `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` and serve as `timescale-cache:{source}` through `ATrade.Api` without provider calls; stale/missing rows refresh from IBKR/iBeam or return safe provider errors. Tests remove only temporary `atrade-timescaledb-*-test-*` volumes and never remove the developer default cache volume. | Documentation and delivery notes complete. | `src/ATrade.AppHost/Program.cs`, `src/ATrade.AppHost/AppHostStorageContract.cs`, `.env.template`, `tests/apphost/apphost-timescale-cache-volume-tests.sh`, docs |
| Cache-aside source metadata remains `timescale-cache:{originalSource}` via `ToCacheSource`, and targeted Timescale/AppHost tests asserted `timescale-cache:ibkr-scanner`, `timescale-cache:ibkr-history`, and real AppHost `timescale-cache:ibkr-ibeam-*` responses. | No source metadata compatibility change required. | `src/ATrade.MarketData.Timescale/TimescaleCachedMarketDataService.cs`, `tests/ATrade.MarketData.Timescale.Tests`, `tests/apphost/apphost-timescale-cache-volume-tests.sh` |
| Missing/stale cache behavior still delegates to `providerBackedService` and calls `TryPersistTrendingSymbols` / `TryPersistCandleSeries` on successful provider responses; `TimescaleMarketDataCacheAsideTests` for provider miss/persist paths and `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passed. | Cache-aside refresh/persist semantics preserved. | `src/ATrade.MarketData.Timescale/TimescaleCachedMarketDataService.cs`, `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataCacheAsideTests.cs` |
| Stale provider-unavailable behavior is covered by fake-repository unit tests, real Timescale service/repository recreation tests, and the full AppHost reboot script; all assert provider errors rather than stale `timescale-cache:*` success. | Stale rows remain unavailable when provider refresh cannot happen. | `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataCacheAsideTests.cs`, `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataRebootPersistenceTests.cs`, `tests/apphost/apphost-timescale-cache-volume-tests.sh` |
| Frontend market-data client still calls only `/api/market-data/*` through the configured API base URL, and `market-data-feature-tests.sh` passed its static assertion that `frontend/lib/marketDataClient.ts` does not contain `timescale`. | Browser remains behind `ATrade.Api`; no direct Timescale access added. | `frontend/lib/marketDataClient.ts`, `tests/apphost/market-data-feature-tests.sh` |
| No user-facing frontend source/error copy changed for TP-035, so frontend tests did not need updates; `bash tests/apphost/market-data-feature-tests.sh` passed with existing expectations. | Frontend compatibility preserved without copy/test churn. | `tests/apphost/market-data-feature-tests.sh` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 22:39 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 22:39 | Step 0 started | Confirm cache persistence gap and freshness contract |
| 2026-05-01 | Step 0 completed | Reviewed TP-034 Postgres volume/test-isolation pattern, confirmed Timescale has no persistent AppHost data volume, reviewed current cache-aside coverage, and recorded cross-reboot freshness contract. |
| 2026-05-01 | Step 1 started | Hydrated durable Timescale storage checklist with stable password requirement discovered from TP-034's volume-backed Postgres reboot fix. |
| 2026-05-01 | Step 1 targeted checks | `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`, `dotnet build src/ATrade.AppHost/ATrade.AppHost.csproj --nologo --verbosity minimal`, and `bash tests/apphost/paper-trading-config-contract-tests.sh` passed. |
| 2026-05-01 | Step 2 started | Existing Step 2 checklist already covers real repository/service recreation, trending/candle coverage, stale-provider behavior, deterministic fakes, and container skip behavior; no hydration expansion needed. |
| 2026-05-01 | Step 2 targeted checks | `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passed (new real Timescale tests skip without env) and `bash tests/apphost/market-data-timescale-persistence-tests.sh` passed against a disposable Timescale container. |
| 2026-05-01 | Step 3 started | Existing Step 3 checklist covers isolated full AppHost runtime setup, cache seeding/restart verification, provider-disabled freshness guard, cleanup scope, and targeted tests; no hydration expansion needed. |
| 2026-05-01 | Step 3 targeted checks | `bash tests/apphost/apphost-timescale-cache-volume-tests.sh` passed, verifying fresh Timescale trending/candle cache rows and stale candle rejection across full AppHost restart with broker integration disabled. |
| 2026-05-01 | Step 4 started | Existing Step 4 checklist covers cache source metadata, refresh/persist semantics, stale-provider failure behavior, API-only frontend access, and frontend test scope; no hydration expansion needed. |
| 2026-05-01 | Step 4 targeted checks | `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` and `bash tests/apphost/market-data-feature-tests.sh` passed; no API/frontend compatibility changes required. |
| 2026-05-01 | Step 5 started | Running required verification commands in order. |
| 2026-05-01 | Step 5 check | `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passed (34 tests). |
| 2026-05-01 | Step 5 fix | Initial `market-data-timescale-persistence-tests.sh` run exposed concurrent Timescale schema initialization (`pg_namespace_nspname_index`) after broadening the script to run all project tests; added test assembly-level parallelization disablement for this DB-backed project. |
| 2026-05-01 | Step 5 check | `bash tests/apphost/market-data-timescale-persistence-tests.sh` passed against disposable TimescaleDB after disabling test parallelization. |
| 2026-05-01 | Step 5 check | `bash tests/apphost/apphost-timescale-cache-volume-tests.sh` passed, verifying AppHost reboot cache persistence with an isolated Timescale volume. |
| 2026-05-01 | Step 5 check | `bash tests/apphost/market-data-feature-tests.sh` passed (startup polling emitted transient curl connection retries before API readiness). |
| 2026-05-01 | Step 5 check | `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` passed. |
| 2026-05-01 | Step 5 check | `bash tests/apphost/apphost-infrastructure-runtime-tests.sh` cleanly skipped effective cgroup verification after verifying `postgres HostConfig.PidsLimit=2048`; script now uses isolated Timescale volume before the skip. |
| 2026-05-01 | Step 5 check | `bash tests/apphost/paper-trading-config-contract-tests.sh` passed for `.env.template` changes. |
| 2026-05-01 | Step 5 check | `dotnet test ATrade.slnx --nologo --verbosity minimal` passed (109 tests across solution test projects). |
| 2026-05-01 | Step 5 check | `dotnet build ATrade.slnx --nologo --verbosity minimal` passed with 0 warnings and 0 errors. |
| 2026-05-01 | Step 5 result | The only observed failure was the newly introduced concurrent Timescale schema initialization in the broadened container-backed script; it was fixed by disabling parallelization for the Timescale test assembly, and all required verification commands now pass or cleanly skip as expected. |
| 2026-05-01 | Step 5 completed | Required verification gate complete. |
| 2026-05-01 | Step 6 started | Updating required docs for Timescale volume persistence/freshness, reviewing affected docs, and finalizing discoveries. |
| 2026-05-01 | Step 6 docs | Must-update docs now describe AppHost volume-backed TimescaleDB cache persistence, `ATRADE_TIMESCALEDB_DATA_VOLUME` / stable `ATRADE_TIMESCALEDB_PASSWORD`, post-reboot freshness reuse, and stale/provider-unavailable semantics. |
| 2026-05-01 | Step 6 affected-docs | `.env.template` updated for TimescaleDB volume/password defaults, `README.md` and `docs/architecture/overview.md` updated for runtime-surface/storage wording, and `docs/INDEX.md` reviewed with no change needed because no new active docs were introduced. |
| 2026-05-01 | Step 6 discoveries | Final discovery summary logged with root cause, volume override/password behavior, freshness semantics, and cleanup caveats. |
| 2026-05-01 | Step 6 check | `bash tests/apphost/paper-trading-config-contract-tests.sh` passed after documentation updates. |
| 2026-04-30 23:04 | Worker iter 1 | done in 1520s, tools: 225 |
| 2026-04-30 23:04 | Task complete | .DONE created |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
