# Task: TP-033 - Fix LEAN Aspire runtime wiring and dashboard resource

**Created:** 2026-04-30
**Size:** L

## Review Level: 2 (Plan and Code)

**Assessment:** This fixes the optional LEAN runtime path across AppHost, API configuration, the LEAN provider, tests, and docs. It adds an optional container/runtime integration but does not touch auth, broker credentials, or order placement.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-033-lean-aspire-runtime-wiring/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Fix the LEAN analysis engine startup path so a local `start run` session can actually use the configured LEAN runtime and, when Docker mode is selected, the LEAN runtime is represented as an Aspire dashboard resource. The committed default must remain disabled (`ATRADE_ANALYSIS_ENGINE=none`), but ignored `.env` settings such as `ATRADE_ANALYSIS_ENGINE=Lean` and `ATRADE_LEAN_RUNTIME_MODE=docker` must flow from the repo-local startup contract into `ATrade.Api`, register the LEAN provider, and expose a visible `lean-engine` (or explicitly documented equivalent) resource in the AppHost graph without introducing live trading or broker/order side effects.

## Dependencies

- **None**

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite. Do **not** read, print, or commit the ignored repo-root `.env` file.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/analysis-engines.md` — current provider-neutral LEAN runtime contract
- `docs/architecture/paper-trading-workspace.md` — no-real-orders and analysis panel contract
- `docs/architecture/modules.md` — AppHost/API/Analysis module responsibilities
- `docs/architecture/overview.md` — AppHost graph summary
- `scripts/README.md` — repo-local `.env` and `start run` contract
- `.env.template` — committed LEAN placeholders only; never read ignored `.env`
- `src/ATrade.AppHost/Program.cs` — Aspire resource graph and project env wiring
- `src/ATrade.AppHost/PaperTradingEnvironmentContract.cs` — pattern for reading merged `.env.template`/`.env` values without committing secrets
- `src/ATrade.Analysis.Lean/*` — LEAN runtime options, executor, workspace, and guardrails
- `src/ATrade.Api/Program.cs` — analysis provider registration and endpoints
- `tests/ATrade.Analysis.Lean.Tests/*` — LEAN provider test patterns
- `tests/apphost/lean-analysis-engine-tests.sh` — current LEAN source/contract verification
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` — AppHost manifest assertion style
- `tests/start-contract/start-wrapper-tests.sh` — `start run` env-loading contract if wrapper behavior changes

## Environment

- **Workspace:** Repository root
- **Services required:** Automated tests must not require real IBKR credentials or a live trading account. Docker/Podman or the official LEAN runtime may be used only for optional runtime smoke tests that cleanly skip when unavailable. Manifest/configuration tests should run without starting containers.

## File Scope

> The orchestrator uses this to avoid merge conflicts. Keep changes inside this scope unless `STATUS.md` records a discovered prerequisite.

- `.env.template`
- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.AppHost/PaperTradingEnvironmentContract.cs` (only if shared local-contract parsing is extended)
- `src/ATrade.AppHost/LeanAnalysisRuntimeContract.cs` (new, or equivalent)
- `src/ATrade.Analysis.Lean/LeanAnalysisEnvironmentVariables.cs`
- `src/ATrade.Analysis.Lean/LeanAnalysisOptions.cs`
- `src/ATrade.Analysis.Lean/LeanRuntimeExecution.cs`
- `src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs`
- `src/ATrade.Analysis.Lean/LeanModuleServiceCollectionExtensions.cs` (only if registration/unavailable semantics change)
- `src/ATrade.Api/Program.cs` (only if API config/registration must change)
- `tests/ATrade.Analysis.Lean.Tests/*`
- `tests/apphost/lean-aspire-runtime-tests.sh` (new)
- `tests/apphost/lean-analysis-engine-tests.sh`
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (only if shared manifest helpers are updated)
- `tests/start-contract/start-wrapper-tests.sh` (only if startup env loading changes)
- `docs/architecture/analysis-engines.md`
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `scripts/README.md`
- `README.md` (only if runtime-surface wording changes)
- `tasks/TP-033-lean-aspire-runtime-wiring/STATUS.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Diagnose current LEAN startup gap

- [ ] Inspect the current `start run`/AppHost path and record whether LEAN `.env` values reach `ATrade.Api`
- [ ] Publish or inspect the AppHost manifest with LEAN disabled and with temporary LEAN Docker-mode values, and record why no LEAN resource currently appears in the Aspire dashboard
- [ ] Choose and record the final Aspire resource name (prefer `lean-engine`) and runtime execution strategy in `STATUS.md`
- [ ] Confirm the default committed configuration still disables LEAN and creates no LEAN runtime container

**Artifacts:**
- `tasks/TP-033-lean-aspire-runtime-wiring/STATUS.md` (modified)

### Step 1: Wire LEAN configuration into the AppHost graph

- [ ] Add an AppHost-side LEAN runtime contract reader (or equivalent) that reads the same merged local contract as other `start run` settings without reading or printing ignored `.env` values
- [ ] Explicitly pass all safe LEAN settings needed by `ATrade.Api` (`ATRADE_ANALYSIS_ENGINE`, runtime mode, CLI/docker command/image, workspace root, timeout, keep-workspace, and any new managed-container settings) from AppHost to the `api` project resource
- [ ] Keep committed defaults disabled and ensure no broker credentials, account identifiers, tokens, or cookies are added to LEAN env variables
- [ ] Add manifest/config tests proving disabled defaults omit the LEAN resource but still preserve analysis no-engine behavior
- [ ] Run targeted build/tests for AppHost/API configuration wiring

**Artifacts:**
- `src/ATrade.AppHost/Program.cs` (modified)
- `src/ATrade.AppHost/LeanAnalysisRuntimeContract.cs` (new, or equivalent)
- `.env.template` (modified only if new non-secret LEAN settings are introduced)
- `tests/apphost/lean-aspire-runtime-tests.sh` (new)

### Step 2: Add an Aspire-visible LEAN Docker runtime resource

- [ ] When `ATRADE_ANALYSIS_ENGINE=Lean` and `ATRADE_LEAN_RUNTIME_MODE=docker`, declare an Aspire-managed LEAN runtime resource using the configured official LEAN image (`ATRADE_LEAN_DOCKER_IMAGE`)
- [ ] Make the resource visible in the Aspire dashboard with a stable name such as `lean-engine`, and preserve disabled-by-default behavior
- [ ] Provide a safe shared workspace mount/volume strategy so analysis workspaces created by `ATrade.Api` can be executed by the managed LEAN runtime without exposing secrets
- [ ] Apply the same local container safeguards used elsewhere where applicable (for example process limits), and do not require IBKR/iBeam credentials
- [ ] Add manifest assertions for resource name, image, workspace mount/volume, and API env handoff using temporary test `.env` values

**Artifacts:**
- `src/ATrade.AppHost/Program.cs` (modified)
- `src/ATrade.AppHost/LeanAnalysisRuntimeContract.cs` (modified/new)
- `tests/apphost/lean-aspire-runtime-tests.sh` (modified)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (modified only if shared helpers are reused)

### Step 3: Make the LEAN executor use the managed runtime safely

- [ ] Extend `LeanAnalysisOptions` and environment variable bindings for any managed-container execution metadata required by Step 2 (for example container name and container workspace root), while keeping CLI mode unchanged
- [ ] Update Docker-mode execution so it can run analysis in the AppHost-managed runtime (for example through a stable container name and shared workspace mapping) or fail as `analysis-engine-unavailable` with a clear message when the managed runtime is not available
- [ ] Preserve current `docker run` or CLI fallback only if it is explicitly documented and tested; do not claim the dashboard resource is used when it is not
- [ ] Keep no-order guardrails intact: no `MarketOrder`, brokerage model, live mode, or `/api/orders` calls in generated analysis code
- [ ] Add/update unit tests for option binding, command construction/execution strategy, unavailable runtime handling, timeout handling, and no-order guardrails
- [ ] Run targeted LEAN provider tests

**Artifacts:**
- `src/ATrade.Analysis.Lean/LeanAnalysisEnvironmentVariables.cs` (modified)
- `src/ATrade.Analysis.Lean/LeanAnalysisOptions.cs` (modified)
- `src/ATrade.Analysis.Lean/LeanRuntimeExecution.cs` (modified if needed)
- `src/ATrade.Analysis.Lean/LeanRuntimeExecutor.cs` (modified)
- `tests/ATrade.Analysis.Lean.Tests/*` (modified/new)

### Step 4: Verify API behavior and optional runtime smoke

- [ ] Extend `tests/apphost/lean-aspire-runtime-tests.sh` so a temporary LEAN-enabled contract proves `GET /api/analysis/engines` returns the LEAN engine when AppHost passes configuration into API
- [ ] If a Docker-compatible runtime and the configured LEAN image are available, run a bounded `POST /api/analysis/run` smoke with direct request bars; otherwise skip with a clear message
- [ ] Ensure unavailable runtime responses are explicit `analysis-engine-unavailable` failures, not fake successful signals
- [ ] Update `tests/apphost/lean-analysis-engine-tests.sh` so it covers the new managed-runtime contract and still verifies provider-neutral boundaries
- [ ] Run targeted AppHost/LEAN verification scripts

**Artifacts:**
- `tests/apphost/lean-aspire-runtime-tests.sh` (new/modified)
- `tests/apphost/lean-analysis-engine-tests.sh` (modified)
- `tests/ATrade.Analysis.Lean.Tests/*` (modified/new)

### Step 5: Testing & Verification

> ZERO unexpected test failures allowed. Runtime-dependent checks must pass or cleanly skip according to existing contracts.

- [ ] Run `dotnet test tests/ATrade.Analysis.Lean.Tests/ATrade.Analysis.Lean.Tests.csproj --nologo --verbosity minimal`
- [ ] Run `bash tests/apphost/lean-analysis-engine-tests.sh`
- [ ] Run `bash tests/apphost/lean-aspire-runtime-tests.sh`
- [ ] Run `bash tests/apphost/analysis-engine-contract-tests.sh`
- [ ] Run `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run solution build: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures or record pre-existing unrelated failures with evidence in `STATUS.md`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs describe how LEAN is selected, how its AppHost/Docker resource appears, and what safe unavailable states look like
- [ ] "Check If Affected" docs reviewed and updated only where relevant
- [ ] `STATUS.md` Discoveries record the original root cause, final resource name, runtime strategy, and any local setup caveats

## Documentation Requirements

**Must Update:**
- `docs/architecture/analysis-engines.md` — document AppHost-managed LEAN runtime selection, dashboard resource behavior, and unavailable-state semantics
- `scripts/README.md` — document the local `.env` settings required for LEAN Docker mode and dashboard visibility
- `docs/architecture/modules.md` — update AppHost/API/Analysis.Lean module responsibilities if runtime ownership changes

**Check If Affected:**
- `.env.template` — update only if new non-secret LEAN runtime settings are introduced
- `docs/architecture/paper-trading-workspace.md` — update if the analysis panel/runtime status wording changes
- `docs/architecture/overview.md` — update if the AppHost graph summary changes
- `README.md` — update if current runtime surface wording changes
- `docs/INDEX.md` — update only if new active docs are introduced

## Completion Criteria

- [ ] With committed defaults, LEAN remains disabled and no LEAN runtime container starts
- [ ] With ignored `.env` selecting `ATRADE_ANALYSIS_ENGINE=Lean` and Docker mode, AppHost passes LEAN settings into `ATrade.Api`
- [ ] The Aspire graph/manifest includes a visible LEAN runtime resource using the configured LEAN image
- [ ] `GET /api/analysis/engines` reports the LEAN provider only when selected
- [ ] `POST /api/analysis/run` either runs through the configured official runtime or returns an explicit unavailable error; it never returns fake success
- [ ] Tests prove provider-neutral API/frontend contracts and no-order/no-live-trading guardrails remain intact

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `fix(TP-033): complete Step N — description`
- **Bug fixes:** `fix(TP-033): description`
- **Tests:** `test(TP-033): description`
- **Hydration:** `hydrate: TP-033 expand Step N checkboxes`

## Do NOT

- Read, print, or commit ignored `.env` values, credentials, account identifiers, session cookies, or tokens
- Enable LEAN by default in committed configuration
- Add real order placement, live-trading behavior, brokerage routing, or LEAN live mode
- Claim the Aspire dashboard resource is used by analysis unless tests prove the execution path uses it
- Break CLI mode or no-engine fallback behavior
- Skip tests or commit without the task ID prefix

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
