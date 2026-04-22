---
status: active
owner: devops
updated: 2026-04-22
summary: Approved design for the first bootstrap implementation of the cross-platform `start run` contract and minimal Aspire AppHost.
see_also:
  - scripts/README.md
  - PLAN.md
  - plans/devops/CURRENT.md
---

# `start run` Bootstrap Design

## Goal

Implement the first real version of the repository-local `start run` contract so Unix and Windows entrypoints all start through Aspire AppHost instead of a placeholder script surface.

## Scope

This design covers the first bootstrap slice only.

It includes:

- thin cross-platform command shims
- a hand-authored Aspire 13.2 AppHost project
- a small shared .NET solution structure
- a minimal JavaScript frontend placeholder that Aspire can manage
- initial tests for command delegation and unsupported subcommands
- documentation updates required for the new durable repository surface

It does not include:

- real backend APIs
- worker services
- Postgres or TimescaleDB wiring
- NATS wiring
- Redis unless it is needed as the safest bootstrap resource during implementation
- any production trading logic

## Why This Slice

The repository contract already says `start run` is the single startup command. A shim that only prints "not implemented" would preserve documentation but still fail the core local startup promise.

The repository also does not yet contain any `.sln`, `.csproj`, frontend, or AppHost files. A full-stack bootstrap in one pass would create too much surface area for the first real implementation. The first slice should therefore establish the startup contract and the smallest runnable graph behind it, then extend that graph in later work.

## Chosen Approach

Use a real cross-platform shim now, backed by a minimal hand-authored Aspire AppHost.

### Alternatives Considered

#### 1. Shim-only placeholder

Create `start`, `start.ps1`, and `start.cmd` now, but have them exit with a friendly "AppHost not implemented yet" message.

This was rejected because it satisfies the script surface without satisfying the repository's main operational contract.

#### 2. Full infrastructure bootstrap in one pass

Implement the shims, AppHost, API, workers, frontend, Postgres, TimescaleDB, Redis, and NATS immediately.

This was rejected because the repository is still empty and the first implementation slice would become too large to verify safely.

#### 3. Minimal real AppHost bootstrap

Implement the shims together with a small but real AppHost project and a placeholder frontend resource.

This is the chosen approach because it delivers the semantic `start run` contract now while keeping the first slice small and extensible.

## Architecture

The startup surface remains intentionally thin.

- `start`, `start.ps1`, and `start.cmd` are wrapper entrypoints only.
- `scripts/start.run.sh` and `scripts/start.run.ps1` contain the platform-specific `run` implementation.
- those scripts delegate to `dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj`
- Aspire AppHost owns the local graph and is the only place where orchestration decisions live.

This keeps platform wrappers simple while preserving one orchestration model across Unix and Windows.

## Planned Repository Additions

### Script Surface

- `start`
- `start.ps1`
- `start.cmd`
- `scripts/start.run.sh`
- `scripts/start.run.ps1`

Only the `run` subcommand is implemented in this slice. Other reserved commands still exist only as documented future contract.

### .NET Bootstrap

- `ATrade.sln`
- `src/ATrade.AppHost/ATrade.AppHost.csproj`
- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.ServiceDefaults/ATrade.ServiceDefaults.csproj`

`ATrade.ServiceDefaults` is added now because it is a standard shared bootstrap point for later .NET services, even if the first slice uses very little of it.

### Frontend Bootstrap

- `frontend/package.json`
- `frontend/server.js`

The frontend is a minimal JavaScript placeholder process that exposes a predictable dev server command. It is intentionally small so Aspire can manage a real frontend resource before the full Next.js application exists.

## AppHost Contract For This Slice

The AppHost must be real and runnable.

For the first slice it should:

- start successfully through `dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj`
- include the minimal AppHost launch profile needed for direct local `dotnet run` startup without extra shell-exported dashboard bootstrap variables
- include a JavaScript-managed frontend resource using the Aspire JavaScript hosting package line
- provide a clear extension point for later API, worker, and infrastructure resources

The frontend resource should be wired through `Aspire.Hosting.JavaScript`, which is the current 13.2 package line. The older `Aspire.Hosting.NodeJs` package line exists but has been superseded for new work.

Infrastructure resources are deferred to the next slice unless one proves necessary to make the first graph viable. If one resource is introduced early, Redis is the preferred candidate because it is the smallest operational addition among the currently known infrastructure targets.

## Platform Semantics

All entrypoints must present the same behavior.

- `./start run`
- `./start.ps1 run`
- `./start.cmd run`

Windows documentation must use an explicit relative path because `start` is already a shell built-in on Windows platforms.

They must:

- accept the same subcommand name
- fail with a non-zero exit code for unsupported subcommands
- print a short usage message for unsupported subcommands
- delegate to the same AppHost project path

They must not:

- contain orchestration logic themselves
- diverge in feature support by platform

## Error Handling

The script layer should fail early and clearly for:

- missing subcommand
- unsupported subcommand
- missing `dotnet` runtime or SDK
- missing AppHost project path

The messages should be short and action-oriented. The wrappers should not attempt advanced recovery in this slice.

## Testing Strategy

This slice follows TDD.

Tests are required before production code for the script surface.

The first test set should verify:

- the POSIX `start` wrapper dispatches `run` to `scripts/start.run.sh`
- the PowerShell wrapper dispatches `run` to `scripts/start.run.ps1`
- unsupported subcommands exit non-zero
- unsupported subcommands print a stable usage message
- the run scripts target `src/ATrade.AppHost/ATrade.AppHost.csproj`

Verification after implementation should include:

- targeted script tests
- `dotnet build` for the solution
- a direct run of the AppHost entrypoint or equivalent bootstrap verification

## Documentation Changes

The implementation must update durable docs in the same change.

Required documentation work:

- add this approved design doc
- add this doc to `docs/INDEX.md`
- update `scripts/README.md` so it no longer claims the scripts are entirely unimplemented
- update `plans/devops/CURRENT.md` when the implementation slice is completed or materially advanced

## Dependencies And Constraints

Known local environment facts:

- `.NET SDK 10.0.202` is installed
- `node v24.15.0` is installed
- Aspire templates are not installed locally, so AppHost must be hand-authored rather than scaffolded from templates

Known current package availability:

- `Aspire.Hosting.AppHost 13.2.3`
- `Aspire.Hosting.JavaScript 13.2.3`
- `Aspire.Hosting.PostgreSQL 13.2.3`
- `Aspire.Hosting.Redis 13.2.3`
- `Aspire.Hosting.Nats 13.2.3`

## Deferred Work

The next implementation slice should extend this bootstrap with:

- real .NET API projects
- worker services
- full Aspire-managed infrastructure resources
- a real Next.js application in place of the placeholder frontend process
- broader `start` subcommand coverage such as `test`, `build`, and `lint`

## Approval

This design was approved by the user on 2026-04-22 and is the implementation authority for the first `start run` bootstrap slice.
