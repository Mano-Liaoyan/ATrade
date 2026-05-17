---
status: active
owner: maintainer
updated: 2026-05-17
summary: Local runtime and deployment diagram for start shims, Compose-managed infrastructure, Aspire app services, optional iBeam, and optional LEAN.
see_also:
  - ../../INDEX.md
  - ../overview.md
  - ../modules.md
  - ../analysis-engines.md
  - ../../../scripts/README.md
  - ../../../README.md
  - ../../../PLAN.md
---

# Local Runtime And Deployment

The repo-local `start run` contract starts Compose-managed infrastructure first,
then delegates app-service orchestration to Aspire AppHost. Compose remains the
default infrastructure owner; AppHost launches the API, worker, and frontend.

```mermaid
flowchart TD
    dev["Developer"]
    shims["Repo-local start shims<br/>./start run<br/>./start.ps1 run<br/>./start.cmd run"]
    env["Local runtime contract<br/>.env.template -> ignored .env -> process env"]
    composeHelper["scripts/compose-infra.* up"]
    compose["Compose project"]
    apphost["Aspire AppHost"]
    dashboard["Aspire dashboard and telemetry"]

    subgraph infra["Compose-managed infrastructure"]
        postgres["Postgres<br/>atrade database<br/>named data volume"]
        timescale["TimescaleDB<br/>atrade_marketdata database<br/>named data volume"]
        redis["Redis<br/>ephemeral cache"]
        nats["NATS<br/>internal events"]
        ibeam["Optional ibkr-gateway<br/>iBeam profile"]
        lean["Optional lean-engine<br/>LEAN profile"]
    end

    subgraph apps["Aspire-managed app services"]
        api["ATrade.Api"]
        worker["ATrade.Ibkr.Worker"]
        frontend["Next.js frontend"]
    end

    dev --> shims
    shims --> env
    shims --> composeHelper
    composeHelper --> compose
    compose --> postgres
    compose --> timescale
    compose --> redis
    compose --> nats
    compose -.-> ibeam
    compose -.-> lean

    shims --> apphost
    env --> apphost
    apphost --> api
    apphost --> worker
    apphost --> frontend
    apphost --> dashboard

    api -->|"localhost connection string"| postgres
    api -->|"localhost connection string"| timescale
    api -->|"localhost connection string"| redis
    api -->|"localhost connection string"| nats
    worker -->|"localhost connection string"| postgres
    worker -->|"localhost connection string"| redis
    worker -->|"localhost connection string"| nats
    frontend -->|"browser-safe API base URL"| api

    api -.->|"safe local provider settings"| ibeam
    worker -.->|"safe paper readiness checks"| ibeam
    api -.->|"managed runtime metadata"| lean
```

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Shim as start run shim
    participant Env as Runtime contract loader
    participant Compose as Compose helper
    participant Infra as Local infrastructure
    participant AppHost as Aspire AppHost
    participant Apps as API, worker, frontend

    Dev->>Shim: run repo-local start command
    Shim->>Env: overlay .env.template, ignored .env, process env
    Shim->>Compose: start infrastructure
    Compose->>Infra: Postgres, TimescaleDB, Redis, NATS
    opt Broker integration enabled with non-placeholder local credentials
        Compose->>Infra: start iBeam profile
    end
    opt LEAN selected in Docker mode
        Compose->>Infra: start LEAN profile
    end
    Shim->>AppHost: launch AppHost
    Env->>AppHost: pass non-secret settings and secret references
    AppHost->>Apps: launch API, worker, Next.js frontend
    AppHost-->>Dev: expose dashboard and app-service telemetry
```

## How To Read It

- `ATRADE_INFRASTRUCTURE_MODE=compose` is the default. In that mode Postgres,
  TimescaleDB, Redis, and NATS are owned by Compose and do not appear as default
  Aspire dashboard resources.
- AppHost injects direct localhost connection strings into app services while
  keeping password-bearing values as secret references.
- Compose infrastructure stays warm after AppHost exits until the developer
  explicitly stops it.
- The `ibkr-gateway` and `lean-engine` paths are opt-in local profiles. They are
  enabled only by ignored or process-local settings that make the runtime safe.
- `ATRADE_INFRASTRUCTURE_MODE=apphost` remains only a diagnostic fallback where
  Aspire can declare infrastructure containers itself.
