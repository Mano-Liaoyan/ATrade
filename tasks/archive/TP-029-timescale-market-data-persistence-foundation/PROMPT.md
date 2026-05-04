# Task: TP-029 - Add TimescaleDB market-data persistence foundation

**Created:** 2026-04-30
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This adds a new Timescale-backed persistence module, schema, configuration option, tests, and docs while avoiding endpoint behavior changes until the dependent cache-aside task. It introduces a durable data model, so reversibility is medium even though the implementation should follow existing Postgres module patterns.
**Score:** 4/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 2

## Canonical Task Folder

```text
tasks/TP-029-timescale-market-data-persistence-foundation/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Create the backend foundation for persisting provider market data in the AppHost-managed TimescaleDB resource. This task should add the schema/repository/options needed to store and query fresh provider-backed market-data rows, but it must not yet change `/api/market-data/*` endpoint behavior; TP-030 will wire the API cache-aside flow on top of this foundation.

## Dependencies

- **None**

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite. Do **not** read, print, or commit the ignored repo-root `.env` file.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/paper-trading-workspace.md` — TimescaleDB ownership and market-data storage expectations
- `docs/architecture/modules.md` — module boundaries and persistence responsibilities
- `docs/architecture/overview.md` — AppHost resource graph and infrastructure summary
- `docs/architecture/provider-abstractions.md` — provider-neutral market-data payload shapes that persistence must not leak through
- `scripts/README.md` — `.env` contract and AppHost startup variables
- `.env.template` — committed default for the market-data freshness period (template only; never read ignored `.env`)
- `src/ATrade.AppHost/Program.cs` — existing `timescaledb` AppHost resource and API reference
- `src/ATrade.Workspaces/*` — existing Postgres schema/repository/options/test patterns to adapt, not copy blindly
- `src/ATrade.MarketData/MarketDataModels.cs` and `MarketDataProviderModels.cs` — record shapes to persist
- `tests/ATrade.Workspaces.Tests/*` — SQL-shape test style
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` — TimescaleDB manifest expectations

## Environment

- **Workspace:** Repository root
- **Services required:** Unit/source tests must not require a running TimescaleDB instance. Any optional integration script that starts TimescaleDB must cleanly skip when Docker/Podman-compatible runtime is unavailable.

## File Scope

> The orchestrator uses this to avoid merge conflicts. Keep changes inside this scope unless `STATUS.md` records a discovered prerequisite.

- `src/ATrade.MarketData.Timescale/ATrade.MarketData.Timescale.csproj` (new)
- `src/ATrade.MarketData.Timescale/*` (new)
- `tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj` (new)
- `tests/ATrade.MarketData.Timescale.Tests/*` (new)
- `tests/apphost/market-data-timescale-persistence-tests.sh` (new, optional Docker/Timescale integration check)
- `ATrade.slnx`
- `ATrade.sln` (only if compatibility tooling requires it; `ATrade.slnx` remains authoritative)
- `.env.template`
- `scripts/README.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `docs/architecture/provider-abstractions.md` (only if provider contract wording changes)
- `README.md` (only if current runtime surface wording changes)
- `tasks/TP-029-timescale-market-data-persistence-foundation/STATUS.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight and scope boundary

- [ ] Confirm the AppHost already declares a dedicated `timescaledb` resource and passes it to `ATrade.Api`
- [ ] Confirm current market-data endpoints do not persist IBKR scanner/candle/snapshot data in TimescaleDB
- [ ] Record the chosen boundary in `STATUS.md`: this task creates persistence/options only; TP-030 changes API cache-aside behavior

**Artifacts:**
- `tasks/TP-029-timescale-market-data-persistence-foundation/STATUS.md` (modified)

### Step 1: Add configurable market-data freshness options

- [ ] Add a committed `.env.template` variable named `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` with default `30`
- [ ] Add a typed options/configuration model in the new Timescale module that reads the freshness period from configuration/environment and validates it as a positive `TimeSpan`
- [ ] Make the default freshness period 30 minutes when no explicit value is configured, matching the user-requested behavior
- [ ] Add unit tests for default, configured, invalid, and boundary freshness values without reading ignored `.env`
- [ ] Document that this value controls whether API market-data cache-aside reads may use Timescale rows directly or must refresh from the provider

**Artifacts:**
- `.env.template` (modified)
- `src/ATrade.MarketData.Timescale/*Options*.cs` (new)
- `tests/ATrade.MarketData.Timescale.Tests/*Options*Tests.cs` (new)
- `scripts/README.md` (modified)

### Step 2: Create Timescale schema and repository contracts

- [ ] Create `src/ATrade.MarketData.Timescale` with a narrow dependency on Npgsql/Timescale-compatible Postgres protocol APIs; do not introduce a second database runtime
- [ ] Add idempotent schema initialization for an `atrade_market_data` schema with hypertable-ready tables for OHLCV candles and provider scanner/trending snapshots, including provider, provider symbol id, symbol, exchange, currency, asset class, timeframe/source, observed/generated timestamps, and write timestamps
- [ ] Add repository methods to upsert/read fresh candle series and trending snapshots by provider/source/symbol/timeframe within a caller-provided freshness cutoff
- [ ] Keep repository contracts provider-neutral and store IBKR identifiers as provider metadata, not as API/frontend-only types
- [ ] Add SQL-shape/unit tests that assert schema/table names, freshness predicates, upsert conflict keys, and no accidental use of the regular Postgres watchlist connection name

**Artifacts:**
- `src/ATrade.MarketData.Timescale/ATrade.MarketData.Timescale.csproj` (new)
- `src/ATrade.MarketData.Timescale/TimescaleMarketDataSchemaInitializer.cs` (new or equivalent)
- `src/ATrade.MarketData.Timescale/TimescaleMarketDataRepository.cs` (new or equivalent)
- `src/ATrade.MarketData.Timescale/TimescaleMarketDataSql.cs` (new or equivalent)
- `src/ATrade.MarketData.Timescale/TimescaleMarketDataModels.cs` (new or equivalent)
- `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataSqlTests.cs` (new or equivalent)
- `tests/ATrade.MarketData.Timescale.Tests/TimescaleMarketDataRepositoryTests.cs` (new or equivalent)

### Step 3: Add composition and optional integration verification hooks

- [ ] Add service-registration extensions for the Timescale module that use `ConnectionStrings:timescaledb` and fail safely with a clear storage-unavailable error when the connection is absent or unreachable
- [ ] Add the new source and test projects to `ATrade.slnx`; update `ATrade.sln` only if existing compatibility tooling requires it
- [ ] Create an optional `tests/apphost/market-data-timescale-persistence-tests.sh` script or equivalent focused verification that initializes the schema and round-trips fake market-data rows against TimescaleDB when a container runtime is available, and skips cleanly otherwise
- [ ] Ensure this task does not register a cache-aside decorator into `ATrade.Api`; endpoint behavior changes belong to TP-030
- [ ] Run targeted build/tests for the new module

**Artifacts:**
- `src/ATrade.MarketData.Timescale/*ServiceCollectionExtensions.cs` (new)
- `tests/apphost/market-data-timescale-persistence-tests.sh` (new if integration script is feasible)
- `ATrade.slnx` (modified)
- `ATrade.sln` (modified only if necessary)

### Step 4: Testing & Verification

> ZERO unexpected test failures allowed. Runtime-dependent checks must pass or cleanly skip according to existing contracts.

- [ ] Run `dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj --nologo --verbosity minimal`
- [ ] Run `dotnet build src/ATrade.MarketData.Timescale/ATrade.MarketData.Timescale.csproj --nologo --verbosity minimal`
- [ ] If added, run `bash tests/apphost/market-data-timescale-persistence-tests.sh`
- [ ] Run `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run solution build: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures or record pre-existing unrelated failures with evidence in `STATUS.md`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs describe TimescaleDB as the market-data persistence foundation and document `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`
- [ ] "Check If Affected" docs reviewed and updated only where relevant
- [ ] `STATUS.md` Discoveries record schema choices, freshness option behavior, and why API endpoint behavior is deferred to TP-030

## Documentation Requirements

**Must Update:**
- `.env.template` — add the market-data cache freshness setting with a safe default of 30 minutes
- `scripts/README.md` — document the new `.env` variable and clarify it is non-secret
- `docs/architecture/paper-trading-workspace.md` — update TimescaleDB current-state/foundation wording for persisted market data
- `docs/architecture/modules.md` — add/update `ATrade.MarketData.Timescale` module responsibility

**Check If Affected:**
- `docs/architecture/overview.md` — update if the infrastructure/current module summary changes
- `docs/architecture/provider-abstractions.md` — update only if persistence affects provider-neutral payload/source language
- `README.md` — update if current runtime surface wording changes
- `docs/INDEX.md` — update only if new active docs are introduced

## Completion Criteria

- [ ] A Timescale-specific market-data persistence module exists and builds independently
- [ ] The schema can initialize idempotently and is ready to store candles and scanner/trending snapshots
- [ ] A configurable freshness period exists in `.env.template` with default 30 minutes and tests
- [ ] Tests cover SQL/freshness behavior without requiring real IBKR credentials
- [ ] No API endpoint behavior changes are made before TP-030

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-029): complete Step N — description`
- **Bug fixes:** `fix(TP-029): description`
- **Tests:** `test(TP-029): description`
- **Hydration:** `hydrate: TP-029 expand Step N checkboxes`

## Do NOT

- Read, print, or commit ignored `.env` values or broker credentials
- Change `/api/market-data/*` runtime behavior in this task; defer cache-aside wiring to TP-030
- Use the regular Postgres watchlist connection string for market-data time-series storage
- Introduce direct frontend access to TimescaleDB; the browser must continue to go through `ATrade.Api`
- Reintroduce production mock market data or hard-coded production symbol catalogs
- Skip tests or commit without the task ID prefix

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
