# Task: TP-071 - Compose startup cutover for Aspire-launched app services

**Created:** 2026-05-09
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This task changes the default cross-platform startup path so Compose owns infrastructure while Aspire continues to launch API, worker, and frontend. It has a multi-service runtime blast radius and secret-bearing environment handling, but the staged foundation and opt-in mode make it reversible.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 1, Security: 1, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-071-compose-startup-cutover/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Cut over the default local runtime so `./start run`, `./start.ps1 run`, and `./start.cmd run` start infrastructure through Podman/Docker Compose first, then launch the Aspire AppHost for only the API, IBKR worker, and Next.js frontend. Infrastructure containers must not appear in the Aspire dashboard by default. The Compose stack should remain running after AppHost exits, and all docs/tests must describe the new division of responsibility clearly.

## Dependencies

- **Task:** TP-069 (Compose runtime foundation must exist)
- **Task:** TP-070 (AppHost external Compose infrastructure mode must exist)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `tasks/TP-069-compose-runtime-foundation/PROMPT.md` — Compose helper and contract expectations
- `tasks/TP-070-aspire-external-compose-infra/PROMPT.md` — AppHost external-infra mode expectations
- `docs/INDEX.md` — documentation discovery layer
- `README.md` — human-facing runtime overview and verification inventory
- `PLAN.md` — active runtime/startup direction
- `scripts/README.md` — startup contract and local environment contract
- `docs/architecture/overview.md` — authoritative architecture wording that currently says Aspire manages infrastructure
- `docs/architecture/modules.md` — runtime/module map, if affected by the orchestration change
- `.env.template` — final default local runtime values
- `scripts/start.run.sh` — Unix `start run` implementation
- `scripts/start.run.ps1` — PowerShell `start run` implementation
- `start.cmd` / `start.ps1` / `start` — top-level wrapper contracts
- `src/ATrade.AppHost/Program.cs` — final AppHost graph behavior

## Environment

- **Workspace:** cross-platform startup scripts, AppHost graph/tests, active runtime docs
- **Services required:** Source/static tests must run without real IBKR/iBeam/LEAN credentials. Runtime Compose tests should skip clearly if neither Podman Compose nor Docker Compose is available.

## File Scope

