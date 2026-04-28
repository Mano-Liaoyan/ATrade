---
status: active
owner: devops
updated: 2026-04-24
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

The current bootstrap slice now implements the first infrastructure-aware runnable subset of that graph:

- Aspire AppHost
- a minimal `ATrade.Api` backend service managed by Aspire
- the first real Next.js frontend slice managed by Aspire
- Aspire-managed `Postgres`, `TimescaleDB`, `Redis`, and `NATS` resources declared in the AppHost graph
- explicit container-runtime `--pids-limit 2048` settings for the AppHost-managed `postgres`, `timescaledb`, `redis`, and `nats` resources so Podman-backed Docker API runs do not collapse to an effective `pids.max=1`
- deterministic `TS_TUNE_MEMORY=512MB` and `TS_TUNE_NUM_CPUS=2` inputs for the `timescaledb` resource so its init-time tuning script does not crash in the rootless Podman environment used here

Later slices extend that graph with additional backend services, workers, and richer frontend routes.

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

## Next.js Runtime Contract

The AppHost-managed frontend must preserve the same core runtime assumptions as direct startup inside `frontend/`.

- The AppHost still launches the existing `npm run dev` script.
- The AppHost explicitly sets `NODE_ENV=development` for `next dev`; richer repo-specific environment identity must not be encoded through `NODE_ENV`.
- `frontend/next.config.ts` pins `turbopack.root` to the frontend directory so workspace-root detection does not depend on lockfile heuristics higher in the repo.

## Local Port Contract

Developer-controlled local bind ports now come from a repo-level `.env` contract.

- Commit the shared defaults in `.env.example`.
- Keep developer-specific overrides in a repo-root `.env` file, which stays ignored by git.
- When `.env` is absent, AppHost, direct API startup, and the shell test helpers fall back to `.env.example`.

Current variables:

- `ATRADE_API_HTTP_PORT` — direct `ATrade.Api` startup and smoke coverage
- `ATRADE_FRONTEND_DIRECT_HTTP_PORT` — direct `frontend/` `npm run dev` verification path
- `ATRADE_APPHOST_FRONTEND_HTTP_PORT` — AppHost-managed Next.js frontend port

This contract intentionally does **not** move everything into `.env`.

- AppHost internal host/dashboard bindings stay intentionally ephemeral on `127.0.0.1:0`.
- Service/container target ports such as `5432`, `6379`, and `4222` remain fixed where the protocol or container image expects them.

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
- the AppHost-managed frontend runtime path is verified via `tests/apphost/frontend-nextjs-bootstrap-tests.sh`, including `NODE_ENV=development`, preserved AppHost frontend logs, and warning-free startup even when a temporary repo-root lockfile exists
- `tests/apphost/local-port-contract-tests.sh` writes a temporary repo `.env` and verifies that direct API startup, direct frontend startup, and the AppHost frontend/manifest checks all honor changed local port values
- the AppHost manifest now verifies `Postgres`, `TimescaleDB`, `Redis`, `NATS`, `api`, and `frontend` without requiring a container engine via `tests/apphost/apphost-infrastructure-manifest-tests.sh`, including the deterministic `TS_TUNE_*` inputs for `timescaledb`
- when a local Docker-compatible engine is available, `tests/apphost/apphost-infrastructure-runtime-tests.sh` starts `./start run`, verifies the AppHost-managed infra containers get a real process limit (`pids.max > 1`), and confirms `postgres` / `timescaledb` no longer die in their entrypoint scripts
- `./start.ps1 run` and `./start.cmd run` are verified by GitHub Actions on `windows-latest` via `tests/start-contract/start-wrapper-windows.ps1`

## Bootstrap Status

The `run` contract is now bootstrapped in the repository. This covers the first real AppHost-managed slice.

- `./start run` delegates to the Aspire AppHost
- `./start.ps1 run` provides the PowerShell entrypoint
- `./start.cmd run` provides the Windows command prompt entrypoint
- GitHub Actions now runs a Windows-hosted smoke harness for both Windows wrappers
- the current graph hosts the first minimal `ATrade.Api` service, the first real Next.js frontend home page, and named Aspire-managed `postgres`, `timescaledb`, `redis`, and `nats` resources
- developer-controlled local bind ports now come from the repo-level `.env` contract (`.env.example` defaults + optional ignored `.env` overrides)
- the AppHost graph now applies explicit runtime safeguards for the local Podman-backed Docker API path: `--pids-limit 2048` on the four managed infra containers plus deterministic `TS_TUNE_MEMORY=512MB` / `TS_TUNE_NUM_CPUS=2` values for `timescaledb`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh` verifies the direct frontend startup path, stable visible markers for the home page, and the AppHost-managed frontend runtime contract (`NODE_ENV=development` + warning-free Turbopack root resolution)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` verifies that the published AppHost manifest preserves `api` / `frontend`, declares the four managed infrastructure resources, and carries the `timescaledb` tuning inputs in an engine-independent way
- `tests/apphost/apphost-infrastructure-runtime-tests.sh` verifies the live AppHost-managed infra startup path when a local engine is available, including effective `pids.max > 1` and clean `postgres` / `timescaledb` startup

Reserved subcommands such as `test`, `build`, and `lint` remain future work.
