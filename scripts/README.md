---
status: active
owner: maintainer
updated: 2026-05-01
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
- a minimal `ATrade.Api` backend service managed by Aspire, with stable `GET /health` and `GET /api/accounts/overview` endpoints
- an AppHost-managed `ATrade.Ibkr.Worker` shell process managed by Aspire
- the first real Next.js frontend slice managed by Aspire
- Aspire-managed `Postgres`, `TimescaleDB`, `Redis`, and `NATS` resources declared in the AppHost graph
- an optional AppHost-managed `ibkr-gateway` iBeam container using `voyz/ibeam:latest` when broker integration is enabled locally with real ignored `.env` credentials
- provider-neutral analysis endpoints with an optional LEAN analysis provider selected by ignored `.env` runtime settings, plus an Aspire-visible `lean-engine` runtime container when LEAN Docker mode is selected
- explicit AppHost resource references from `api` to `Postgres`, `TimescaleDB`, `Redis`, and `NATS`, plus matching worker references from `ibkr-worker` to `Postgres`, `Redis`, and `NATS`
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
- The trading workspace client reads `NEXT_PUBLIC_ATRADE_API_BASE_URL` for browser-side HTTP/SignalR calls, falls back to the TP-015 `ATRADE_FRONTEND_API_BASE_URL` name when available, and otherwise uses the local API default at `http://127.0.0.1:5181`.
- The AppHost-managed frontend receives both `NEXT_PUBLIC_ATRADE_API_BASE_URL` and `ATRADE_FRONTEND_API_BASE_URL` pointing at the repo-level `ATRADE_API_HTTP_PORT` so browser fetches and SignalR negotiation target the local API.

## Local Configuration Contract

Developer-controlled local bind ports and paper-trading workspace placeholders
now come from a repo-level `.env` contract.

- Commit shared defaults only in `.env.template`.
- To configure a local machine, copy `.env.template` to repo-root `.env`; keep `.env` ignored by git.
- Store any real broker usernames, passwords, tokens, session cookies, or real account identifiers only in that ignored `.env` (or a separate local secret source), never in committed files.
- When `.env` is absent, AppHost, direct API startup, and the shell test helpers fall back to `.env.template` with broker integration disabled.

The .NET side resolves this contract through `ATrade.ServiceDefaults`' shared
local runtime contract loader. That loader reads `.env.template`, overlays
ignored `.env` when present, overlays process environment variables last,
validates local port and Docker volume values, exposes resolved non-secret
settings, and classifies database passwords plus IBKR username/password/account
id values as secret. The Unix and PowerShell startup shims mirror the same
`.env.template` → `.env` → process environment precedence for startup-time
values such as the Aspire dashboard UI port.

### Current local port variables

- `ATRADE_API_HTTP_PORT` — direct `ATrade.Api` startup and smoke coverage; committed default `5181`
- `ATRADE_FRONTEND_DIRECT_HTTP_PORT` — direct `frontend/` `npm run dev` verification path; committed default `3111`
- `ATRADE_APPHOST_FRONTEND_HTTP_PORT` — AppHost-managed Next.js frontend port; committed default `3000`
- `ATRADE_ASPIRE_DASHBOARD_HTTP_PORT` — Aspire dashboard UI bind port used by `./start run`, `./start.ps1 run`, and `./start.cmd run`; the committed default `0` preserves an ephemeral loopback dashboard URL, while a non-zero value in ignored `.env` pins the dashboard UI to `http://127.0.0.1:<port>`

The dashboard OTLP endpoint remains intentionally ephemeral on
`ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL=http://127.0.0.1:0`; only the human-facing
Aspire dashboard UI port is part of the `.env` contract.

### AppHost database persistence variables

The AppHost-managed `postgres` and `timescaledb` resources are volume-backed so
backend-owned workspace preferences and provider-backed market-data cache rows
survive a full `start run` stop/start cycle rather than only an API process
restart.

- `ATRADE_POSTGRES_DATA_VOLUME` — Docker-compatible named volume used for the
  AppHost `postgres` data directory; committed default is
  `atrade-postgres-data`. Override in ignored `.env` when multiple worktrees
  need isolated local databases.
