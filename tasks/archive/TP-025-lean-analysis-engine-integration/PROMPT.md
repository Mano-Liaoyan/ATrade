# Task: TP-025 - Integrate LEAN as the first analysis engine provider

**Created:** 2026-04-29
**Size:** L

## Review Level: 3 (Full)

**Assessment:** This introduces the first real algorithm analysis engine integration using LEAN, adds runtime/configuration choices, wires analysis into API/frontend surfaces, and must prove the integration stays analysis-only. It is novel, multi-surface, and harder to reverse than a simple module addition.
**Score:** 6/8 — Blast radius: 2, Pattern novelty: 2, Security: 0, Reversibility: 2

## Canonical Task Folder

```text
tasks/TP-025-lean-analysis-engine-integration/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Use the open-source LEAN algorithmic trading engine (https://www.lean.io/) as ATrade's first analysis engine provider behind the TP-024 analysis abstraction. The implementation should run analysis/backtest-style evaluations over ATrade-normalized market-data bars and return provider-neutral signals/metrics to the API and frontend. LEAN must remain an analysis engine only: no brokerage routing, live trading, automatic order placement, or direct frontend dependency on LEAN-specific types.

## Dependencies

- **Task:** TP-022 (IBKR/iBeam real market-data provider must exist first)
- **Task:** TP-024 (provider-neutral analysis engine abstraction must exist first)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/analysis-engines.md` — analysis abstraction from TP-024
- `docs/architecture/provider-abstractions.md` — provider-switching contract
- `docs/architecture/paper-trading-workspace.md` — LEAN seam and no-real-trades rules
- `docs/architecture/modules.md` — Analysis/API/frontend module responsibilities
- `scripts/README.md` — `.env` and local startup contract
- `.env.template` — committed environment template
- `.env.template` — user-facing environment template from TP-021
- `src/ATrade.Analysis/*` — provider-neutral analysis contracts
- `src/ATrade.MarketData/*` and `src/ATrade.MarketData.Ibkr/*` — normalized bars/data provider
- `src/ATrade.Api/Program.cs` — analysis endpoint registration from TP-024
- `frontend/components/SymbolChartView.tsx` — symbol page integration point
- `frontend/lib/marketDataClient.ts` — frontend API-client style
- `tests/apphost/analysis-engine-contract-tests.sh` — TP-024 analysis seam verification

## Environment

- **Workspace:** Project root plus `frontend/`
- **Services required:** Automated unit/contract tests must not require live IBKR credentials. LEAN runtime integration tests may require Docker or a locally available LEAN runtime and must cleanly skip with a clear message when unavailable. Manual verification may use real `.env` IBKR data and an installed/containerized LEAN runtime.

## File Scope

> This task owns the LEAN provider implementation and first analysis UI/API integration.

