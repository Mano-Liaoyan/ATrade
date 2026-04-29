# Task: TP-013 - Wire the IBKR worker and AppHost resource consumers

**Created:** 2026-04-29
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This extends the Aspire runtime graph beyond declared infrastructure by adding the first worker process and explicit application resource references. It touches AppHost startup, manifest verification, and active architecture/startup docs, but it must not add broker behavior or data schemas.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-013-apphost-worker-resource-wiring/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Complete the next `PLAN.md` milestone by extending the current Aspire AppHost graph from "API + frontend + declared infrastructure" to "API + frontend + first worker + explicit infrastructure consumers." The `ATrade.Ibkr.Worker` project already exists as an inert shell, and `Postgres`, `TimescaleDB`, `Redis`, and `NATS` are already declared; this task wires the worker into the AppHost runtime graph and makes the application resources reference the managed infrastructure they will later consume.

## Dependencies

- **Task:** TP-008 (managed infrastructure resources must exist)
- **Task:** TP-009 (the inert `ATrade.Ibkr.Worker` project shell must exist)
- **Task:** TP-012 (the latest AppHost local-port contract must be integrated)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `PLAN.md` — source milestone for this task
- `docs/architecture/overview.md` — target/current runtime graph language
- `docs/architecture/modules.md` — worker and infrastructure dependency map
- `scripts/README.md` — `start run` and AppHost verification contract
- `src/ATrade.AppHost/Program.cs` — current Aspire graph
- `src/ATrade.AppHost/ATrade.AppHost.csproj` — AppHost project references/packages
- `workers/ATrade.Ibkr.Worker/Program.cs` — current inert worker host
- `workers/ATrade.Ibkr.Worker/IbkrWorkerShell.cs` — current inert worker service
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` — existing manifest verification pattern

## Environment

- **Workspace:** Project root
- **Services required:** None for implementation or manifest verification; live infrastructure runtime checks may skip when no Docker-compatible engine is available

## File Scope

> The orchestrator uses this to avoid merge conflicts. TP-014 also touches some API/docs paths and must run after this task.

- `src/ATrade.AppHost/ATrade.AppHost.csproj`
- `src/ATrade.AppHost/Program.cs`
- `workers/ATrade.Ibkr.Worker/*`
- `tests/apphost/apphost-worker-resource-wiring-tests.sh` (new)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (only if shared assertions must change)
- `scripts/README.md`
- `docs/architecture/overview.md`
- `docs/architecture/modules.md`
- `README.md` (if current-status wording would otherwise be stale)
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm `ATrade.Ibkr.Worker` is compileable but not yet part of `src/ATrade.AppHost/Program.cs`
- [ ] Confirm AppHost currently declares `postgres`, `timescaledb`, `redis`, and `nats` without application consumer references

### Step 1: Wire the worker and resource references in AppHost

- [ ] Add `workers/ATrade.Ibkr.Worker/ATrade.Ibkr.Worker.csproj` as an AppHost project reference so Aspire can generate a `Projects.ATrade_Ibkr_Worker` resource type
- [ ] Update `src/ATrade.AppHost/Program.cs` to assign named variables for `postgres`, `timescaledb`, `redis`, and `nats`
- [ ] Add `ATrade.Ibkr.Worker` to the AppHost graph with stable resource name `ibkr-worker`
- [ ] Reference the managed resources from application resources in the graph: API should receive the backend infrastructure it will consume; `ibkr-worker` should receive only its expected worker dependencies (`Postgres`, `Redis`, and `NATS`) unless the source docs justify more
- [ ] Preserve the existing Next.js frontend, local-port contract, container `--pids-limit`, and TimescaleDB `TS_TUNE_*` safeguards
- [ ] Run targeted build: `dotnet build ATrade.sln --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.AppHost/ATrade.AppHost.csproj` (modified)
- `src/ATrade.AppHost/Program.cs` (modified)

### Step 2: Add manifest verification for the new runtime graph

- [ ] Create `tests/apphost/apphost-worker-resource-wiring-tests.sh`
- [ ] Verify the published AppHost manifest contains `ibkr-worker` as a project resource while preserving `api`, `frontend`, `postgres`, `timescaledb`, `redis`, and `nats`
- [ ] Verify manifest output proves the expected resource references / connection-string environment are wired for `api` and `ibkr-worker`
- [ ] Keep the test engine-independent; do not require Docker/Podman for the primary new verification
- [ ] Run targeted test: `bash tests/apphost/apphost-worker-resource-wiring-tests.sh`

**Artifacts:**
- `tests/apphost/apphost-worker-resource-wiring-tests.sh` (new)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (modified only if required)

### Step 3: Update docs and milestone state

- [ ] Update `scripts/README.md` so the current `start run` slice includes the AppHost-managed `ibkr-worker` and explicit application infrastructure references
- [ ] Update `docs/architecture/overview.md` so the current-slice note no longer says worker shells are absent from the runtime graph
- [ ] Update `docs/architecture/modules.md` so `ATrade.Ibkr.Worker`, `ATrade.Api`, and AppHost dependency notes distinguish graph wiring from functional broker/data behavior
- [ ] Update `PLAN.md` to mark the worker/resource-consumer milestone complete only if the implementation actually satisfies it
- [ ] Check `README.md` and update current-status wording if it would otherwise become stale

**Artifacts:**
- `scripts/README.md` (modified)
- `docs/architecture/overview.md` (modified)
- `docs/architecture/modules.md` (modified)
- `PLAN.md` (modified)
- `README.md` (modified if affected)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet build ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm `apphost-infrastructure-runtime-tests.sh` passes or cleanly skips when no Docker-compatible engine is available
- [ ] Fix all failures
- [ ] Confirm generated AppHost manifest still preserves the frontend local-port contract and infrastructure container safeguards

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `scripts/README.md` — add the worker/resource-consumer wiring to the current bootstrap graph and verification scope
- `docs/architecture/overview.md` — update current-slice wording for the runtime graph
- `docs/architecture/modules.md` — update AppHost/API/worker current-state notes without overstating feature behavior
- `PLAN.md` — mark the relevant milestone complete only after implementation and verification

**Check If Affected:**
- `README.md` — update current status if it still says workers are not part of the runtime graph
- `docs/INDEX.md` — update only if a new indexed document is added (none expected)

## Completion Criteria

- [ ] `ATrade.Ibkr.Worker` is an AppHost-managed project resource named `ibkr-worker`
- [ ] AppHost application resources explicitly reference the managed infrastructure they are expected to consume
- [ ] Existing API, frontend, local-port, and infrastructure safeguards are preserved
- [ ] A new manifest test verifies worker/resource wiring without requiring a container engine
- [ ] Active docs and `PLAN.md` accurately describe the resulting graph

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-013): complete Step N — description`
- **Bug fixes:** `fix(TP-013): description`
- **Tests:** `test(TP-013): description`
- **Hydration:** `hydrate: TP-013 expand Step N checkboxes`

## Do NOT

- Implement IBKR connectivity, broker sessions, order routing, account reconciliation, or market-data behavior
- Add hard-coded secrets, connection strings, credentials, or machine-specific values
- Replace Aspire references with ad-hoc environment variables or scripts
- Remove or weaken the TP-010/TP-011/TP-012 frontend, container-runtime, or local-port safeguards
- Mark the first backend feature-behavior milestone complete in this task
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