- `ATRADE_POSTGRES_PASSWORD` — fake local-dev placeholder passed as a secret
  Aspire parameter to `postgres` and dependent services. The value must stay
  stable for the lifetime of a named data volume; if an existing local volume was
  initialized with a different password, either set that same value in ignored
  `.env` or intentionally remove/recreate the volume after confirming no local
  data is needed.
- `ATRADE_TIMESCALEDB_DATA_VOLUME` — Docker-compatible named volume used for the
  AppHost `timescaledb` data directory; committed default is
  `atrade-timescaledb-data`. Override in ignored `.env` when multiple worktrees
  need isolated market-data cache databases.
- `ATRADE_TIMESCALEDB_PASSWORD` — fake local-dev placeholder passed as a secret
  Aspire parameter to `timescaledb` and `api`. Like Postgres, the value must stay
  stable for the lifetime of a named TimescaleDB data volume; if an existing
  local volume was initialized with a different password, either set that value
  in ignored `.env` or intentionally remove/recreate the volume after confirming
  no local cache data is needed.

Do not remove the shared default volumes from automated tests. The AppHost
watchlist, Timescale cache reboot, manifest, and runtime infrastructure tests
override database volume/password settings with unique `atrade-postgres-*-test-*`
or `atrade-timescaledb-*-test-*` values and remove only those temporary volumes.

### Paper-trading, iBeam, market-data cache, and LEAN runtime placeholders

These placeholders define the safe local IBKR/iBeam, market-data cache, and
analysis-runtime contract without committing real credentials or enabling broker
behavior by default.

- `ATRADE_BROKER_INTEGRATION_ENABLED` — feature flag for local broker/iBeam wiring; committed default stays `false`
- `ATRADE_BROKER_ACCOUNT_MODE` — committed default stays `Paper`; live mode remains rejected by the API, worker, and simulation guardrails
- `ATRADE_IBKR_GATEWAY_URL` — local iBeam/IBKR Gateway Client Portal API base URL; committed default is `https://127.0.0.1:5000` because `voyz/ibeam:latest` serves HTTPS on the local gateway host port
- `ATRADE_IBKR_GATEWAY_PORT` — local host bind port for the iBeam Client Portal API; committed default is `5000`; AppHost maps this host port to the container's internal Client Portal port `5000`
- `ATRADE_IBKR_GATEWAY_IMAGE` — local iBeam image/tag; committed default is the user-approved `voyz/ibeam:latest`
- `ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS` — optional timeout for the official iBeam/Gateway status client; committed default stays a paper-safe low value
- `ATRADE_IBKR_USERNAME` — fake `IBKR_USERNAME` placeholder; replace only in ignored `.env` with the IBKR paper-login username, which AppHost maps to iBeam `IBEAM_ACCOUNT`
- `ATRADE_IBKR_PASSWORD` — fake `IBKR_PASSWORD` placeholder; replace only in ignored `.env` with the IBKR paper-login password, which AppHost maps to iBeam `IBEAM_PASSWORD`
- `ATRADE_IBKR_PAPER_ACCOUNT_ID` — fake `IBKR_ACCOUNT_ID` placeholder for a paper account identifier; real values stay only in ignored `.env` and surface only as redacted booleans in status payloads
- `ATRADE_FRONTEND_API_BASE_URL` — legacy/frontend-to-API base URL for the paper-trading workspace
- `NEXT_PUBLIC_ATRADE_API_BASE_URL` — browser-safe Next.js public API base URL used by the trading workspace HTTP and SignalR clients; committed default mirrors `ATRADE_FRONTEND_API_BASE_URL`
- `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` — non-secret TimescaleDB market-data cache freshness window; committed default is `30`, meaning API cache-aside reads for trending, candles, and indicator candle inputs may use provider-backed rows written within the last 30 minutes before refreshing from the provider. Because the AppHost `timescaledb` data directory is volume-backed, fresh rows can survive a full `start run` stop/start cycle and be served after reboot without another IBKR/iBeam provider call; stale rows still require provider refresh and are not returned as current when refresh fails.
- `ATRADE_ANALYSIS_ENGINE` — analysis provider selector; committed default is `none`, set ignored `.env` to `Lean` to enable the LEAN provider
- `ATRADE_LEAN_RUNTIME_MODE` — official LEAN runtime invocation mode (`cli` by default; `docker` selects the AppHost-managed `lean-engine` container path)
- `ATRADE_LEAN_CLI_COMMAND` — local official LEAN CLI command/path; committed default is `lean`
- `ATRADE_LEAN_DOCKER_COMMAND` — Docker-compatible command/path for containerized LEAN invocation; committed default is `docker`
- `ATRADE_LEAN_DOCKER_IMAGE` — LEAN runtime image used by the AppHost-managed `lean-engine`; committed default is `quantconnect/lean:latest` because Docker mode invokes the open-source LEAN engine launcher directly and does not require a paid LEAN CLI organization workspace
- `ATRADE_LEAN_WORKSPACE_ROOT` — non-secret local directory for generated LEAN workspaces; committed default is the ignored/generated `artifacts/lean-workspaces` path so AppHost can bind-mount the same host directory into `lean-engine`
- `ATRADE_LEAN_TIMEOUT_SECONDS` — analysis runtime timeout; committed default is `45`
- `ATRADE_LEAN_KEEP_WORKSPACE` — optional debugging flag for generated LEAN workspaces; committed default is `false`
- `ATRADE_LEAN_MANAGED_CONTAINER_NAME` — stable local container name passed to `ATrade.Api` so Docker-mode execution can use the AppHost-managed runtime; committed default is `atrade-lean-engine` (override in ignored `.env` if multiple worktrees need simultaneous LEAN Docker sessions)
- `ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT` — container path where `ATRADE_LEAN_WORKSPACE_ROOT` is mounted; committed default is `/workspace`

