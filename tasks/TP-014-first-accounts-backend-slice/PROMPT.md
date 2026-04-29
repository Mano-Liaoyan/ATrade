# Task: TP-014 - Add the first read-only Accounts backend slice

**Created:** 2026-04-29
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This creates the first concrete backend feature-module behavior by wiring `ATrade.Accounts` into `ATrade.Api` and exposing a stable read-only endpoint. It establishes the first module composition pattern and API contract, but avoids persistence, auth, broker integration, and money-moving behavior.
**Score:** 4/8 — Blast radius: 1, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-014-first-accounts-backend-slice/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Complete the remaining `PLAN.md` backend-feature milestone with a deliberately small, safe, read-only Accounts slice. `ATrade.Accounts` is currently only a marker-type project; turn it into the first usable feature module by adding a deterministic account-overview service and exposing it through `ATrade.Api` at `GET /api/accounts/overview`. The endpoint must prove feature-module wiring without pretending IBKR connectivity, persisted account data, authentication, trading, or portfolio reconciliation exists yet.

## Dependencies

- **Task:** TP-013 (AppHost worker/resource-consumer wiring should land first because this task touches overlapping API/AppHost documentation and should build on the updated runtime graph)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `PLAN.md` — source milestone for this task
- `docs/architecture/overview.md` — current backend slice language
- `docs/architecture/modules.md` — Accounts/API module boundary and dependency language
- `scripts/README.md` — verification and startup contract context
- `src/ATrade.Accounts/ATrade.Accounts.csproj` — current Accounts project shell
- `src/ATrade.Accounts/AccountsAssemblyMarker.cs` — current marker-only implementation
- `src/ATrade.Api/ATrade.Api.csproj` — API project references
- `src/ATrade.Api/Program.cs` — current API endpoint mapping
- `tests/apphost/api-bootstrap-tests.sh` — direct API startup/test pattern
- `scripts/local-env.sh` — local port contract helper used by shell tests

## Environment

- **Workspace:** Project root
- **Services required:** None. This slice must run without Postgres, Redis, NATS, TimescaleDB, IBKR, or Polygon.

## File Scope

> The orchestrator uses this to avoid merge conflicts. This task depends on TP-013 because both tasks touch API/runtime docs.

- `src/ATrade.Accounts/*`
- `src/ATrade.Api/ATrade.Api.csproj`
- `src/ATrade.Api/Program.cs`
- `tests/apphost/accounts-feature-bootstrap-tests.sh` (new)
- `tests/apphost/api-bootstrap-tests.sh` (only if shared API assertions must change)
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `scripts/README.md` (if verification scope changes)
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm `ATrade.Accounts` currently contains only marker/shell behavior
- [ ] Confirm `ATrade.Api` currently exposes only `GET /health`

### Step 1: Implement the read-only Accounts module behavior

- [ ] Create Accounts module types for a deterministic account overview response with stable fields: `module`, `status`, `brokerConnection`, and an empty `accounts` collection
- [ ] Add an Accounts overview service/provider that returns bootstrap-safe data such as `module = "accounts"`, `status = "bootstrap"`, `brokerConnection = "not-configured"`, and `accounts = []`
- [ ] Add a minimal module registration extension so `ATrade.Api` can register Accounts behavior through dependency injection
- [ ] Keep the existing assembly marker or equivalent compile-time anchor if useful for module discovery/tests
- [ ] Do not add persistence, schemas, external provider clients, fake positions, fake balances, or trading/order behavior
- [ ] Run targeted build: `dotnet build src/ATrade.Accounts/ATrade.Accounts.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.Accounts/ATrade.Accounts.csproj` (modified if required)
- `src/ATrade.Accounts/AccountsAssemblyMarker.cs` (modified or preserved)
- `src/ATrade.Accounts/AccountOverview.cs` (new or equivalent)
- `src/ATrade.Accounts/AccountOverviewService.cs` (new or equivalent)
- `src/ATrade.Accounts/AccountsModuleServiceCollectionExtensions.cs` (new or equivalent)

### Step 2: Expose the Accounts overview through the API

