# Task: TP-019 - Introduce provider-neutral broker and market-data abstractions

**Created:** 2026-04-29
**Size:** L

## Review Level: 3 (Full)

**Assessment:** This refactors the current IBKR broker and market-data modules behind stable provider contracts before real IBKR/iBeam data replaces the mocked implementation. It spans multiple backend modules, API composition, tests, and architecture docs, but must preserve current behavior until the follow-on provider task lands.
**Score:** 6/8 — Blast radius: 2, Pattern novelty: 2, Security: 1, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-019-provider-abstractions-broker-market-data/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Create the provider-neutral seams that let ATrade switch broker and market-data providers without rewriting the API, frontend, or future analysis engine. The current IBKR broker adapter and deterministic market-data implementation should become implementations behind abstractions, not API-facing assumptions. This task is a refactor/foundation task only: keep existing endpoints working, keep mocked market data temporarily available for compatibility, and do not connect to real iBeam/IBKR data until TP-021 and TP-022.

## Dependencies

- **Task:** TP-016 (current IBKR broker adapter/status slice must exist)
- **Task:** TP-017 (current market-data API and SignalR slice must exist)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/modules.md` — current module boundaries and dependency direction
- `docs/architecture/overview.md` — runtime topology and provider-agnostic architecture rules
- `docs/architecture/paper-trading-workspace.md` — current paper workspace, mocked data, and future provider seam language
- `src/ATrade.Brokers.Ibkr/*` — current concrete IBKR broker/status implementation
- `src/ATrade.MarketData/*` — current market-data contracts, mocked implementation, and SignalR service
- `src/ATrade.Api/Program.cs` — endpoint and DI composition style
- `ATrade.sln` — project registration baseline
- `tests/ATrade.Brokers.Ibkr.Tests/*` — existing broker unit-test style
- `tests/apphost/market-data-feature-tests.sh` — current market-data shell/API contract
- `tests/scaffolding/project-shells-tests.sh` — project-shell verification pattern

## Environment

- **Workspace:** Project root
- **Services required:** None. This task must not require Postgres, iBeam, IBKR credentials, LEAN, Redis, NATS, or external market-data providers.

## File Scope

> The orchestrator uses this to avoid merge conflicts. This foundation intentionally overlaps follow-on provider tasks and must land first.

- `ATrade.sln`
- `src/ATrade.Brokers/*` (new)
- `src/ATrade.Brokers.Ibkr/*`
- `src/ATrade.MarketData/*`
- `src/ATrade.Api/ATrade.Api.csproj`
- `src/ATrade.Api/Program.cs`
- `tests/ATrade.ProviderAbstractions.Tests/*` (new)
- `tests/apphost/provider-abstraction-contract-tests.sh` (new)
- `tests/apphost/market-data-feature-tests.sh` (only if composition assertions change)
- `tests/scaffolding/project-shells-tests.sh` (only if new project expectations are centralized there)
- `docs/architecture/provider-abstractions.md` (new)
- `docs/INDEX.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `docs/architecture/paper-trading-workspace.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm current broker and market-data endpoints pass before refactoring
- [ ] Confirm no task-local implementation connects to real iBeam/IBKR data or LEAN

### Step 1: Add provider-neutral broker contracts

- [ ] Create a provider-neutral broker project such as `src/ATrade.Brokers/ATrade.Brokers.csproj` and add it to `ATrade.sln`
- [ ] Define broker contracts for provider identity, capabilities, session/status, account mode, and safe read-only market-data support without embedding IBKR-specific types in the contract surface
- [ ] Update `ATrade.Brokers.Ibkr` so the current IBKR status adapter implements the provider-neutral broker contracts while preserving `GET /api/broker/ibkr/status`
- [ ] Keep order placement out of the contract unless represented only as an explicit unsupported capability; no live-trading path is allowed
- [ ] Run targeted tests/build: `dotnet test tests/ATrade.Brokers.Ibkr.Tests/ATrade.Brokers.Ibkr.Tests.csproj --nologo --verbosity minimal && dotnet build src/ATrade.Brokers.Ibkr/ATrade.Brokers.Ibkr.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.Brokers/ATrade.Brokers.csproj` (new)
- `src/ATrade.Brokers/BrokerProvider*.cs` (new or equivalent)
- `src/ATrade.Brokers.Ibkr/*` (modified)
- `ATrade.sln` (modified)

### Step 2: Add provider-neutral market-data contracts

- [ ] Separate market-data contracts from the current concrete mocked implementation: provider identity, symbol identity, candles/bars, indicators, streaming snapshots, trending/scanner results, and search-readiness hooks should be usable by any provider
- [ ] Preserve the existing `IMarketDataService`/HTTP payload behavior for compatibility, but make it compose over a swappable provider abstraction
- [ ] Keep the current `MockMarketDataService` only as the temporary provider implementation until TP-022 removes production mocks; do not add new mocked behavior in this task
- [ ] Add contract-level handling for provider unavailable/not configured states so TP-022 can return safe errors instead of silently falling back to fake data
- [ ] Run targeted build: `dotnet build src/ATrade.MarketData/ATrade.MarketData.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.MarketData/MarketDataProvider*.cs` (new or modified)
- `src/ATrade.MarketData/MarketDataModels.cs` (modified)
- `src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs` (modified)
- `src/ATrade.MarketData/MockMarketDataService.cs` (modified only to implement the new abstraction temporarily)
- `src/ATrade.MarketData/MockMarketDataStreamingService.cs` (modified only to implement the new abstraction temporarily)

### Step 3: Wire provider composition through the API and tests

- [ ] Update API composition so endpoints depend on provider-neutral broker and market-data services rather than concrete IBKR/mock assumptions
- [ ] Add tests that prove a test provider can be swapped in without changing API endpoint code
- [ ] Add `tests/apphost/provider-abstraction-contract-tests.sh` to assert the solution contains the new provider projects/contracts and no API endpoint directly instantiates provider implementations
- [ ] Preserve existing health, accounts, broker status, order simulation, market-data HTTP, and SignalR behavior
- [ ] Run targeted tests: `dotnet test tests/ATrade.ProviderAbstractions.Tests/ATrade.ProviderAbstractions.Tests.csproj --nologo --verbosity minimal && bash tests/apphost/provider-abstraction-contract-tests.sh`

**Artifacts:**
- `src/ATrade.Api/ATrade.Api.csproj` (modified if new project references are needed)
- `src/ATrade.Api/Program.cs` (modified)
- `tests/ATrade.ProviderAbstractions.Tests/*` (new)
- `tests/apphost/provider-abstraction-contract-tests.sh` (new)
- `tests/apphost/market-data-feature-tests.sh` (modified only if assertions must follow the new composition)

### Step 4: Document the provider abstraction contract

- [ ] Create `docs/architecture/provider-abstractions.md` with required frontmatter and a concise provider-switching contract for brokers and market data
- [ ] Update `docs/INDEX.md` to index the new active document
- [ ] Update `docs/architecture/modules.md` with the new provider-neutral broker and market-data current-state notes
- [ ] Update `docs/architecture/overview.md` and `docs/architecture/paper-trading-workspace.md` so they describe real IBKR/iBeam and LEAN as plug-ins behind contracts, not as API/UI assumptions
- [ ] Update `README.md` only if the repository map/current-status text would otherwise be stale

**Artifacts:**
- `docs/architecture/provider-abstractions.md` (new)
- `docs/INDEX.md` (modified)
- `docs/architecture/modules.md` (modified)
- `docs/architecture/overview.md` (modified)
- `docs/architecture/paper-trading-workspace.md` (modified)
- `README.md` (modified if affected)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/provider-abstraction-contract-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm `apphost-infrastructure-runtime-tests.sh` passes or cleanly skips when no Docker-compatible engine is available
- [ ] Fix all failures
- [ ] Solution build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/provider-abstractions.md` — new authoritative provider-switching contract
- `docs/INDEX.md` — index the new document as active
- `docs/architecture/modules.md` — record broker and market-data abstraction boundaries
- `docs/architecture/paper-trading-workspace.md` — replace direct mock/future-provider assumptions with the new seam language

**Check If Affected:**
- `docs/architecture/overview.md` — update if runtime topology or provider-dependency direction changes
- `README.md` — update if current-status/repo-map text becomes stale
- `tests/scaffolding/project-shells-tests.sh` — update if new project shell checks are required

## Completion Criteria

- [ ] Provider-neutral broker contracts exist and the current IBKR adapter implements them
- [ ] Provider-neutral market-data contracts exist and the current mocked implementation is only a temporary provider behind the contract
- [ ] API endpoints compose through abstractions without behavior regressions
- [ ] Tests prove provider swapability and preserve existing endpoint behavior
- [ ] Active docs explain how brokers and market-data providers can be replaced without changing the API/frontend contract

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-019): complete Step N — description`
- **Bug fixes:** `fix(TP-019): description`
- **Tests:** `test(TP-019): description`
- **Hydration:** `hydrate: TP-019 expand Step N checkboxes`

## Do NOT

- Connect to real iBeam/IBKR market data in this task
- Remove the existing mocked market-data implementation before TP-022
- Add LEAN runtime dependencies or analysis behavior in this task
- Place, route, simulate as live, or imply support for real broker orders
- Commit secrets, account identifiers, tokens, or credential-like placeholders outside ignored `.env`
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
