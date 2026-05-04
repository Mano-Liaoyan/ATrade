# Task: TP-035 - Persist TimescaleDB cache across application reboot and honor freshness

**Created:** 2026-04-30
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This fixes durable market-data cache behavior across AppHost restarts and verifies freshness semantics through TimescaleDB, cache-aside services, API behavior, tests, and docs. It touches runtime storage plus market-data cache verification, but it does not change auth or broker/order behavior.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-035-timescale-cache-reboot-persistence/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Make the TimescaleDB-backed market-data cache persist across full application reboot and prove that fresh cache entries are served without another provider/API fetch. When a trending snapshot or candle series was persisted less than `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` ago, restarting `start run` must not force a new IBKR/iBeam provider call; `ATrade.Api` should return the Timescale cache response. Once the data is stale, the existing cache-aside behavior must refresh from the provider or return the safe provider-unavailable state when refresh cannot happen.

## Dependencies

- **Task:** TP-034 (AppHost database volume pattern and safe isolated runtime-test strategy must exist first)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite. Do **not** read, print, or commit the ignored repo-root `.env` file.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/paper-trading-workspace.md` — Timescale-first market-data read path and freshness behavior
- `docs/architecture/provider-abstractions.md` — provider/cache source metadata and unavailable-state semantics
- `docs/architecture/modules.md` — MarketData/Timescale/AppHost responsibilities
- `docs/architecture/overview.md` — AppHost infrastructure graph summary
- `scripts/README.md` — `.env`, cache freshness, and local AppHost runtime contract
- `.env.template` — committed non-secret cache defaults only; never read ignored `.env`
- `src/ATrade.AppHost/Program.cs` — current `timescaledb` resource declaration
- `src/ATrade.AppHost/AppHostStorageContract.cs` (if added by TP-034) — volume-name parsing pattern
- `src/ATrade.MarketData.Timescale/*` — cache-aside service, repository, schema, options
- `src/ATrade.MarketData/*` — provider-neutral market-data payloads
- `src/ATrade.Api/Program.cs` — market-data endpoint composition
- `tests/ATrade.MarketData.Timescale.Tests/*` — cache-aside and repository test patterns
- `tests/apphost/market-data-timescale-persistence-tests.sh` — existing Timescale integration verification
- `tests/apphost/market-data-feature-tests.sh` — API market-data behavior
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` — manifest assertion style
- `tests/apphost/apphost-infrastructure-runtime-tests.sh` — Docker runtime AppHost verification pattern

## Environment

- **Workspace:** Repository root
- **Services required:** Unit/source tests must not require real IBKR credentials. Timescale/AppHost persistence tests may require Docker/Podman and must cleanly skip when unavailable. Tests must use isolated temporary Timescale volume names and must not delete a developer's default cache volume.

## File Scope

> The orchestrator uses this to avoid merge conflicts. Keep changes inside this scope unless `STATUS.md` records a discovered prerequisite.

- `.env.template` (only if a non-secret Timescale volume-name override is introduced)
- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.AppHost/AppHostStorageContract.cs` (modified if introduced by TP-034)
- `src/ATrade.AppHost/PaperTradingEnvironmentContract.cs` (only if shared parsing is reused)
- `src/ATrade.MarketData.Timescale/*`
- `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataRebootPersistenceTests.cs` (new, or equivalent new focused test file)
- `tests/ATrade.MarketData.Timescale.Tests/*`
- `tests/apphost/apphost-timescale-cache-volume-tests.sh` (new)
- `tests/apphost/market-data-timescale-persistence-tests.sh`
- `tests/apphost/market-data-feature-tests.sh` (only if API source/error expectations change)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh`
- `tests/apphost/apphost-infrastructure-runtime-tests.sh` (only if shared helpers are updated)
- `tests/apphost/paper-trading-config-contract-tests.sh` (only if `.env.template` contract assertions change)
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/provider-abstractions.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `scripts/README.md`
- `README.md` (only if current runtime-surface wording changes)
- `tasks/TP-035-timescale-cache-reboot-persistence/STATUS.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Confirm cache persistence gap and freshness contract

- [ ] Confirm TP-034 is complete and understand the AppHost volume/test isolation pattern it introduced
- [ ] Inspect the AppHost `timescaledb` resource and confirm whether it currently has a persistent data volume or bind mount
- [ ] Review existing Timescale cache-aside tests and record which cases already prove fresh-hit/no-provider-call behavior within one process or fake repository
- [ ] Record the required cross-reboot behavior in `STATUS.md`: fresh persisted rows must survive AppHost restart and be served without provider refresh until `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` expires

**Artifacts:**
- `tasks/TP-035-timescale-cache-reboot-persistence/STATUS.md` (modified)

### Step 1: Add durable TimescaleDB storage to AppHost

- [ ] Add a persistent AppHost data volume for the `timescaledb` resource while preserving the existing image, `--pids-limit`, and `TS_TUNE_*` safeguards
- [ ] If TP-034 introduced configurable volume names, extend that contract with a non-secret Timescale default such as `ATRADE_TIMESCALEDB_DATA_VOLUME=atrade-timescaledb-data`; otherwise document and test the stable named Timescale volume
- [ ] Ensure tests can use an isolated temporary Timescale volume name without deleting or modifying a developer's default cache volume
- [ ] Keep the AppHost `api` reference to `ConnectionStrings:timescaledb` unchanged
- [ ] Add/update manifest assertions proving `timescaledb` has a non-read-only data volume mount

**Artifacts:**
- `src/ATrade.AppHost/Program.cs` (modified)
- `src/ATrade.AppHost/AppHostStorageContract.cs` (modified if applicable)
- `.env.template` (modified only if non-secret volume setting is added)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (modified)
- `tests/apphost/paper-trading-config-contract-tests.sh` (modified only if `.env.template` changes)

### Step 2: Add real Timescale cache persistence/freshness regression tests

- [ ] Create a focused new test (for example `TimescaleMarketDataRebootPersistenceTests.cs`) that uses a real Timescale repository connection when available, writes a provider response, recreates the repository/cache service, and proves a fresh read returns `timescale-cache:*` without invoking the provider
- [ ] Cover both trending snapshots and candle/indicator inputs where practical; at minimum, one trending path and one candle path must prove fresh persisted data survives service/repository recreation
- [ ] Add a stale-data case proving rows older than `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` do not get served as fresh when provider refresh is unavailable
- [ ] Keep tests deterministic with a fake `TimeProvider` and fake provider call counters; no real IBKR/iBeam credentials or network calls
- [ ] Extend `tests/apphost/market-data-timescale-persistence-tests.sh` if needed so container-backed integration tests run only when Docker/Podman is available and skip clearly otherwise

**Artifacts:**
- `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataRebootPersistenceTests.cs` (new, or equivalent)
- `tests/ATrade.MarketData.Timescale.Tests/*` (modified)
- `tests/apphost/market-data-timescale-persistence-tests.sh` (modified if needed)

### Step 3: Add full AppHost Timescale cache reboot coverage

- [ ] Create `tests/apphost/apphost-timescale-cache-volume-tests.sh` that starts AppHost with isolated temporary ports, isolated Timescale data volume, and a short positive `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`
- [ ] Seed or obtain a provider-backed trending/candle cache row through the API or Timescale repository, stop the full AppHost session, restart AppHost with the same isolated Timescale volume, and verify API market-data endpoints return a `timescale-cache:*` response while provider/iBeam is disabled or unavailable
- [ ] Prove the same test does not rely on live IBKR/iBeam credentials and does not silently pass by serving stale rows as fresh
- [ ] Clean up only temporary containers/volumes created by the test; do not remove a developer's default Timescale data volume
- [ ] Run targeted AppHost/Timescale tests

**Artifacts:**
- `tests/apphost/apphost-timescale-cache-volume-tests.sh` (new)
- `tests/apphost/market-data-feature-tests.sh` (modified only if endpoint expectations change)
- `tests/apphost/apphost-infrastructure-runtime-tests.sh` (modified only if shared helpers are reused)

### Step 4: Preserve cache-aside semantics and API compatibility

- [ ] Ensure fresh Timescale rows still return honest source metadata such as `timescale-cache:{originalSource}`
- [ ] Ensure missing/stale rows still trigger provider refresh and persistence when provider is available
- [ ] Ensure stale rows are not served as current when provider refresh fails; return the safe provider-not-configured/provider-unavailable/authentication-required error instead
- [ ] Keep frontend/browser data access behind `ATrade.Api`; do not add direct frontend-to-Timescale access
- [ ] Update frontend tests only if user-facing source/error copy changes

**Artifacts:**
- `src/ATrade.MarketData.Timescale/*` (modified only if tests expose a cache-aside bug)
- `src/ATrade.Api/Program.cs` (modified only if composition/error mapping is wrong)
- `tests/apphost/market-data-feature-tests.sh` (modified only if API expectations change)

### Step 5: Testing & Verification

> ZERO unexpected test failures allowed. Runtime-dependent checks must pass or cleanly skip according to existing contracts.

- [ ] Run `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal`
- [ ] Run `bash tests/apphost/market-data-timescale-persistence-tests.sh`
- [ ] Run `bash tests/apphost/apphost-timescale-cache-volume-tests.sh`
- [ ] Run `bash tests/apphost/market-data-feature-tests.sh`
- [ ] Run `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Run `bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Run `bash tests/apphost/paper-trading-config-contract-tests.sh` if `.env.template` changes
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run solution build: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures or record pre-existing unrelated failures with evidence in `STATUS.md`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs describe TimescaleDB volume-backed cache persistence and freshness behavior across app reboot
- [ ] "Check If Affected" docs reviewed and updated only where relevant
- [ ] `STATUS.md` Discoveries record the root cause, volume name/override behavior, cache freshness semantics, and test cleanup caveats

## Documentation Requirements

**Must Update:**
- `scripts/README.md` — document TimescaleDB cache persistence, any non-secret volume-name setting, and how freshness controls post-reboot cache reuse
- `docs/architecture/paper-trading-workspace.md` — clarify cache rows survive AppHost restart and are served only while fresh
- `docs/architecture/provider-abstractions.md` — document source/error semantics for fresh cache hits versus stale/provider-unavailable misses
- `docs/architecture/modules.md` — update `ATrade.MarketData.Timescale` and AppHost responsibilities if wording changes

**Check If Affected:**
- `.env.template` — update if a non-secret Timescale volume-name setting is added
- `docs/architecture/overview.md` — update if infrastructure graph persistence wording changes
- `README.md` — update if current runtime surface wording changes
- `docs/INDEX.md` — update only if new active docs are introduced

## Completion Criteria

- [ ] AppHost-managed `timescaledb` uses durable data storage across `start run` stop/start cycles
- [ ] Fresh persisted trending/candle rows survive AppHost reboot and are served as `timescale-cache:*` responses
- [ ] A fresh post-reboot cache hit does not invoke the provider/iBeam refresh path before `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` expires
- [ ] Stale rows are not served as current when provider refresh is unavailable
- [ ] Tests cover real Timescale persistence, service/repository recreation, AppHost reboot, and safe runtime skips
- [ ] Frontend still goes only through `ATrade.Api`; no browser direct DB access is added

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `fix(TP-035): complete Step N — description`
- **Bug fixes:** `fix(TP-035): description`
- **Tests:** `test(TP-035): description`
- **Hydration:** `hydrate: TP-035 expand Step N checkboxes`

## Do NOT

- Serve stale Timescale data as fresh when provider refresh fails
- Delete, truncate, or `docker volume rm` a developer's default Timescale data volume from tests
- Let the frontend connect directly to TimescaleDB
- Read, print, or commit ignored `.env` values, broker credentials, tokens, cookies, or account identifiers
- Reintroduce production mock market data or hard-coded production symbol catalogs
- Skip tests or commit without the task ID prefix

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
