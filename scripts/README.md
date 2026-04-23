---
status: active
owner: devops
updated: 2026-04-23
summary: Bootstrap status and contract for the cross-platform `start run` entrypoints.
see_also:
  - ../PLAN.md
  - ../AGENTS.md
---

# Startup Script Contract

## Goal

Expose one semantic startup contract on both Unix and Windows through repo-local shims:

- Unix-like: `./start run`
- Windows PowerShell: `./start.ps1 run`
- Windows Command Prompt: `./start.cmd run`

All variants must mean the same thing: start the currently implemented local ATrade stack, growing toward the full target graph over time.

In this repository, `start run` refers to the repo-local shim contract, not the Windows shell built-in.

Windows documentation must use an explicit relative path when invoking the repo-local shim.

## Required Behavior

The long-term `start run` contract is to bring up:

- Aspire AppHost
- backend services
- long-running workers
- Next.js frontend
- infrastructure resources managed by Aspire

There must not be separate mandatory commands for the frontend, workers, or infra in the normal local startup path.

The current bootstrap slice intentionally implements only the first runnable subset of that graph:

- Aspire AppHost
- a minimal `ATrade.Api` backend service managed by Aspire
- the first real Next.js frontend slice managed by Aspire

Later slices extend that graph with additional backend services, workers, richer frontend routes, and infrastructure resources.

## Planned Layout

The script surface should be thin and delegating.

Suggested layout:

```text
ATrade/
├── start               # POSIX entrypoint
├── start.ps1           # PowerShell entrypoint
├── start.cmd           # Windows command prompt entrypoint
└── scripts/
    ├── start.run.sh
    ├── start.run.ps1
    ├── start.test.sh
    ├── start.test.ps1
    └── ...
```

## AppHost Contract

The script delegates to Aspire AppHost, not to a pile of per-service shell commands.

Target AppHost responsibilities:

- run the main .NET API host
- run worker services
- run the Next.js app as an Aspire-managed node resource
- start Postgres, TimescaleDB, Redis, and NATS as Aspire-managed resources

## Next.js Orchestration Requirement

The frontend is no longer Blazor.

Aspire must orchestrate the Next.js app directly so the frontend participates in the same local graph, environment setup, and lifecycle as the .NET services.

## Reserved Commands

Only `run` is mandatory for the first implementation wave, but the contract reserves:

- `start run`
- `start test`
- `start build`
- `start lint`
- `start fmt`
- `start agents:dispatch`
- `start plans:check`
- `start docs:check`

## Windows And Unix Rule

Behavior must stay semantically identical across platforms.

- same subcommand names
- same success criteria
- same environment contract where possible
- platform-specific wrappers may differ internally, but not conceptually

## Current Verification Scope

- `./start run` and direct AppHost startup are verified in this repository's Linux environment
- direct `ATrade.Api` startup and `GET /health` smoke coverage are verified in this repository's Linux environment
- direct frontend startup and the Next.js home-page markers are verified in this repository's Linux environment via `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `./start.ps1 run` and `./start.cmd run` are verified by GitHub Actions on `windows-latest` via `tests/start-contract/start-wrapper-windows.ps1`

## Bootstrap Status

The `run` contract is now bootstrapped in the repository for the first real AppHost-managed slice.

- `./start run` delegates to the Aspire AppHost
- `./start.ps1 run` provides the PowerShell entrypoint
- `./start.cmd run` provides the Windows command prompt entrypoint
- GitHub Actions now runs a Windows-hosted smoke harness for both Windows wrappers
- the current graph hosts the first minimal `ATrade.Api` service and the first real Next.js frontend home page
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh` verifies the direct frontend startup path plus stable visible markers for the home page
- infrastructure resources remain intentionally out of scope for this bootstrap slice

Reserved subcommands such as `test`, `build`, and `lint` remain future work.