To show and use the LEAN Docker runtime in the Aspire dashboard, copy
`.env.template` to ignored `.env`, set `ATRADE_ANALYSIS_ENGINE=Lean`, set
`ATRADE_LEAN_RUNTIME_MODE=docker`, keep or override the non-secret image,
workspace, timeout, and managed-container values, and run `./start run`. The
AppHost then declares `lean-engine`, bind-mounts the host workspace root into the
container, passes the safe LEAN settings to `api`, and the LEAN executor uses
`docker exec` to invoke `dotnet QuantConnect.Lean.Launcher.dll` against a
generated local engine config inside that managed container. This Docker path
uses the open-source LEAN engine image directly and does not require a paid LEAN
CLI organization workspace. If the Docker command, container, image, or runtime
is unavailable, analysis requests return explicit `analysis-engine-unavailable`
failures with no fake signals/metrics/backtest; when Docker is unavailable the
optional smoke test reports a clear skip. CLI mode remains available by keeping
`ATRADE_LEAN_RUNTIME_MODE=cli` and configuring `ATRADE_LEAN_CLI_COMMAND`, but the
official `lean backtest` CLI path may require an initialized LEAN workspace and a
QuantConnect organization tier accepted by the CLI.

To start local iBeam for user-driven IBKR API login, copy `.env.template` to
`.env`, set `ATRADE_BROKER_INTEGRATION_ENABLED=true`, keep
`ATRADE_BROKER_ACCOUNT_MODE=Paper`, keep `ATRADE_IBKR_GATEWAY_URL` on the local
HTTPS gateway URL (`https://127.0.0.1:<ATRADE_IBKR_GATEWAY_PORT>`), and replace
only the fake `ATRADE_IBKR_USERNAME`, `ATRADE_IBKR_PASSWORD`, and
`ATRADE_IBKR_PAPER_ACCOUNT_ID` placeholders in ignored `.env`. The AppHost then
adds `ibkr-gateway` with `voyz/ibeam:latest`, publishes the container's
internal Client Portal port `5000` on the configured HTTPS host port, mounts the
repo-local non-secret `src/ATrade.AppHost/ibeam-inputs/conf.yaml` into
`/srv/inputs` read-only so Client Portal accepts loopback/private Docker bridge
callers used by Aspire, passes only `IBEAM_ACCOUNT` and `IBEAM_PASSWORD` to that
container via Aspire secret parameters, and keeps the raw username, password,
and account id out of manifests and status payloads. The Client Portal
certificate is a local development/self-signed certificate; ATrade's HTTP
clients send a stable Client Portal-compatible user agent and trust that
certificate condition only for loopback/local iBeam HTTPS traffic, never
disabling certificate validation globally or for arbitrary hosts.

