# TP-029: Add TimescaleDB market-data persistence foundation — Status

**Current Step:** Step 4: Testing & Verification
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-30
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight and scope boundary
**Status:** ✅ Complete

- [x] Existing AppHost `timescaledb` resource and API reference confirmed
- [x] Current lack of Timescale market-data persistence confirmed
- [x] Scope boundary recorded: persistence/options now, API cache-aside in TP-030

---

### Step 1: Add configurable market-data freshness options
**Status:** ✅ Complete

- [x] `.env.template` defines `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES=30`
- [x] Typed freshness options parse and validate configured/default values
- [x] Default freshness period is 30 minutes
- [x] Freshness option tests added
- [x] Non-secret config behavior documented

---

### Step 2: Create Timescale schema and repository contracts
**Status:** ✅ Complete

- [x] New `ATrade.MarketData.Timescale` module created
- [x] Idempotent Timescale schema initialization added for candles and scanner/trending snapshots
- [x] Repository contracts can upsert/read fresh candle series and trending snapshots
- [x] Provider metadata remains provider-neutral in storage contracts
- [x] SQL-shape/unit tests cover schema, freshness predicates, conflict keys, and connection-name guardrails

---

### Step 3: Add composition and optional integration verification hooks
**Status:** ✅ Complete

- [x] Timescale service-registration extensions added for `ConnectionStrings:timescaledb`
- [x] New source/test projects added to `ATrade.slnx` and compatibility solution only if needed
- [x] Optional Timescale integration script added or explicit rationale recorded
- [x] API cache-aside behavior intentionally left untouched for TP-030
- [x] Targeted build/tests run

---

### Step 4: Testing & Verification
**Status:** ✅ Complete