- `.env.template`
- `scripts/start.run.sh`
- `scripts/start.run.ps1`
- `scripts/compose-infra.sh`
- `scripts/compose-infra.ps1`
- `start`, `start.ps1`, `start.cmd` (read/check; modify only if wrapper contract needs usage text updates)
- `src/ATrade.AppHost/Program.cs`
- `tests/start-contract/start-wrapper-tests.sh`
- `tests/start-contract/start-wrapper-windows.ps1`
- `tests/apphost/apphost-infrastructure-manifest-tests.sh`
- `tests/apphost/apphost-worker-resource-wiring-tests.sh`
- `tests/apphost/apphost-infrastructure-runtime-tests.sh`
- `tests/apphost/apphost-postgres-watchlist-volume-tests.sh`
- `tests/apphost/apphost-timescale-cache-volume-tests.sh`
- `tests/apphost/lean-aspire-runtime-tests.sh`
- `tests/apphost/ibeam-runtime-contract-tests.sh`
- `tests/compose/*`
- `README.md`
- `PLAN.md`
- `scripts/README.md`
- `docs/architecture/overview.md`
- `docs/architecture/modules.md` (check/update if affected)
- `docs/INDEX.md` (only if a new ADR/doc is added)
- `tasks/CONTEXT.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Flip the default startup contract to Compose-managed infrastructure

- [ ] Update `.env.template` and runtime defaults so the default infrastructure mode is Compose-managed infrastructure with Aspire-launched app services
- [ ] Update Unix and PowerShell `start run` implementations to invoke the Compose helper `up` before launching AppHost
- [ ] Ensure helper command selection defaults to `podman compose`, falls back to `docker compose`, and honors exact `ATRADE_COMPOSE_COMMAND` overrides
- [ ] Ensure `start run` does not automatically run Compose `down` when AppHost exits; infrastructure stays warm until the developer stops it explicitly
- [ ] Preserve cross-platform wrapper semantics for `./start run`, `./start.ps1 run`, and `./start.cmd run`

**Artifacts:**
- `.env.template` (modified)
- `scripts/start.run.sh` (modified)
- `scripts/start.run.ps1` (modified)
- `scripts/compose-infra.sh` (modified if needed)
- `scripts/compose-infra.ps1` (modified if needed)

### Step 2: Make the default AppHost graph dashboard-honest

- [ ] Make Compose infrastructure mode the default AppHost path
- [ ] Ensure the default Aspire manifest/dashboard model contains API, IBKR worker, and frontend resources, but not `postgres`, `timescaledb`, `redis`, `nats`, `ibkr-gateway`, or `lean-engine` container resources
- [ ] Preserve secret-safe connection string and paper/LEAN environment handoff to API/worker
- [ ] If an explicit legacy/fallback AppHost-managed infra mode remains, document it as diagnostic/temporary only and keep it out of the default path

**Artifacts:**
- `src/ATrade.AppHost/Program.cs` (modified)
- AppHost helper files (modified if needed)

### Step 3: Migrate startup and AppHost validation

- [ ] Update start-wrapper tests to verify `start run` calls the Compose helper before AppHost, uses Podman-first selection by default, honors `ATRADE_COMPOSE_COMMAND`, preserves `.env.template` → `.env` → process env precedence, and leaves Compose running on AppHost exit
- [ ] Update AppHost manifest/resource wiring tests so default expectations assert no Aspire-managed infra container resources are present
- [ ] Update iBeam and LEAN tests so optional runtime containers are Compose profile responsibilities, while API/worker still receive safe/redacted runtime settings
- [ ] Keep Windows wrapper validation semantically aligned with Unix behavior

**Artifacts:**
- `tests/start-contract/start-wrapper-tests.sh` (modified)
- `tests/start-contract/start-wrapper-windows.ps1` (modified if affected)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (modified)
- `tests/apphost/apphost-worker-resource-wiring-tests.sh` (modified)
- `tests/apphost/ibeam-runtime-contract-tests.sh` (modified)
- `tests/apphost/lean-aspire-runtime-tests.sh` (modified)

### Step 4: Migrate runtime persistence and infrastructure tests

- [ ] Update AppHost infrastructure runtime validation to exercise Compose-managed Postgres, TimescaleDB, Redis, and NATS rather than looking for Aspire-created infra containers
- [ ] Update Postgres watchlist persistence validation so durable rows survive a full `start run` AppHost restart when Compose uses the same configured named Postgres volume
- [ ] Update Timescale cache persistence validation so fresh cache rows survive a full `start run` AppHost restart when Compose uses the same configured named TimescaleDB volume
- [ ] Ensure live runtime tests clean up only isolated test containers/volumes they created and skip clearly when no compatible Podman/Docker Compose engine is available

**Artifacts:**
- `tests/apphost/apphost-infrastructure-runtime-tests.sh` (modified)
- `tests/apphost/apphost-postgres-watchlist-volume-tests.sh` (modified)
- `tests/apphost/apphost-timescale-cache-volume-tests.sh` (modified)
- `tests/compose/*` (modified if shared helpers are needed)

### Step 5: Documentation and durable memory update

- [ ] Update `README.md`, `PLAN.md`, `scripts/README.md`, and `docs/architecture/overview.md` to state the final split: Compose manages infra; Aspire launches API, worker, and frontend; infra no longer appears in the Aspire dashboard by default
- [ ] Update `docs/architecture/modules.md` if its runtime map still says Aspire directly owns infrastructure containers
- [ ] Update verification inventories for new/renamed Compose/startup tests
- [ ] Consider whether a short ADR is warranted for the orchestration split; if added, include it in `docs/INDEX.md`
- [ ] Update `tasks/CONTEXT.md` with the new runtime contract and next task state

**Artifacts:**
- `README.md` (modified)
- `PLAN.md` (modified)
- `scripts/README.md` (modified)
- `docs/architecture/overview.md` (modified)
- `docs/architecture/modules.md` (modified if affected)
- `docs/INDEX.md` (modified only if a new ADR/doc is added)
- `tasks/CONTEXT.md` (modified)

### Step 6: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run Compose contract tests: `bash tests/compose/compose-infra-contract-tests.sh`
- [ ] Run start wrapper tests: `bash tests/start-contract/start-wrapper-tests.sh`
- [ ] Run AppHost manifest validation: `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Run AppHost worker/resource wiring validation: `bash tests/apphost/apphost-worker-resource-wiring-tests.sh`
- [ ] Run iBeam runtime contract validation: `bash tests/apphost/ibeam-runtime-contract-tests.sh`
- [ ] Run LEAN runtime validation: `bash tests/apphost/lean-aspire-runtime-tests.sh`
- [ ] Run Compose/AppHost infra runtime validation if a compatible engine is available: `bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Run Postgres watchlist volume validation if a compatible engine is available: `bash tests/apphost/apphost-postgres-watchlist-volume-tests.sh`
- [ ] Run Timescale cache volume validation if a compatible engine is available: `bash tests/apphost/apphost-timescale-cache-volume-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 7: Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `README.md` — current stack, run contract, runtime surface, and verification inventory
- `PLAN.md` — current runtime direction and active task queue state
- `scripts/README.md` — authoritative startup/local env/Compose/AppHost contract
- `docs/architecture/overview.md` — authoritative architecture change from Aspire-managed infra to Compose-managed infra with Aspire app orchestration
- `tasks/CONTEXT.md` — durable runtime memory and next task state

**Check If Affected:**
- `docs/architecture/modules.md` — update if runtime/module map references AppHost-managed infra containers
- `docs/INDEX.md` — update only if a new ADR/doc is added
- `docs/architecture/provider-abstractions.md`, `docs/architecture/analysis-engines.md`, `docs/architecture/backtesting.md`, and `docs/architecture/paper-trading-workspace.md` — update only if they contain stale AppHost-managed iBeam/LEAN/infra wording that becomes misleading

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] `start run` starts Compose infrastructure first, then starts Aspire for app services
- [ ] Podman Compose is the default Compose implementation, Docker Compose is fallback, and `ATRADE_COMPOSE_COMMAND` is honored
- [ ] Default Aspire dashboard/manifest no longer shows infra containers
- [ ] API and worker still receive correct Postgres, TimescaleDB, Redis, NATS, iBeam, and LEAN runtime settings
- [ ] Optional iBeam and LEAN containers are Compose profile services selected automatically from `.env`/process env
- [ ] Compose stays running after AppHost exits unless the developer explicitly stops it
- [ ] No real secrets, account identifiers, tokens, cookies, or live-trading behavior are introduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-071): complete Step N — description`
- **Bug fixes:** `fix(TP-071): description`
- **Tests:** `test(TP-071): description`
- **Hydration:** `hydrate: TP-071 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Remove Aspire or stop Aspire from launching API, worker, and frontend
- Show Postgres, TimescaleDB, Redis, NATS, iBeam, or LEAN containers in the default Aspire dashboard/manifest
- Make Docker Compose the default over Podman Compose
- Automatically run Compose `down` when AppHost exits
- Commit or print real IBKR credentials, account identifiers, database passwords, tokens, session cookies, gateway sessions, or local secret values
- Add live order placement, live-trading behavior, direct frontend/database/provider access, or order-entry UI paths

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