This contract intentionally does **not** move everything into `.env`.

- AppHost internal host bindings other than the dashboard UI, including the dashboard OTLP endpoint, stay intentionally ephemeral on `127.0.0.1:0`.
- Service/container target ports such as `5432`, `6379`, `4222`, and iBeam's internal Client Portal port `5000` remain fixed where the protocol or container image expects them; configure only their host bind ports where supported.
- Real broker credentials, session cookies, tokens, real account identifiers, or any value that would create a live-trading path must never appear in `.env.template`. Dashboard, LEAN, `ATRADE_POSTGRES_DATA_VOLUME`, `ATRADE_TIMESCALEDB_DATA_VOLUME`, and `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES` settings are non-secret local runtime settings only and must not contain broker credentials. The committed `ATRADE_POSTGRES_PASSWORD` and `ATRADE_TIMESCALEDB_PASSWORD` values are obvious fake local-dev placeholders; replace them only in ignored `.env` if your own local database volumes need different stable passwords.

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

## Solution File Contract

Repository-level .NET verification commands use `ATrade.slnx` as the
authoritative solution file:

```bash
dotnet test ATrade.slnx --nologo --verbosity minimal
dotnet build ATrade.slnx --nologo --verbosity minimal
```

`ATrade.sln` remains temporarily as a non-authoritative compatibility artifact
for older tooling only. Startup and verification scripts should inspect, build,
and test `ATrade.slnx` instead of adding new active `ATrade.sln` guidance.

## Current Verification Scope

- `./start run` and direct AppHost startup are verified in this repository's Linux environment
- direct `ATrade.Api` startup, `GET /health` smoke coverage, the read-only Accounts overview endpoint, the safe IBKR status endpoint, deterministic paper-order simulation, provider-backed market-data unavailable states, and analysis endpoints are verified in this repository's Linux environment via `tests/apphost/api-bootstrap-tests.sh`, `tests/apphost/accounts-feature-bootstrap-tests.sh`, `tests/apphost/ibkr-paper-safety-tests.sh`, `tests/apphost/market-data-feature-tests.sh`, `tests/apphost/analysis-engine-contract-tests.sh`, and `tests/apphost/lean-analysis-engine-tests.sh`
- direct frontend startup and the Next.js home-page markers are verified in this repository's Linux environment via `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- the frontend trading workspace source/build/direct-runtime checks are verified via `tests/apphost/frontend-trading-workspace-tests.sh`, including the chart/SignalR dependencies, no proprietary TradingView package, backend watchlist source, direct API/frontend startup, landing/chart markers, timeframe controls, SignalR label, analysis panel markers, and no-real-orders marker
- the AppHost-managed frontend runtime path is verified via `tests/apphost/frontend-nextjs-bootstrap-tests.sh`, including `NODE_ENV=development`, preserved AppHost frontend logs, and warning-free startup even when a temporary repo-root lockfile exists
- `tests/apphost/local-port-contract-tests.sh` writes a temporary repo `.env` and verifies that direct API startup, direct frontend startup, the AppHost frontend/manifest checks, and the optional non-zero Aspire dashboard UI port all honor changed local port values
- the AppHost manifest now verifies `Postgres`, `TimescaleDB`, `Redis`, `NATS`, `api`, and `frontend` without requiring a container engine via `tests/apphost/apphost-infrastructure-manifest-tests.sh`, including writable AppHost Postgres and TimescaleDB data volumes and deterministic `TS_TUNE_*` inputs for `timescaledb`
- `tests/apphost/lean-aspire-runtime-tests.sh` verifies LEAN disabled defaults, the Docker-mode `lean-engine` AppHost resource and workspace mount, API LEAN engine discovery from AppHost env handoff, explicit unavailable runtime responses, and optional managed-runtime smoke skipping when Docker or the configured image is unavailable
- `tests/apphost/apphost-worker-resource-wiring-tests.sh` publishes the AppHost manifest without starting containers and verifies that `ibkr-worker` is part of the graph while `api` and `ibkr-worker` receive the expected managed-resource references and the optional iBeam container stays disabled until broker integration and real credentials are configured
- `tests/apphost/ibeam-runtime-contract-tests.sh` verifies the `.env.template` iBeam contract, redacted AppHost secret-parameter wiring, default-disabled behavior, and redacted broker status payloads
- when a local Docker-compatible engine is available, `tests/apphost/apphost-infrastructure-runtime-tests.sh` starts `./start run` with isolated temporary Postgres and TimescaleDB volumes, verifies the AppHost-managed infra containers get a real process limit (`pids.max > 1`) when the host exposes effective cgroup data, and confirms `postgres` / `timescaledb` no longer die in their entrypoint scripts
- `./start run` verifies the dashboard UI port loader with a bounded fixed-port smoke check in `tests/start-contract/start-wrapper-tests.sh`
- `./start.ps1 run` and `./start.cmd run` are verified by GitHub Actions on `windows-latest` via `tests/start-contract/start-wrapper-windows.ps1`

