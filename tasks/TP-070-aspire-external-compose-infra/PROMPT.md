# Task: TP-070 - Aspire external Compose infrastructure mode

**Created:** 2026-05-09
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This task teaches the Aspire AppHost to reference Compose-managed infrastructure through external localhost connection strings while preserving the existing AppHost-managed infra path until the final cutover. It affects AppHost runtime wiring across API/worker/frontend and must avoid leaking database or broker secrets into manifests.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 1, Security: 1, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-070-aspire-external-compose-infra/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Add an opt-in AppHost mode where Aspire still launches the ATrade API, IBKR worker, and Next.js frontend, but no longer declares or displays infrastructure containers. In that mode, AppHost injects connection strings pointing at the Compose-published localhost ports created by TP-069, while optional iBeam and LEAN runtime containers are treated as Compose-owned external runtimes. The default `start run` behavior must remain unchanged in this task so the full suite can pass before the final cutover.

## Dependencies

- **Task:** TP-069 (Compose runtime foundation must exist)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `tasks/TP-069-compose-runtime-foundation/PROMPT.md` — Compose contract established by the prerequisite task
- `docs/INDEX.md` — documentation discovery layer
- `scripts/README.md` — current AppHost/startup/runtime contracts
- `docs/architecture/overview.md` — current Aspire role and infrastructure wording
- `.env.template` — local runtime variable defaults
- `src/ATrade.AppHost/Program.cs` — current AppHost graph
- `src/ATrade.AppHost/AppHostStorageContract.cs` — existing storage contract wrapper
- `src/ATrade.AppHost/PaperTradingEnvironmentContract.cs` — existing iBeam enablement/placeholder logic
- `src/ATrade.AppHost/LeanAnalysisRuntimeContract.cs` — existing LEAN Docker runtime logic
- `src/ATrade.ServiceDefaults/LocalRuntimeContract.cs` — shared runtime contract loader

## Environment

- **Workspace:** `src/ATrade.AppHost`, `src/ATrade.ServiceDefaults`, AppHost/runtime tests
- **Services required:** None for manifest/static validation. Compose containers are not required for opt-in manifest tests.

## File Scope

- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.AppHost/*Compose*Contract*.cs` or equivalent new AppHost helper files
- `src/ATrade.AppHost/AppHostStorageContract.cs` (if updated/replaced)
- `src/ATrade.ServiceDefaults/LocalRuntimeContract.cs` (only if TP-069 left runtime-mode/port fields incomplete)
- `.env.template` (only if TP-069 left runtime-mode documentation incomplete)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh`
- `tests/apphost/apphost-worker-resource-wiring-tests.sh`
- `tests/apphost/lean-aspire-runtime-tests.sh` (check/update compose-mode expectations only if affected)
- `tests/apphost/ibeam-runtime-contract-tests.sh` (check/update compose-mode expectations only if affected)
- `tests/ATrade.ServiceDefaults.Tests/*` (if runtime contract changes)
- `scripts/README.md`
- `tasks/CONTEXT.md` (log discoveries only if needed)

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Model opt-in Compose infrastructure mode

- [ ] Add or finalize an `ATRADE_INFRASTRUCTURE_MODE`-style runtime setting with accepted values for the current AppHost-managed path and the new Compose-managed-infra path; keep the default on the current AppHost-managed path in this task
- [ ] Build localhost connection strings from the shared runtime contract values: Postgres on `ATRADE_POSTGRES_PORT`, TimescaleDB on `ATRADE_TIMESCALEDB_PORT`, Redis on `ATRADE_REDIS_PORT`, and NATS on `ATRADE_NATS_PORT`
- [ ] Keep database passwords secret in Aspire manifests by using secret parameter/reference-expression plumbing rather than embedding raw password values into generated manifests
- [ ] Validate/normalize port and mode values consistently with the existing `LocalRuntimeContract` validation style

**Artifacts:**
- `src/ATrade.AppHost/*` (new/modified helper files)
- `src/ATrade.ServiceDefaults/LocalRuntimeContract.cs` (modified only if needed)
- `.env.template` (modified only if needed)

### Step 2: Add external-infra AppHost graph behavior

- [ ] In Compose infrastructure mode, stop declaring AppHost container resources for `postgres`, `timescaledb`, `redis`, `nats`, `ibkr-gateway`, and `lean-engine`
- [ ] In Compose infrastructure mode, keep Aspire project resources for `api`, `ibkr-worker`, and the Next.js `frontend`
- [ ] In Compose infrastructure mode, inject `ConnectionStrings__postgres`, `ConnectionStrings__timescaledb`, `ConnectionStrings__redis`, and `ConnectionStrings__nats` into the resources that currently receive managed-resource references
- [ ] Preserve existing API/worker paper-trading and LEAN environment variables; optional iBeam and LEAN containers are Compose-owned but API/worker still receive the safe runtime contract values they need
- [ ] Preserve the existing AppHost-managed infrastructure behavior when the mode is not Compose so current startup remains stable until TP-071

**Artifacts:**
- `src/ATrade.AppHost/Program.cs` (modified)
- AppHost helper files (new/modified)

### Step 3: Add opt-in manifest and wiring tests

- [ ] Update or add manifest tests that run AppHost in Compose infrastructure mode and assert infra container resources are absent from the Aspire manifest/dashboard model
- [ ] Assert `api`, `ibkr-worker`, and `frontend` remain present and that API/worker receive direct/external connection string environment values or secret-safe reference expressions
- [ ] Assert raw database passwords, IBKR usernames/passwords/account ids, gateway URLs with real credentials, tokens, cookies, and LEAN workspace secrets are not exposed in manifests
- [ ] Keep existing AppHost-managed default manifest expectations passing until the final cutover task changes the default

**Artifacts:**
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (modified)
- `tests/apphost/apphost-worker-resource-wiring-tests.sh` (modified)
- `tests/apphost/lean-aspire-runtime-tests.sh` (modified only if affected)
- `tests/apphost/ibeam-runtime-contract-tests.sh` (modified only if affected)

### Step 4: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run AppHost manifest validation: `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Run AppHost worker/resource wiring validation: `bash tests/apphost/apphost-worker-resource-wiring-tests.sh`
- [ ] Run iBeam runtime contract validation if affected: `bash tests/apphost/ibeam-runtime-contract-tests.sh`
- [ ] Run LEAN runtime validation if affected: `bash tests/apphost/lean-aspire-runtime-tests.sh`
- [ ] Run local runtime contract tests if affected: `dotnet test tests/ATrade.ServiceDefaults.Tests/ATrade.ServiceDefaults.Tests.csproj --nologo --verbosity minimal`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `scripts/README.md` — document the new opt-in AppHost mode and clarify that default `start run` still uses existing behavior until the cutover task

**Check If Affected:**
- `.env.template` — update only if a runtime mode variable or missing port default is added here rather than in TP-069
- `docs/architecture/overview.md` — mention only the staged opt-in behavior if needed; do not claim default cutover yet
- `README.md` / `PLAN.md` — update verification inventory only if new validation scripts are added
- `tasks/CONTEXT.md` — log discoveries/deferred work only if needed

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] AppHost has a tested Compose infrastructure mode where infrastructure containers do not appear in the Aspire manifest/dashboard model
- [ ] API, worker, and frontend remain Aspire-launched project/frontend resources
- [ ] Compose-mode API/worker receive correct external localhost connection strings and safe paper/LEAN environment values
- [ ] Default `start run` behavior is still unchanged until TP-071
- [ ] No raw database passwords, IBKR credentials, account ids, tokens, session cookies, or secret local values are committed or exposed in manifests

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-070): complete Step N — description`
- **Bug fixes:** `fix(TP-070): description`
- **Tests:** `test(TP-070): description`
- **Hydration:** `hydrate: TP-070 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Remove Aspire or stop Aspire from launching API, worker, or frontend
- Change the default `./start run` behavior in this task
- Let Compose-mode AppHost declare/display `postgres`, `timescaledb`, `redis`, `nats`, `ibkr-gateway`, or `lean-engine` as Aspire-managed container resources
- Leak raw database passwords, IBKR credentials, account identifiers, tokens, cookies, or local secret values into manifests, docs, tests, logs, or source
- Add live-trading behavior, order placement, or direct frontend/database/provider access

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
