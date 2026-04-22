---
status: active
owner: devops
updated: 2026-04-22
summary: Design contract for the future cross-platform `go run` startup command.
see_also:
  - PLAN.md
  - AGENT.md
---

# Startup Script Contract

## Goal

Expose one semantic startup contract on both Unix and Windows through repo-local shims:

- Unix-like: `./go run`
- Windows PowerShell: `./go.ps1 run`
- Windows shell-friendly alias: `go run`

All variants must mean the same thing: start the entire local ATrade stack.

In this repository, `go run` refers to the repo-local shim contract, not the Go toolchain.

## Required Behavior

`go run` must bring up:

- Aspire AppHost
- backend services
- long-running workers
- Next.js frontend
- infrastructure resources managed by Aspire

There must not be separate mandatory commands for the frontend, workers, or infra in the normal local startup path.

## Planned Layout

The script surface should be thin and delegating.

Suggested layout:

```text
ATrade/
├── go                  # POSIX entrypoint
├── go.ps1              # PowerShell entrypoint
├── go.cmd              # Optional Windows shell shim
└── scripts/
    ├── go.run.sh
    ├── go.run.ps1
    ├── go.test.sh
    ├── go.test.ps1
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

- `go run`
- `go test`
- `go build`
- `go lint`
- `go fmt`
- `go agents:dispatch`
- `go plans:check`
- `go docs:check`

## Windows And Unix Rule

Behavior must stay semantically identical across platforms.

- same subcommand names
- same success criteria
- same environment contract where possible
- platform-specific wrappers may differ internally, but not conceptually

## Bootstrap Limitation

This document defines the contract only. The scripts are not implemented in this pass.