## Bootstrap Status

The `run` contract is now bootstrapped in the repository. This covers the first real AppHost-managed slice.

- `./start run` delegates to the Aspire AppHost
- `./start.ps1 run` provides the PowerShell entrypoint
- `./start.cmd run` provides the Windows command prompt entrypoint
- GitHub Actions now runs a Windows-hosted smoke harness for both Windows wrappers
- the current graph hosts `ATrade.Api` with its `GET /health`, `GET /api/accounts/overview`, `GET /api/broker/ibkr/status`, `POST /api/orders/simulate`, `GET /api/market-data/trending`, candle/indicator, `GET /api/analysis/engines`, `POST /api/analysis/run`, and `/hubs/market-data` SignalR slice, an `ATrade.Ibkr.Worker` background service that reports safe paper-session states, the first Next.js trading workspace route set with analysis panel, and named Aspire-managed `postgres`, `timescaledb`, `redis`, and `nats` resources
- the AppHost now wires explicit managed-resource references into the application graph: `api` receives `Postgres`, `TimescaleDB`, `Redis`, and `NATS`, while `ibkr-worker` receives `Postgres`, `Redis`, and `NATS`
- developer-controlled local bind ports, including the optional fixed Aspire dashboard UI port, the AppHost Postgres and TimescaleDB data volume/password contracts, safe IBKR/iBeam paper-mode placeholders, LEAN runtime placeholders and managed-container metadata, and the browser-safe `NEXT_PUBLIC_ATRADE_API_BASE_URL` frontend API base URL now come from the repo-level `.env` contract (`.env.template` defaults + optional ignored `.env` overrides)
- the AppHost graph now applies explicit runtime safeguards for the local Podman-backed Docker API path: `--pids-limit 2048` on the four managed infra containers plus deterministic `TS_TUNE_MEMORY=512MB` / `TS_TUNE_NUM_CPUS=2` values for `timescaledb`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh` verifies the direct frontend startup path, stable visible markers for the home page, and the AppHost-managed frontend runtime contract (`NODE_ENV=development` + warning-free Turbopack root resolution)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` verifies that the published AppHost manifest preserves `api` / `frontend`, declares the four managed infrastructure resources, includes writable Postgres and TimescaleDB data-volume mounts, and carries the `timescaledb` tuning inputs in an engine-independent way
- `tests/apphost/apphost-postgres-watchlist-volume-tests.sh` verifies that exact backend watchlist pins survive a full AppHost stop/start cycle when the same isolated Postgres data volume is reused
- `tests/apphost/apphost-timescale-cache-volume-tests.sh` verifies that fresh TimescaleDB trending/candle cache rows survive a full AppHost stop/start cycle when the same isolated TimescaleDB data volume is reused, while stale rows still return provider-not-configured/provider-unavailable errors when IBKR/iBeam is disabled
- `tests/apphost/apphost-infrastructure-runtime-tests.sh` verifies the live AppHost-managed infra startup path with isolated Postgres and TimescaleDB volumes when a local engine is available, including effective `pids.max > 1` where readable and clean `postgres` / `timescaledb` startup
- `tests/apphost/ibkr-paper-safety-tests.sh` verifies the broker/project references, safe paper-only iBeam config defaults, redacted broker status payloads, deterministic simulated orders, credentials-missing/configured-iBeam states, and rejected live-mode behavior

Reserved subcommands such as `test`, `build`, and `lint` remain future work.
