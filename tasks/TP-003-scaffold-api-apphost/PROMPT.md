# Task: TP-003 — Scaffold `ATrade.Api` and wire it into AppHost

**Created:** 2026-04-23
**Size:** M

## Review Level: 2 (Moderate)

**Assessment:** Adds the first backend project and changes the solution,
Aspire AppHost graph, verification coverage, and implementation-facing docs.
No auth, broker, or database work is included, but the runnable bootstrap graph
changes in multiple places.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-003-scaffold-api-apphost/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Create the first minimal backend service, `ATrade.Api`, and make the existing
`start run` / Aspire AppHost bootstrap bring it up alongside the placeholder
frontend.

This task should stay intentionally small. Deliver one minimal .NET 10 API
project, one stable smoke-verification endpoint, the AppHost wiring needed to
launch it, a small regression test surface, and the doc updates required to
keep the repo contract accurate.

## Scope

Deliver the smallest useful backend scaffold:

1. Add `src/ATrade.Api` as a minimal .NET 10 web project.
2. Add it to `ATrade.sln`.
3. Reference and use `ATrade.ServiceDefaults` in the smallest non-speculative
   way needed for this first API slice.
4. Expose a stable health endpoint (`GET /health`) that can be used by a shell
   smoke test.
5. Update `src/ATrade.AppHost/Program.cs` so Aspire launches the API project
   and the existing placeholder frontend together.
6. Add regression coverage for the new API scaffold and AppHost graph.
7. Update the active docs that describe the current bootstrap slice.

## Dependencies

- **None** — TP-002 is already merged and the architecture docs are available on `main`.

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `docs/INDEX.md`
- `docs/architecture/overview.md`
- `docs/architecture/modules.md`
- `scripts/README.md`
- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.AppHost/ATrade.AppHost.csproj`
- `src/ATrade.ServiceDefaults/Extensions.cs`
- `tests/start-contract/start-wrapper-tests.sh`

## Environment

- **Workspace:** Project root
- **Services required:** None before implementation; AppHost launch is part of verification

## File Scope

- `ATrade.sln`
- `src/ATrade.Api/` (new)
- `src/ATrade.AppHost/ATrade.AppHost.csproj`
- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.ServiceDefaults/Extensions.cs`
- `tests/apphost/api-bootstrap-tests.sh` (new)
- `tests/start-contract/start-wrapper-tests.sh` (if needed)
- `scripts/README.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md` (if bootstrap status wording changes)
- `README.md` (if current runnable-slice wording changes)

## Steps

### Step 0: Preflight

- [ ] Read the context docs and current AppHost / ServiceDefaults / test files listed above
- [ ] Confirm `src/ATrade.Api/` does not yet exist
- [ ] Confirm `ATrade.sln` does not yet include an API project
- [ ] Confirm the current AppHost graph only launches the placeholder frontend

### Step 1: Scaffold `src/ATrade.Api`

- [ ] Create `src/ATrade.Api/ATrade.Api.csproj` as a minimal .NET 10 web project
- [ ] Create `src/ATrade.Api/Program.cs`
- [ ] Add the project to `ATrade.sln`
- [ ] Reference `ATrade.ServiceDefaults`
- [ ] Expose `GET /health` with a stable 200 response suitable for shell smoke verification

### Step 2: Wire shared defaults and AppHost

- [ ] Add only the minimum `ATrade.ServiceDefaults` extension code needed for this scaffold to stay shared and non-speculative
- [ ] Update `src/ATrade.AppHost/ATrade.AppHost.csproj` with the project reference(s) or package surface needed to launch `ATrade.Api`
- [ ] Update `src/ATrade.AppHost/Program.cs` so Aspire launches both `ATrade.Api` and the existing frontend resource
- [ ] Keep infrastructure resources (`Postgres`, `TimescaleDB`, `Redis`, `NATS`) out of scope for this task

### Step 3: Add regression coverage

- [ ] Create `tests/apphost/api-bootstrap-tests.sh`
- [ ] Verify the API project exists, builds into the solution, and serves `GET /health` when launched directly on a fixed localhost URL
- [ ] Update `tests/start-contract/start-wrapper-tests.sh` only where the new AppHost graph changes expected bootstrap behavior

### Step 4: Update docs

- [ ] Update `scripts/README.md` so the current bootstrap slice reflects the new API + placeholder frontend graph
- [ ] Update `docs/architecture/modules.md` so `ATrade.Api` is no longer described as purely planned
- [ ] Update `docs/architecture/overview.md` if its bootstrap-status note needs to mention the new current runnable slice
- [ ] Update `README.md` only if its current-status wording becomes inaccurate after the scaffold lands

### Step 5: Verification

- [ ] `dotnet build ATrade.sln`
- [ ] `bash tests/start-contract/start-wrapper-tests.sh`
- [ ] `bash tests/apphost/api-bootstrap-tests.sh`
- [ ] `timeout 20s dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj`
- [ ] `timeout 20s ./start run`

### Step 6: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `scripts/README.md`, `docs/architecture/modules.md`
**Check If Affected:** `docs/architecture/overview.md`, `README.md`, `plans/senior-engineer/CURRENT.md`, `plans/devops/CURRENT.md`

## Completion Criteria

- [ ] `src/ATrade.Api/` exists and is part of `ATrade.sln`
- [ ] `ATrade.Api` references and uses `ATrade.ServiceDefaults`
- [ ] `GET /health` returns success in the new smoke test
- [ ] Aspire AppHost launches the API and placeholder frontend together
- [ ] Verification commands pass
- [ ] Active docs reflect the new current bootstrap slice

## Git Commit Convention

- **Implementation:** `feat(TP-003): description`
- **Checkpoints:** `checkpoint: TP-003 description`

## Do NOT

- Add `Postgres`, `TimescaleDB`, `Redis`, or `NATS` resources in this slice
- Replace the placeholder frontend with a real Next.js app yet
- Add auth, broker integrations, market-data integrations, or trading logic
- Split the backend into multiple feature modules in this task
- Change the Windows wrapper contract or reserved `start` subcommands

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