- `ATrade.sln`
- `src/ATrade.Analysis/*`
- `src/ATrade.Analysis.Lean/*` (new)
- `src/ATrade.Api/ATrade.Api.csproj`
- `src/ATrade.Api/Program.cs`
- `.env.template`
- `.env.template`
- `frontend/components/AnalysisPanel.tsx` (new)
- `frontend/components/SymbolChartView.tsx`
- `frontend/lib/analysisClient.ts` (new)
- `frontend/types/analysis.ts` (new)
- `tests/ATrade.Analysis.Lean.Tests/*` (new)
- `tests/apphost/lean-analysis-engine-tests.sh` (new)
- `tests/apphost/analysis-engine-contract-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `docs/architecture/analysis-engines.md`
- `docs/architecture/provider-abstractions.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `scripts/README.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm analysis contracts exist and default to no-engine behavior from TP-024
- [ ] Confirm real market-data provider contracts expose normalized bars suitable for LEAN analysis
- [ ] Review LEAN integration options (official packages, CLI, or containerized engine) and record the selected approach in STATUS.md before implementation

### Step 1: Add LEAN provider project and runtime configuration

- [ ] Create `src/ATrade.Analysis.Lean/ATrade.Analysis.Lean.csproj`, add it to `ATrade.sln`, and reference the core Analysis project
- [ ] Integrate with the official open-source LEAN engine/runtime using a documented approach (package, CLI, or container), not a hand-written fake engine
- [ ] Add safe config placeholders to `.env.template` for selecting the analysis engine (`Lean`), LEAN workspace/runtime path or image if needed, timeout, and any non-secret local settings
- [ ] Register the LEAN provider through the TP-024 analysis engine abstraction without coupling API/frontend contracts to LEAN-specific types
- [ ] Run targeted build: `dotnet build src/ATrade.Analysis.Lean/ATrade.Analysis.Lean.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.Analysis.Lean/ATrade.Analysis.Lean.csproj` (new)
- `src/ATrade.Analysis.Lean/LeanAnalysisEngine.cs` (new or equivalent)
- `src/ATrade.Analysis.Lean/LeanAnalysisOptions.cs` (new or equivalent)
- `src/ATrade.Analysis.Lean/LeanModuleServiceCollectionExtensions.cs` (new or equivalent)
- `.env.template` (modified)
- `.env.template` (modified)
- `ATrade.sln` (modified)

### Step 2: Implement analysis-only LEAN execution over ATrade market data

- [ ] Convert ATrade normalized bars/symbol metadata into the LEAN input format selected in Step 1
- [ ] Add a minimal analysis/backtest algorithm such as moving-average crossover plus risk/return metrics that LEAN executes and returns as provider-neutral `AnalysisResult`
- [ ] Include engine/source metadata, analysis window, input symbol, metrics, and generated signals in the result
- [ ] Enforce analysis-only behavior: no brokerage model, no live order routing, no IBKR order endpoints, and no automatic trading side effects
- [ ] Add unit tests for input conversion, option validation, result parsing, timeout/error handling, and no-order guardrails
- [ ] Run targeted tests: `dotnet test tests/ATrade.Analysis.Lean.Tests/ATrade.Analysis.Lean.Tests.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.Analysis.Lean/*` (modified)
- `tests/ATrade.Analysis.Lean.Tests/*` (new)

### Step 3: Wire LEAN analysis through API and frontend

- [ ] Register the LEAN analysis provider in `src/ATrade.Api/Program.cs` when configured, while preserving no-engine/not-configured responses when LEAN is unavailable
- [ ] Update or extend analysis endpoints so users can request analysis for a symbol/timeframe using existing market-data provider bars
- [ ] Add frontend analysis client/types and an `AnalysisPanel` on the symbol chart page that can request and render LEAN-sourced signals/metrics
- [ ] Show loading, unavailable, timeout, and error states clearly; do not imply automated trading
- [ ] Run targeted frontend build: `cd frontend && npm run build`

**Artifacts:**
- `src/ATrade.Api/ATrade.Api.csproj` (modified)
- `src/ATrade.Api/Program.cs` (modified)
- `frontend/lib/analysisClient.ts` (new)
- `frontend/types/analysis.ts` (new)
- `frontend/components/AnalysisPanel.tsx` (new)
- `frontend/components/SymbolChartView.tsx` (modified)

### Step 4: Add LEAN verification

- [ ] Create `tests/apphost/lean-analysis-engine-tests.sh`
- [ ] Verify the solution contains the LEAN provider, configuration placeholders, and provider registration
- [ ] Verify API/core/frontend contracts remain provider-neutral and do not expose LEAN-specific DTOs
- [ ] Verify automated test fixtures can run the LEAN adapter path or cleanly skip when the LEAN runtime is unavailable
- [ ] Verify no order-routing, brokerage, or live-trading APIs are invoked by the analysis provider
- [ ] Update frontend trading workspace tests for the analysis panel markers
- [ ] Run targeted tests: `bash tests/apphost/lean-analysis-engine-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh`

**Artifacts:**
- `tests/apphost/lean-analysis-engine-tests.sh` (new)
- `tests/apphost/analysis-engine-contract-tests.sh` (modified if provider registration changes contract assertions)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified)

### Step 5: Update docs for LEAN analysis

- [ ] Update `docs/architecture/analysis-engines.md` with the selected LEAN integration approach, runtime/configuration contract, provider-neutral result shape, and how another engine would replace it
- [ ] Update `docs/architecture/paper-trading-workspace.md` so LEAN is an implemented analysis provider while no-real-orders guardrails remain explicit
- [ ] Update `docs/architecture/modules.md` for `ATrade.Analysis`, `ATrade.Analysis.Lean`, API, and frontend current-state notes
- [ ] Update `docs/architecture/provider-abstractions.md` with LEAN as the first analysis provider implementation
- [ ] Update `scripts/README.md` and `README.md` if startup/configuration/current-status wording becomes stale

**Artifacts:**
- `docs/architecture/analysis-engines.md` (modified)
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `docs/architecture/provider-abstractions.md` (modified)
- `scripts/README.md` (modified if affected)
- `README.md` (modified if affected)

### Step 6: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet test ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/ibeam-runtime-contract-tests.sh && bash tests/apphost/ibkr-market-data-provider-tests.sh && bash tests/apphost/ibkr-symbol-search-tests.sh && bash tests/apphost/market-data-feature-tests.sh && bash tests/apphost/provider-abstraction-contract-tests.sh && bash tests/apphost/postgres-watchlist-persistence-tests.sh && bash tests/apphost/analysis-engine-contract-tests.sh && bash tests/apphost/lean-analysis-engine-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/frontend-trading-workspace-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm Docker/iBeam/LEAN-dependent runtime tests pass or cleanly skip without required local runtimes/credentials
- [ ] Fix all failures
- [ ] Frontend build passes: `cd frontend && npm run build`
- [ ] Solution build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 7: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/analysis-engines.md` — record LEAN implementation, configuration, result shape, and replacement seam
- `docs/architecture/paper-trading-workspace.md` — update LEAN from future seam to implemented analysis provider
- `docs/architecture/modules.md` — update Analysis/LEAN/API/frontend current state
- `docs/architecture/provider-abstractions.md` — record LEAN as first analysis provider
- `.env.template` — add safe LEAN runtime placeholders if needed

**Check If Affected:**
- `scripts/README.md` — update if LEAN startup/configuration changes the local setup contract
- `README.md` — update if current-status wording becomes stale
- `docs/INDEX.md` — update only if new indexed docs are added (none expected)

## Completion Criteria

- [ ] LEAN is the first configured analysis engine provider behind `ATrade.Analysis`
- [ ] Analysis runs over ATrade-normalized market-data bars and returns provider-neutral signals/metrics
- [ ] API and frontend expose LEAN analysis without LEAN-specific DTO coupling
- [ ] Tests prove result parsing, no-order guardrails, configuration, and runtime-skip behavior
- [ ] Active docs explain how to switch to another analysis engine later

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-025): complete Step N — description`
- **Bug fixes:** `fix(TP-025): description`
- **Tests:** `test(TP-025): description`
- **Hydration:** `hydrate: TP-025 expand Step N checkboxes`

## Do NOT

- Use LEAN brokerage/order routing, live trading, or automatic order placement
- Make frontend/API payloads depend on LEAN-specific classes or namespaces
- Return fake production analysis results if LEAN is not configured
- Require real IBKR credentials or a LEAN runtime for normal unit tests
- Store secrets in LEAN config, committed templates, Postgres, localStorage, or logs
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
