# Task: TP-069 - Compose runtime foundation

**Created:** 2026-05-09
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This task adds the Docker/Podman Compose infrastructure contract, shared runtime variables, helper scripts, and contract tests without changing the default `start run` path yet. It touches runtime configuration and secret-bearing environment variable plumbing, but remains reversible because Aspire-managed infrastructure is still the default until the later cutover task.
**Score:** 4/8 — Blast radius: 1, Pattern novelty: 1, Security: 1, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-069-compose-runtime-foundation/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Create the foundation for managing ATrade infrastructure containers through a repo-owned Compose file that works with Podman Compose by default and Docker Compose as a fallback. The foundation must keep the existing `.env.template` → ignored `.env` → process environment precedence, reuse the current `ATRADE_*` runtime contract, publish stable localhost ports for infrastructure, and define optional iBeam and LEAN profiles without changing the current Aspire startup behavior yet.

## Dependencies

- **None**

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `README.md` — current runtime surface and verification inventory
- `PLAN.md` — active runtime/startup direction
- `scripts/README.md` — current `start run`, local env, AppHost, and infra contracts
- `docs/architecture/overview.md` — current Aspire-managed infrastructure architecture to preserve until cutover
- `.env.template` — committed local runtime contract shape
- `src/ATrade.ServiceDefaults/LocalRuntimeContract.cs` — shared `.env` contract loader and defaults
- `src/ATrade.AppHost/Program.cs` — current AppHost container settings to mirror in Compose where needed

## Environment

- **Workspace:** repository root runtime configuration, scripts, and tests
- **Services required:** None for source/static validation. Optional `podman compose config` or `docker compose config` may be used when available; tests must skip cleanly if no Compose implementation is installed.

## File Scope

- `compose.yaml` (new)
- `.env.template`
- `src/ATrade.ServiceDefaults/LocalRuntimeContract.cs`
- `tests/ATrade.ServiceDefaults.Tests/*` (if runtime contract tests need updates)
- `tests/apphost/local-runtime-contract-module-tests.sh`
- `tests/apphost/paper-trading-config-contract-tests.sh`
- `scripts/compose-infra.sh` (new)
- `scripts/compose-infra.ps1` (new)
- `tests/compose/compose-infra-contract-tests.sh` (new)
- `scripts/README.md`
- `README.md` / `PLAN.md` (only if verification inventory or active queue references must be adjusted)
- `tasks/CONTEXT.md` (log discoveries only if needed)

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Extend the local runtime contract for Compose-managed infrastructure

- [ ] Add committed `.env.template` variables for Compose command/project selection and stable localhost infrastructure ports: `ATRADE_COMPOSE_COMMAND`, `ATRADE_COMPOSE_PROJECT_NAME`, `ATRADE_POSTGRES_PORT`, `ATRADE_TIMESCALEDB_PORT`, `ATRADE_REDIS_PORT`, and `ATRADE_NATS_PORT`
- [ ] Preserve current precedence semantics: `.env.template` defaults are loaded first, ignored `.env` overrides them, and process environment overrides both
- [ ] Extend `LocalRuntimeContract` defaults/known variables/tests so .NET code and scripts share the same values without introducing Compose-only duplicate names
- [ ] Keep database passwords and IBKR credential/account variables classified as secret; do not add real credentials or account identifiers to committed files

**Artifacts:**
- `.env.template` (modified)
- `src/ATrade.ServiceDefaults/LocalRuntimeContract.cs` (modified)
- `tests/ATrade.ServiceDefaults.Tests/*` (modified if needed)
- `tests/apphost/local-runtime-contract-module-tests.sh` (modified)
- `tests/apphost/paper-trading-config-contract-tests.sh` (modified)

### Step 2: Add the Compose infrastructure definition

- [ ] Create `compose.yaml` with `postgres`, `timescaledb`, `redis`, and `nats` services enabled by default and bound to `127.0.0.1` on the configured `ATRADE_*_PORT` values
- [ ] Preserve the existing durable data contract by mapping the `ATRADE_POSTGRES_DATA_VOLUME` and `ATRADE_TIMESCALEDB_DATA_VOLUME` named volumes to `/var/lib/postgresql/data`
- [ ] Mirror the current AppHost infra safeguards where Compose supports them: `pids_limit: 2048` for local infra containers and deterministic `TS_TUNE_MEMORY=512MB` / `TS_TUNE_NUM_CPUS=2` for TimescaleDB
- [ ] Add optional `ibkr` and `lean` profiles for `ibkr-gateway` and `lean-engine`, reusing existing `ATRADE_IBKR_*` and `ATRADE_LEAN_*` variables, iBeam inputs mount, LEAN workspace mount, stable LEAN container name, and no committed real secrets

