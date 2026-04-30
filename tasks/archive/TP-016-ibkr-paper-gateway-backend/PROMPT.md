# Task: TP-016 - Implement IBKR paper Gateway backend and order simulation guard

**Created:** 2026-04-29
**Size:** L

## Review Level: 3 (Full)

**Assessment:** This adds the first broker-adapter behavior and paper-only safety guardrails across backend modules, the API host, the IBKR worker, AppHost configuration, and tests. It touches sensitive broker/session configuration and must prove no path can place or simulate live trades.
**Score:** 6/8 — Blast radius: 2, Pattern novelty: 2, Security: 1, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-016-ibkr-paper-gateway-backend/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Implement the safe backend half of the paper-trading workspace by adding an IBKR Gateway adapter boundary that can talk to the official Dockerized IBKR Gateway / Client Portal Gateway when configured, while remaining disabled and testable by default. The implementation must enforce paper-trading mode only, expose broker session/status information, and provide order simulation that never places real broker orders. Real credentials and account identifiers must live only in ignored `.env`, never in committed files.

## Dependencies

- **Task:** TP-015 (paper-trading workspace architecture and `.env` contract must exist first)

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/paper-trading-workspace.md` — authoritative safety/data-flow contract from TP-015
- `.env.template` — paper-mode configuration placeholders from TP-015
- `docs/architecture/modules.md` — module boundary authority
- `docs/architecture/overview.md` — runtime topology and infrastructure authority
- `scripts/README.md` — startup and ignored `.env` contract
- `src/ATrade.Api/ATrade.Api.csproj` — API project references
- `src/ATrade.Api/Program.cs` — current endpoint mapping and module registration style
- `src/ATrade.Orders/ATrade.Orders.csproj` — current Orders module shell
- `workers/ATrade.Ibkr.Worker/Program.cs` — current worker host composition
- `workers/ATrade.Ibkr.Worker/IbkrWorkerShell.cs` — current inert worker shell
- `src/ATrade.AppHost/Program.cs` — current AppHost resource graph
- `tests/apphost/accounts-feature-bootstrap-tests.sh` — direct API feature-test pattern
- `tests/apphost/apphost-worker-resource-wiring-tests.sh` — AppHost manifest/resource verification pattern

## Environment

- **Workspace:** Project root
- **Services required:** None for automated tests. Tests must use disabled mode, fake gateway responses, or local process stubs. A real official IBKR paper Gateway may be used only for optional manual verification when configured through ignored `.env`.

## File Scope

> This task intentionally touches backend and runtime graph files. It depends on TP-015 and should run before frontend paper-trading dashboard work.

- `ATrade.sln`
- `src/ATrade.Brokers.Ibkr/*` (new)
- `src/ATrade.Api/ATrade.Api.csproj`
- `src/ATrade.Api/Program.cs`
- `src/ATrade.Orders/*`
- `workers/ATrade.Ibkr.Worker/*`
- `src/ATrade.AppHost/Program.cs`
- `.env.template`
- `tests/apphost/ibkr-paper-safety-tests.sh` (new)
- `tests/apphost/apphost-worker-resource-wiring-tests.sh` (only if manifest expectations change)
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `scripts/README.md`
- `README.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm TP-015 architecture/config contract is present and indexed
- [ ] Confirm current `ATrade.Ibkr.Worker` still has no broker behavior beyond the inert shell
- [ ] Confirm no committed file contains real IBKR credentials or account identifiers

### Step 1: Add the IBKR broker adapter project and paper-only guard

- [ ] Create `src/ATrade.Brokers.Ibkr/ATrade.Brokers.Ibkr.csproj` and add it to `ATrade.sln`
- [ ] Add typed options for IBKR Gateway base URL, enabled/disabled state, account mode, optional paper account identifier, timeout, and optional official Gateway container metadata
- [ ] Implement a paper-only guard that refuses any mode other than `Paper` and makes live trading impossible by construction
- [ ] Implement a minimal Gateway client boundary for official IBKR Gateway session/status calls; if no official package is available, use a thin `HttpClient` wrapper against the official Gateway endpoint shape and test it with fake handlers
- [ ] Do not add unofficial broker SDKs, real credential storage, order placement, executions, positions reconciliation, or database persistence
- [ ] Run targeted build: `dotnet build src/ATrade.Brokers.Ibkr/ATrade.Brokers.Ibkr.csproj --nologo --verbosity minimal`

**Artifacts:**
- `src/ATrade.Brokers.Ibkr/ATrade.Brokers.Ibkr.csproj` (new)
- `src/ATrade.Brokers.Ibkr/IbkrGatewayOptions.cs` (new or equivalent)
- `src/ATrade.Brokers.Ibkr/IbkrPaperTradingGuard.cs` (new or equivalent)
- `src/ATrade.Brokers.Ibkr/IbkrGatewayClient.cs` (new or equivalent)
- `src/ATrade.Brokers.Ibkr/IbkrServiceCollectionExtensions.cs` (new or equivalent)
- `ATrade.sln` (modified)

### Step 2: Wire paper-mode configuration through the worker and AppHost

- [ ] Register the IBKR broker adapter in `workers/ATrade.Ibkr.Worker` without starting a live broker session when disabled
- [ ] Update the worker shell so it reports safe disabled/paper-only status and fails fast or degrades safely if configuration requests live mode
- [ ] Wire relevant paper-mode environment variables through `src/ATrade.AppHost/Program.cs` without committing secrets or requiring an IBKR Gateway container by default
- [ ] If AppHost declares an IBKR Gateway container, make it optional and driven by an explicit official image value from ignored `.env`; do not hard-code or pull an unofficial image
- [ ] Preserve existing Postgres/Redis/NATS worker resource references
- [ ] Run targeted manifest test: `bash tests/apphost/apphost-worker-resource-wiring-tests.sh`

**Artifacts:**
- `workers/ATrade.Ibkr.Worker/ATrade.Ibkr.Worker.csproj` (modified if project reference needed)
- `workers/ATrade.Ibkr.Worker/Program.cs` (modified)
- `workers/ATrade.Ibkr.Worker/IbkrWorkerShell.cs` (modified or replaced)
- `src/ATrade.AppHost/Program.cs` (modified)
- `tests/apphost/apphost-worker-resource-wiring-tests.sh` (modified only if required)

### Step 3: Expose safe API status and order simulation endpoints

- [ ] Register the IBKR adapter and Orders simulation behavior in `src/ATrade.Api/Program.cs`
- [ ] Add a safe read-only endpoint such as `GET /api/broker/ibkr/status` that reports disabled/paper/session status without exposing secrets
- [ ] Add order simulation behavior under `ATrade.Orders` and expose it through an API endpoint such as `POST /api/orders/simulate`
- [ ] Ensure simulated orders are clearly marked `simulated`, never call the IBKR Gateway order endpoints, and reject any non-paper configuration
- [ ] Preserve existing `GET /health` and `GET /api/accounts/overview` behavior exactly
- [ ] Run targeted API smoke checks against `/health`, `/api/accounts/overview`, `/api/broker/ibkr/status`, and the simulation endpoint

**Artifacts:**
- `src/ATrade.Api/ATrade.Api.csproj` (modified)
- `src/ATrade.Api/Program.cs` (modified)
- `src/ATrade.Orders/ATrade.Orders.csproj` (modified if required)
- `src/ATrade.Orders/OrderSimulation*.cs` (new or equivalent)
- `src/ATrade.Orders/OrdersModuleServiceCollectionExtensions.cs` (new or equivalent)

### Step 4: Add paper-safety verification

- [ ] Create `tests/apphost/ibkr-paper-safety-tests.sh`
- [ ] Verify the solution builds with the new broker adapter and API/worker references
- [ ] Verify default configuration is disabled or paper-only and never live-enabled
- [ ] Verify API status output redacts secrets and exposes only safe status fields
- [ ] Verify order simulation returns deterministic simulated responses and does not call a broker order endpoint
- [ ] Verify live-mode configuration is rejected or fails safely before any broker action can occur
- [ ] Run targeted test: `bash tests/apphost/ibkr-paper-safety-tests.sh`

**Artifacts:**
- `tests/apphost/ibkr-paper-safety-tests.sh` (new)

### Step 5: Update architecture and startup docs

- [ ] Update `docs/architecture/paper-trading-workspace.md` with the implemented backend API/worker/config shape and any discovered official Gateway constraints
- [ ] Update `docs/architecture/modules.md` so `ATrade.Brokers.Ibkr`, `ATrade.Orders`, `ATrade.Api`, and `ATrade.Ibkr.Worker` current-state notes reflect the paper-only backend slice
- [ ] Update `docs/architecture/overview.md` if the AppHost graph or runtime surface changed
- [ ] Update `scripts/README.md` and `.env.template` if implementation reveals additional safe configuration placeholders
- [ ] Update `README.md` only if current-status text would otherwise be stale

**Artifacts:**
- `docs/architecture/paper-trading-workspace.md` (modified)
- `docs/architecture/modules.md` (modified)
- `docs/architecture/overview.md` (modified if affected)
- `scripts/README.md` (modified if affected)
- `.env.template` (modified if affected)
- `README.md` (modified if affected)

### Step 6: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet build ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/ibkr-paper-safety-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm `apphost-infrastructure-runtime-tests.sh` passes or cleanly skips when no Docker-compatible engine is available
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 7: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — record implemented paper-only backend, Gateway/session assumptions, and simulation guarantees
- `docs/architecture/modules.md` — update broker, orders, API, and worker current-state notes
- `scripts/README.md` — update `.env`/startup surface if new config or optional Gateway resource is added

**Check If Affected:**
- `docs/architecture/overview.md` — update if AppHost graph/runtime surface changes
- `README.md` — update if current runnable slice changes materially
- `docs/INDEX.md` — update only if new indexed docs are added (none expected)
- `.env.template` — update only for safe additional placeholders discovered during implementation

## Completion Criteria

- [ ] New IBKR broker adapter project exists, builds, and is registered only through safe paper-mode configuration
- [ ] Worker and AppHost wiring preserve existing resource references and do not require real IBKR credentials by default
- [ ] API exposes safe broker status and deterministic order simulation without placing or routing real trades
- [ ] Tests prove disabled/default mode, paper-only guardrails, redaction, simulation behavior, and live-mode rejection
- [ ] Active docs accurately describe the implemented backend slice and remaining limitations

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-016): complete Step N — description`
- **Bug fixes:** `fix(TP-016): description`
- **Tests:** `test(TP-016): description`
- **Hydration:** `hydrate: TP-016 expand Step N checkboxes`

## Do NOT

- Place real orders, route simulated orders to IBKR, or add any live-account trading path
- Commit IBKR usernames, passwords, account IDs, tokens, session cookies, or real Gateway URLs
- Enable broker behavior by default or make live mode a documented option
- Use unofficial IBKR libraries, unofficial Docker images, or scraped/undocumented endpoints as the implementation basis
- Add account reconciliation, positions, executions, database migrations, or LEAN integration in this task
- Break `GET /health`, `GET /api/accounts/overview`, the AppHost worker graph, or the local `.env` contract
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
