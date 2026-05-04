# Task: TP-024 - Add provider-neutral analysis engine abstraction and API contract

**Created:** 2026-04-29
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This creates the analysis-engine seam that will let LEAN be the first implementation without coupling API/frontend code to LEAN-specific types. It adds a new backend module, API contracts, tests, and docs, but does not run the LEAN runtime yet.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-024-analysis-engine-abstraction/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Create a provider-neutral algorithm analysis engine boundary so ATrade can use LEAN now and switch to other analysis/backtesting engines later. This task defines the contracts, module shape, normalized request/result payloads, and API surface, but intentionally does not integrate the LEAN runtime. Runtime behavior should be explicit: if no analysis engine is configured yet, API calls return a clear `analysis-engine-not-configured` response instead of fake analysis.

## Dependencies

- **Task:** TP-019 (provider-neutral broker/market-data abstractions must exist first)
- **Task:** TP-022 (real IBKR/iBeam market-data provider must exist first)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/provider-abstractions.md` — provider abstraction language to extend for analysis engines
- `docs/architecture/paper-trading-workspace.md` — future LEAN seam language
- `docs/architecture/modules.md` — planned `ATrade.Strategies`/analysis responsibilities
- `docs/architecture/overview.md` — dependency direction and runtime-surface constraints
- `src/ATrade.MarketData/*` — normalized bars/market-data contracts to feed analysis requests
- `src/ATrade.Api/Program.cs` — endpoint/DI style
- `ATrade.sln` — project registration baseline
- `tests/scaffolding/project-shells-tests.sh` — project shell verification pattern

## Environment

- **Workspace:** Project root
- **Services required:** None. Automated tests must not require LEAN, Docker, iBeam, or real IBKR credentials. This task should only define the seam and no-engine behavior.

## File Scope

> This task lays analysis foundations. LEAN implementation follows in TP-025.

- `ATrade.sln`
- `src/ATrade.Analysis/*` (new)
- `src/ATrade.Api/ATrade.Api.csproj`
- `src/ATrade.Api/Program.cs`
- `tests/ATrade.Analysis.Tests/*` (new)
- `tests/apphost/analysis-engine-contract-tests.sh` (new)
- `tests/scaffolding/project-shells-tests.sh` (only if project-shell checks are updated)
- `docs/architecture/analysis-engines.md` (new)
- `docs/INDEX.md`
- `docs/architecture/provider-abstractions.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm no current analysis/LEAN project exists before adding the seam
- [ ] Confirm real market-data bars are available through provider-neutral contracts from TP-022

### Step 1: Create the analysis module contracts

- [ ] Create `src/ATrade.Analysis/ATrade.Analysis.csproj` and add it to `ATrade.sln`
- [ ] Define provider-neutral contracts such as `IAnalysisEngine`, `AnalysisEngineMetadata`, `AnalysisRequest`, `AnalysisResult`, `AnalysisSignal`, `AnalysisMetric`, `BacktestSummary`, and `AnalysisEngineCapabilities`
- [ ] Model market-data input using ATrade normalized bars/symbol identity, not LEAN-specific data types
- [ ] Include source/engine metadata in results so the frontend can display whether analysis came from LEAN or a future engine
- [ ] Add a no-configured-engine implementation that returns an explicit not-configured result/error; do not implement fake production analysis
- [ ] Run targeted tests/build: `dotnet test tests/ATrade.Analysis.Tests/ATrade.Analysis.Tests.csproj --nologo --verbosity minimal && dotnet build src/ATrade.Analysis/ATrade.Analysis.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.Analysis/ATrade.Analysis.csproj` (new)
- `src/ATrade.Analysis/Analysis*.cs` (new)
- `src/ATrade.Analysis/AnalysisModuleServiceCollectionExtensions.cs` (new)
- `tests/ATrade.Analysis.Tests/*` (new)
- `ATrade.sln` (modified)

### Step 2: Add analysis API contracts without LEAN runtime coupling

- [ ] Register the Analysis module in `src/ATrade.Api/Program.cs`
- [ ] Add endpoint(s), e.g. `GET /api/analysis/engines` and `POST /api/analysis/run`, using provider-neutral request/result payloads
- [ ] Make no-engine/default behavior return a clear not-configured response, not fake signals
- [ ] Ensure analysis endpoint code does not reference LEAN-specific namespaces or require LEAN packages
- [ ] Preserve existing market-data, watchlist, broker, order, health, and frontend-facing API behavior

**Artifacts:**
- `src/ATrade.Api/ATrade.Api.csproj` (modified)
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.Analysis/*` (modified)

### Step 3: Add analysis contract verification

- [ ] Create `tests/apphost/analysis-engine-contract-tests.sh`
- [ ] Verify the Analysis project exists, is in the solution, and has provider-neutral request/result contracts
- [ ] Verify API exposes analysis-engine discovery/run endpoints and returns no-engine/not-configured behavior by default
- [ ] Verify source contains no LEAN package/reference in API or core analysis contracts yet
- [ ] Run targeted tests: `bash tests/apphost/analysis-engine-contract-tests.sh`

**Artifacts:**
- `tests/apphost/analysis-engine-contract-tests.sh` (new)

### Step 4: Document the analysis engine seam

- [ ] Create `docs/architecture/analysis-engines.md` with required frontmatter and the provider-neutral analysis engine contract
- [ ] Update `docs/INDEX.md` to index the new active document
- [ ] Update `docs/architecture/provider-abstractions.md` to reference analysis engines as a separate provider family
- [ ] Update `docs/architecture/paper-trading-workspace.md` so LEAN is now the next implementation behind the analysis seam, not an API/frontend dependency
- [ ] Update `docs/architecture/modules.md` with `ATrade.Analysis` current state and future strategy/LEAN responsibilities
- [ ] Update `README.md` only if current-status wording becomes stale

**Artifacts:**
- `docs/architecture/analysis-engines.md` (new)
- `docs/INDEX.md` (modified)
- `docs/architecture/provider-abstractions.md` (modified)
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `README.md` (modified if affected)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/ibeam-runtime-contract-tests.sh && bash tests/apphost/ibkr-market-data-provider-tests.sh && bash tests/apphost/ibkr-symbol-search-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/provider-abstraction-contract-tests.sh && bash tests/apphost/postgres-watchlist-persistence-tests.sh && bash tests/apphost/analysis-engine-contract-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm Docker/iBeam-dependent runtime tests pass or cleanly skip without real credentials
- [ ] Fix all failures
- [ ] Solution build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/analysis-engines.md` — new authoritative analysis engine abstraction contract
- `docs/INDEX.md` — index the new document as active
- `docs/architecture/provider-abstractions.md` — cross-link analysis engines as a provider family
- `docs/architecture/paper-trading-workspace.md` — update LEAN seam language
- `docs/architecture/modules.md` — add/update `ATrade.Analysis` module state

**Check If Affected:**
- `README.md` — update only if current-status wording becomes stale
- `tests/scaffolding/project-shells-tests.sh` — update if new project shell checks are centralized there

## Completion Criteria

- [ ] Analysis module and provider-neutral request/result contracts exist
- [ ] API exposes analysis engine discovery/run contracts without LEAN-specific coupling
- [ ] Default no-engine behavior is explicit and not fake analysis
- [ ] Tests verify analysis contracts and API not-configured behavior
- [ ] Active docs explain how LEAN and future engines plug into the analysis seam

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-024): complete Step N — description`
- **Bug fixes:** `fix(TP-024): description`
- **Tests:** `test(TP-024): description`
- **Hydration:** `hydrate: TP-024 expand Step N checkboxes`

## Do NOT

- Add LEAN runtime/packages in this task; that is TP-025
- Return fake production analysis signals or backtest results
- Couple API or frontend contracts to LEAN-specific types
- Place orders, route trades, or add automated trading behavior
- Require real IBKR credentials, iBeam, Docker, or LEAN for automated tests
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
