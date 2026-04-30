# TP-029: Add TimescaleDB market-data persistence foundation — Status

**Current Step:** Step 1: Add configurable market-data freshness options
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
**Status:** ⬜ Not Started

- [ ] New `ATrade.MarketData.Timescale` module created
- [ ] Idempotent Timescale schema initialization added for candles and scanner/trending snapshots
- [ ] Repository contracts can upsert/read fresh candle series and trending snapshots
- [ ] Provider metadata remains provider-neutral in storage contracts
- [ ] SQL-shape/unit tests cover schema, freshness predicates, conflict keys, and connection-name guardrails

---

### Step 3: Add composition and optional integration verification hooks
**Status:** ⬜ Not Started

- [ ] Timescale service-registration extensions added for `ConnectionStrings:timescaledb`
- [ ] New source/test projects added to `ATrade.slnx` and compatibility solution only if needed
- [ ] Optional Timescale integration script added or explicit rationale recorded
- [ ] API cache-aside behavior intentionally left untouched for TP-030
- [ ] Targeted build/tests run

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal` passing
- [ ] `dotnet build src/ATrade.MarketData.Timescale/ATrade.MarketData.Timescale.csproj --nologo --verbosity minimal` passing
- [ ] `bash tests/apphost/market-data-timescale-persistence-tests.sh` passing or cleanly skipped if added
- [ ] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` passing
- [ ] FULL test suite passing: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Solution build passing: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] All failures fixed or unrelated pre-existing failures documented

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

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-30 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-30 15:13 | Task started | Runtime V2 lane-runner execution |
| 2026-04-30 15:13 | Step 0 started | Preflight and scope boundary |
| 2026-04-30 | Step 1 started | Freshness option implementation |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
