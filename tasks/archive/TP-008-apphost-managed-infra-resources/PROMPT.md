# Task: TP-008 — Extend AppHost with managed infrastructure resources

**Created:** 2026-04-23
**Size:** M

## Review Level: 2 (Moderate)

**Assessment:** Expands the Aspire AppHost graph to declare managed
infrastructure resources (`Postgres`, `TimescaleDB`, `Redis`, `NATS`) and adds
verification/doc updates. Changes local orchestration behavior, but does not yet
introduce domain logic or external provider integrations.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-008-apphost-managed-infra-resources/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Extend `src/ATrade.AppHost` so the local Aspire graph declares the infrastructure
resources promised by the active architecture docs: `Postgres`, `TimescaleDB`,
`Redis`, and `NATS`.

Right now the runnable slice launches `ATrade.Api` and the Next.js frontend, but
it does not yet declare the infrastructure layer that the repo contract says
Aspire will manage. This task should close that gap in the smallest durable way.

## Scope

Deliver the minimum infrastructure-orchestration slice:

1. Add Aspire-managed resource declarations for `Postgres`, `TimescaleDB`,
   `Redis`, and `NATS` in `src/ATrade.AppHost/Program.cs`.
2. Preserve the existing API + frontend bootstrap graph and the `start run`
   contract.
3. Prefer declarative resource setup and manifest/build verification over
   speculative consumers or feature wiring.
4. Add lightweight verification that asserts the AppHost manifest contains the
   expected resources.
5. Update active docs and `PLAN.md` so the current bootstrap slice accurately
   describes the new graph.

## Dependencies

- **None** — architecture docs and bootstrap slices already exist on `main`.

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `docs/INDEX.md`
- `docs/architecture/overview.md`
- `docs/architecture/modules.md`
- `scripts/README.md`
- `src/ATrade.AppHost/ATrade.AppHost.csproj`
- `src/ATrade.AppHost/Program.cs`
- `tests/apphost/api-bootstrap-tests.sh`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`

## Environment

- **Workspace:** Project root
- **Services required:** None for implementation; verification should not assume Docker/Podman is available

## File Scope

- `src/ATrade.AppHost/ATrade.AppHost.csproj`
- `src/ATrade.AppHost/Program.cs`
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (new)
- `scripts/README.md`
- `docs/architecture/overview.md`
- `docs/architecture/modules.md` (if current-slice notes change)
- `PLAN.md`
- `README.md` (if current-status wording changes)

## Steps

### Step 0: Preflight

- [ ] Read the AppHost, docs, and existing apphost test files listed above
- [ ] Confirm `src/ATrade.AppHost/Program.cs` currently declares only the API and frontend resources
- [ ] Confirm no existing test already verifies infra-resource declarations

### Step 1: Declare managed infrastructure resources

- [ ] Update the AppHost project/package surface as needed for Aspire resource helpers
- [ ] Add named Aspire-managed resources for `Postgres`, `TimescaleDB`, `Redis`, and `NATS`
- [ ] Be explicit about how `TimescaleDB` is represented in the local Aspire graph
- [ ] Use stable, readable resource names suitable for future module wiring

### Step 2: Preserve the current bootstrap graph

- [ ] Keep `ATrade.Api` and the Next.js frontend in the AppHost graph
- [ ] Do not add speculative application consumers of the new resources yet
- [ ] Keep broker logic, market-data logic, and worker wiring out of scope

### Step 3: Add verification

- [ ] Create `tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Verify `dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj -- --publisher manifest` includes the expected infra resources and still includes `api` / `frontend`
- [ ] Prefer manifest/build assertions over runtime checks that require a container engine

### Step 4: Update docs and plan

- [ ] Update `scripts/README.md` to describe the new infrastructure-aware bootstrap graph
- [ ] Update `docs/architecture/overview.md` to keep the current-slice note accurate
- [ ] Update `PLAN.md` if this closes or materially changes the infrastructure-orchestration milestone
- [ ] Update `README.md` or `docs/architecture/modules.md` only where current-state wording would otherwise be stale

### Step 5: Verification

- [ ] `dotnet build ATrade.sln`
- [ ] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Confirm docs and plan text match the resulting AppHost graph

### Step 6: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `PLAN.md`, `scripts/README.md`, `docs/architecture/overview.md`
**Check If Affected:** `docs/architecture/modules.md`, `README.md`

## Completion Criteria

- [ ] AppHost declares `Postgres`, `TimescaleDB`, `Redis`, and `NATS`
- [ ] The existing `api` + `frontend` graph is preserved
- [ ] Manifest-based verification covers the new resources
- [ ] Active docs and `PLAN.md` describe the current graph accurately

## Git Commit Convention

- **Implementation:** `feat(TP-008): description`
- **Checkpoints:** `checkpoint: TP-008 description`

## Do NOT

- Add application-level consumers of these resources in this task
- Add broker/data-provider integrations, schemas, or domain logic
- Replace Aspire with ad-hoc scripts or `docker compose`
- Require a local container engine for the primary verification path
- Commit secrets or machine-specific credentials

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
