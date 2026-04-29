# Task: TP-009 — Scaffold first feature-module shells and the IBKR worker shell

**Created:** 2026-04-23
**Size:** M

## Review Level: 2 (Moderate)

**Assessment:** Adds compileable project shells under `src/` and `workers/` to
turn the architecture docs into real repository structure. Changes the solution
layout, but keeps domain logic and runtime wiring intentionally minimal.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-009-feature-module-and-ibkr-worker-shells/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Create the first implementation-facing project shells for planned backend
feature modules and the first worker process so the repository structure starts
to match `docs/architecture/modules.md`.

Today the repo has the AppHost, shared defaults, a minimal API, and the Next.js
frontend. This task should add the next layer of concrete structure without
pretending the feature modules or broker integration are functional yet.

## Scope

Deliver the minimum useful project-shell slice:

1. Create minimal .NET 10 class-library shells for:
   - `src/ATrade.Accounts`
   - `src/ATrade.Orders`
   - `src/ATrade.MarketData`
2. Create one minimal worker-service shell for:
   - `workers/ATrade.Ibkr.Worker`
3. Add the new projects to `ATrade.sln`.
4. Keep the shells compileable and aligned with the current module docs, but do
   not add domain behavior, broker connectivity, or AppHost wiring yet.
5. Add lightweight verification and update active docs where the current-state
   wording would otherwise stay stale.

## Dependencies

- **None** — this is structure-first scaffolding and does not need infra wiring to land.

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `docs/INDEX.md`
- `docs/architecture/overview.md`
- `docs/architecture/modules.md`
- `ATrade.sln`
- `src/ATrade.Api/ATrade.Api.csproj`
- `src/ATrade.Api/Program.cs`
- `src/ATrade.ServiceDefaults/ATrade.ServiceDefaults.csproj`
- `src/ATrade.ServiceDefaults/Extensions.cs`
- `src/ATrade.AppHost/Program.cs`

## Environment

- **Workspace:** Project root
- **Services required:** None

## File Scope

- `ATrade.sln`
- `src/ATrade.Accounts/` (new)
- `src/ATrade.Orders/` (new)
- `src/ATrade.MarketData/` (new)
- `workers/ATrade.Ibkr.Worker/` (new)
- `tests/scaffolding/project-shells-tests.sh` (new)
- `docs/architecture/modules.md`
- `docs/architecture/overview.md` (if current-slice notes change)
- `README.md` (if repository-map/current-status wording changes)
- `PLAN.md` (if milestone wording changes)

## Steps

### Step 0: Preflight

- [ ] Read the module docs, solution, and existing project patterns listed above
- [ ] Confirm the target module/worker projects do not yet exist
- [ ] Confirm `workers/` is still absent or does not yet contain a real worker project

### Step 1: Scaffold feature-module shells

- [ ] Create `ATrade.Accounts`, `ATrade.Orders`, and `ATrade.MarketData` as minimal compileable class libraries
- [ ] Add a tiny non-speculative placeholder type in each project so the shells are not empty
- [ ] Keep namespaces and project names aligned with the active module docs

### Step 2: Scaffold the IBKR worker shell

- [ ] Create `workers/ATrade.Ibkr.Worker` as a minimal worker-service project
- [ ] Keep the worker compileable and intentionally inert
- [ ] Reference shared defaults only where appropriate for a minimal worker shell
- [ ] Do not connect to IBKR, NATS, or databases in this task

### Step 3: Wire the solution, not the runtime graph

- [ ] Add all new projects to `ATrade.sln`
- [ ] Do not add the worker to `src/ATrade.AppHost/Program.cs` yet unless absolutely required for build-only scaffolding
- [ ] Keep runtime behavior unchanged outside the new compileable shells

### Step 4: Add lightweight verification

- [ ] Create `tests/scaffolding/project-shells-tests.sh`
- [ ] Verify the expected project files exist and are included in `ATrade.sln`
- [ ] Verify the solution builds with the new shells present

### Step 5: Update docs and plan

- [ ] Update `docs/architecture/modules.md` so it distinguishes existing shells from future functional work
- [ ] Update `README.md` or `docs/architecture/overview.md` only where current-state wording becomes inaccurate
- [ ] Update `PLAN.md` if the milestone wording should now reflect this scaffolding progress

### Step 6: Verification

- [ ] `dotnet build ATrade.sln`
- [ ] `bash tests/scaffolding/project-shells-tests.sh`
- [ ] Confirm docs accurately describe the new shells as scaffolding, not implemented features

### Step 7: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `docs/architecture/modules.md`
**Check If Affected:** `README.md`, `docs/architecture/overview.md`, `PLAN.md`

## Completion Criteria

- [ ] The three feature-module shell projects exist under `src/`
- [ ] The IBKR worker shell exists under `workers/`
- [ ] All new projects are part of `ATrade.sln`
- [ ] The solution builds successfully with the new shells
- [ ] Docs describe the new shells accurately without overstating functionality

## Git Commit Convention

- **Implementation:** `feat(TP-009): description`
- **Checkpoints:** `checkpoint: TP-009 description`

## Do NOT

- Implement trading, account, order, or market-data behavior in this task
- Connect the worker shell to IBKR, NATS, Redis, Postgres, or TimescaleDB yet
- Add the new worker to the AppHost runtime graph as if it were production-ready
- Create speculative abstractions or placeholder business logic with no immediate structural value
- Claim the new shells are functionally complete in docs or plan updates

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