- [x] `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passing
- [x] `dotnet build src/ATrade.MarketData.Timescale/ATrade.MarketData.Timescale.csproj --nologo --verbosity minimal` passing
- [x] `bash tests/apphost/market-data-timescale-persistence-tests.sh` passing or cleanly skipped if added
- [x] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` passing
- [x] FULL test suite passing: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [x] Solution build passing: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [x] All failures fixed or unrelated pre-existing failures documented

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged with schema choices, freshness behavior, and TP-030 handoff notes

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| AppHost already declares `timescaledb` as a dedicated Aspire Postgres resource using the TimescaleDB image and passes it to `ATrade.Api` via `.WithReference(timescaledb)`. | Verified as Step 0 scope input. | `src/ATrade.AppHost/Program.cs` |
| Current API market-data endpoints resolve directly through `IMarketDataService`, which delegates to the configured provider; there is no Timescale project/reference or market-data persistence path yet. | Confirms TP-029 must add persistence foundation without changing endpoint behavior. | `src/ATrade.Api/Program.cs`, `src/ATrade.MarketData/MarketDataService.cs`, `src/ATrade.Api/ATrade.Api.csproj` |
| Scope boundary: TP-029 adds Timescale schema/repository/options/composition only; TP-030 will wire `/api/market-data/*` cache-aside reads/writes and endpoint behavior changes. | Recorded in Step 0 and will be preserved in docs/delivery notes. | Task boundary |
| Freshness is represented as a positive `TimeSpan` parsed from `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`; absent/blank configuration keeps the default. | Implemented in new Timescale options model. | `src/ATrade.MarketData.Timescale/TimescaleMarketDataOptions.cs` |
| Default market-data cache freshness is exactly 30 minutes in both the committed environment template and typed options default. | Verified by source build/inspection and will be locked with unit tests. | `.env.template`, `src/ATrade.MarketData.Timescale/TimescaleMarketDataOptions.cs` |
| Freshness option tests cover absent/blank defaults, configured positive values, fractional boundary values, and invalid zero/negative/non-numeric values without loading ignored `.env`. | `dotnet test ... --filter FullyQualifiedName~TimescaleMarketDataOptionsTests` passed (10 tests). | `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataOptionsTests.cs` |
| `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` is documented as non-secret configuration for future Timescale cache-aside reads; it does not enable broker behavior or contain credentials. | Documented in local configuration contract. | `scripts/README.md` |
| New `ATrade.MarketData.Timescale` source module targets `net10.0`, references `ATrade.MarketData`, and builds independently. | `dotnet build src/ATrade.MarketData.Timescale/ATrade.MarketData.Timescale.csproj --nologo --verbosity minimal` passed. | `src/ATrade.MarketData.Timescale/ATrade.MarketData.Timescale.csproj` |
| Timescale schema initialization creates `atrade_market_data.candles` and `atrade_market_data.trending_snapshots` idempotently with Timescale hypertable calls and freshness-focused indexes. | Source build passed after adding SQL and initializer. | `src/ATrade.MarketData.Timescale/TimescaleMarketDataSql.cs`, `TimescaleMarketDataSchemaInitializer.cs` |
| Repository contract exposes upsert/read methods for fresh candle series and trending snapshots, with caller-provided freshness cutoffs and no direct API endpoint behavior changes. | Source module build passed after repository/model implementation. | `src/ATrade.MarketData.Timescale/TimescaleMarketDataRepository.cs`, `TimescaleMarketDataModels.cs` |
| Timescale storage contracts use neutral `provider`/`provider_symbol_id` metadata and do not reference IBKR-specific types, conids, frontend payload types, or API behavior. | Verified with source grep for IBKR/conid/API/frontend terms. | `src/ATrade.MarketData.Timescale/*` |
| SQL/unit coverage asserts Timescale schema shape, hypertable calls, freshness predicates, upsert conflict keys, workspace-schema avoidance, and `timescaledb` connection guardrails. | `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passed (17 tests). | `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataSqlTests.cs`, `TimescaleMarketDataRepositoryTests.cs` |
| Timescale composition extension registers options, data source provider, schema initializer, and repository against `ConnectionStrings:timescaledb`; missing connection strings surface as `TimescaleMarketDataStorageUnavailableException`. | Targeted service-registration tests passed. | `src/ATrade.MarketData.Timescale/TimescaleMarketDataServiceCollectionExtensions.cs`, `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataServiceCollectionExtensionsTests.cs` |
| New Timescale source and test projects are included in authoritative `ATrade.slnx`; compatibility `ATrade.sln` was left unchanged because no required tooling needed it. | `dotnet sln ATrade.slnx list` shows both projects. | `ATrade.slnx` |
| Optional Timescale integration script starts a local TimescaleDB container when Docker/Podman is available, initializes schema, and round-trips fake candle/trending rows; it exits 0 with SKIP when no runtime is available. | `bash tests/apphost/market-data-timescale-persistence-tests.sh` passed in this environment. | `tests/apphost/market-data-timescale-persistence-tests.sh`, `TimescaleMarketDataIntegrationTests.cs` |
| API cache-aside behavior remains deferred: no `ATrade.Api` or core `ATrade.MarketData` source/project changes reference the new Timescale module. | Verified with git diff and source grep before checking Step 3 item. | `src/ATrade.Api`, `src/ATrade.MarketData` |
| Targeted Timescale module verification passed after composition and integration-hook changes. | `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passed (20 tests); `dotnet build src/ATrade.MarketData.Timescale/ATrade.MarketData.Timescale.csproj --nologo --verbosity minimal` passed. | Timescale source/test projects |
| Step 4 Timescale test gate passed. | `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passed (20 tests). | Testing gate |
| Step 4 Timescale source build passed. | `dotnet build src/ATrade.MarketData.Timescale/ATrade.MarketData.Timescale.csproj --nologo --verbosity minimal` passed. | Testing gate |
| Step 4 optional Timescale integration hook passed with local container runtime available. | `bash tests/apphost/market-data-timescale-persistence-tests.sh` passed. | Testing gate |
| Step 4 AppHost infrastructure manifest gate passed. | `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` exited successfully. | Testing gate |
| Step 4 full solution test gate passed. | `dotnet test ATrade.slnx --nologo --verbosity minimal` passed with zero failures. | Testing gate |
| Step 4 full solution build gate passed. | `dotnet build ATrade.slnx --nologo --verbosity minimal` passed with zero warnings/errors. | Testing gate |
| No Step 4 failures remain to fix or document. | All targeted, integration, full test, and solution build commands passed. | Testing gate |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 15:13 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 15:13 | Step 0 started | Preflight and scope boundary |
| 2026-04-30 | Step 1 started | Freshness option implementation |
| 2026-04-30 | Step 2 started | Timescale schema and repository contracts |
| 2026-04-30 | Step 3 started | Composition and optional integration verification |
| 2026-04-30 | Step 4 started | Testing and verification gate |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