- [ ] Add a project reference from `src/ATrade.Api/ATrade.Api.csproj` to `src/ATrade.Accounts/ATrade.Accounts.csproj`
- [ ] Register the Accounts module during API startup in `src/ATrade.Api/Program.cs`
- [ ] Map `GET /api/accounts/overview` to return the Accounts overview service response as JSON
- [ ] Preserve the existing `GET /health` endpoint behavior exactly
- [ ] Run targeted API smoke check by starting `ATrade.Api` and calling both `/health` and `/api/accounts/overview`

**Artifacts:**
- `src/ATrade.Api/ATrade.Api.csproj` (modified)
- `src/ATrade.Api/Program.cs` (modified)

### Step 3: Add feature-slice verification

- [ ] Create `tests/apphost/accounts-feature-bootstrap-tests.sh`
- [ ] Verify `ATrade.Api` references `ATrade.Accounts` and the solution builds
- [ ] Start `ATrade.Api` using the repo local-port contract and assert `/health` still returns `ok`
- [ ] Assert `GET /api/accounts/overview` returns HTTP 200 and JSON markers for `module`, `status`, `brokerConnection`, and `accounts`
- [ ] Assert the endpoint does not require managed infrastructure or external broker/data-provider services
- [ ] Run targeted test: `bash tests/apphost/accounts-feature-bootstrap-tests.sh`

**Artifacts:**
- `tests/apphost/accounts-feature-bootstrap-tests.sh` (new)
- `tests/apphost/api-bootstrap-tests.sh` (modified only if required)

### Step 4: Update docs and milestone state

- [ ] Update `docs/architecture/modules.md` so `ATrade.Accounts` and `ATrade.Api` current-state notes describe the read-only overview slice without overstating persistence, IBKR reconciliation, or broader account behavior
- [ ] Update `docs/architecture/overview.md` so the current backend slice mentions `GET /health` plus the first Accounts overview endpoint
- [ ] Update `README.md` current status if it would otherwise imply no backend feature behavior exists
- [ ] Update `PLAN.md` to mark the first backend feature-behavior milestone complete only if this endpoint and verification land successfully
- [ ] Check `scripts/README.md` and update verification scope only if the new test changes the described startup/test surface

**Artifacts:**
- `docs/architecture/modules.md` (modified)
- `docs/architecture/overview.md` (modified)
- `README.md` (modified)
- `PLAN.md` (modified)
- `scripts/README.md` (modified if affected)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet build ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm `apphost-infrastructure-runtime-tests.sh` passes or cleanly skips when no Docker-compatible engine is available
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/modules.md` — update Accounts/API current-state notes for the first read-only behavior slice
- `docs/architecture/overview.md` — update current backend slice language
- `README.md` — update repository current status if no-backend-feature wording becomes stale
- `PLAN.md` — mark the backend-feature milestone complete only after implementation and verification

**Check If Affected:**
- `scripts/README.md` — update only if the verification/startup surface description changes
- `docs/INDEX.md` — update only if a new indexed document is added (none expected)

## Completion Criteria

- [ ] `ATrade.Accounts` contains real read-only module behavior, not only a marker type
- [ ] `ATrade.Api` exposes `GET /api/accounts/overview` with deterministic bootstrap JSON
- [ ] `/health` still returns `ok`
- [ ] New test coverage proves the Accounts endpoint works without external services
- [ ] Active docs and `PLAN.md` accurately describe the first backend feature behavior

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-014): complete Step N — description`
- **Bug fixes:** `fix(TP-014): description`
- **Tests:** `test(TP-014): description`
- **Hydration:** `hydrate: TP-014 expand Step N checkboxes`

## Do NOT

- Add order placement, broker session handling, account reconciliation, or money-moving behavior
- Add database schemas, migrations, seed data, or persistence in this first slice
- Add fake portfolio balances, fake positions, or fake executions that could be mistaken for broker data
- Require Postgres, TimescaleDB, Redis, NATS, IBKR, or Polygon for this endpoint
- Break the existing `/health` endpoint or local-port contract
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