**Artifacts:**
- `compose.yaml` (new)

### Step 3: Add reusable Compose helper scripts

- [ ] Add Unix helper `scripts/compose-infra.sh` that loads `.env.template`, overlays ignored `.env`, honors process env overrides, and runs Compose actions against `compose.yaml`
- [ ] Add PowerShell helper `scripts/compose-infra.ps1` with equivalent behavior for Windows
- [ ] Implement command selection as: use `ATRADE_COMPOSE_COMMAND` exactly when set; otherwise prefer `podman compose`; otherwise fall back to `docker compose`; otherwise fail with a clear message
- [ ] Implement automatic profile selection for `up`: enable `ibkr` only when broker integration is enabled and non-placeholder IBKR username/password values are present; enable `lean` only when `ATRADE_ANALYSIS_ENGINE=Lean` and `ATRADE_LEAN_RUNTIME_MODE=docker`
- [ ] Ensure helper `up` does not run `down` on exit and does not print secret values

**Artifacts:**
- `scripts/compose-infra.sh` (new)
- `scripts/compose-infra.ps1` (new)

### Step 4: Add contract validation

- [ ] Add `tests/compose/compose-infra-contract-tests.sh` to validate default Podman-first command selection, Docker fallback behavior, exact `ATRADE_COMPOSE_COMMAND` override behavior, stable project name default `atrade`, profile auto-selection rules, localhost port mappings, named volumes, pids limit, Timescale tune env, and absence of real secret values in committed files
- [ ] Keep static/source checks independent of a running container engine; if live `compose config` checks are included, skip them clearly when neither Podman Compose nor Docker Compose is available
- [ ] Update existing local runtime/paper-trading contract tests so the new variables are intentional and documented

**Artifacts:**
- `tests/compose/compose-infra-contract-tests.sh` (new)
- Existing runtime contract tests (modified if affected)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run Compose contract tests: `bash tests/compose/compose-infra-contract-tests.sh`
- [ ] Run local runtime contract tests: `dotnet test tests/ATrade.ServiceDefaults.Tests/ATrade.ServiceDefaults.Tests.csproj --nologo --verbosity minimal`
- [ ] Run apphost local runtime shell contract tests if affected: `bash tests/apphost/local-runtime-contract-module-tests.sh`
- [ ] Run paper-trading config contract tests if affected: `bash tests/apphost/paper-trading-config-contract-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `scripts/README.md` — document the new Compose helper, Podman-first command selection, stable infra ports, project name, profiles, and the fact that default startup is not cut over in this task
- `.env.template` — document every new variable with safe committed defaults

**Check If Affected:**
- `README.md` — update verification inventory only if a new test script should be listed immediately
- `PLAN.md` — update active queue wording only if needed
- `docs/architecture/overview.md` — do not change the authoritative orchestration decision yet except to mention this staged foundation if necessary
- `tasks/CONTEXT.md` — log deferred work or discoveries only if needed

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] `compose.yaml` defines default Postgres, TimescaleDB, Redis, and NATS services with stable localhost ports and named volumes
- [ ] `ibkr-gateway` and `lean-engine` are Compose profile services only
- [ ] Helper scripts default to Podman Compose, fall back to Docker Compose, and honor `ATRADE_COMPOSE_COMMAND`
- [ ] The existing `start run` / Aspire behavior is not cut over yet
- [ ] No real IBKR credentials, account identifiers, tokens, session cookies, or local secret values are committed or printed

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-069): complete Step N — description`
- **Bug fixes:** `fix(TP-069): description`
- **Tests:** `test(TP-069): description`
- **Hydration:** `hydrate: TP-069 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Change `./start run`, `./start.ps1 run`, or `./start.cmd run` to invoke Compose in this foundation task
- Remove Aspire or stop Aspire from launching API, worker, and frontend
- Remove AppHost-managed infrastructure resources yet; that belongs to the later cutover task
- Commit real broker credentials, account identifiers, tokens, cookies, gateway session data, or local secret values
- Add live-trading behavior, order placement, or direct frontend/database/provider access

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
