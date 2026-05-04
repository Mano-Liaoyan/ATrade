---
status: active
owner: maintainer
updated: 2026-05-04
summary: Human-facing overview of the current ATrade application, run contract, and active Taskplane work queue.
see_also:
  - PLAN.md
  - docs/INDEX.md
  - scripts/README.md
  - docs/architecture/overview.md
  - docs/architecture/modules.md
  - docs/architecture/provider-abstractions.md
  - docs/architecture/analysis-engines.md
  - docs/architecture/paper-trading-workspace.md
---

# ATrade

ATrade is a personal swing and position trading platform built as a modular
monolith with .NET 10, Next.js, and Aspire 13.2.

The repository currently contains a runnable local stack and a Taskplane work
queue for architecture deepening across the provider-backed paper-trading
workspace.

## Current Stack

- Backend: `.NET 10`
- Frontend: `Next.js`
- Local orchestrator: `Aspire 13.2`
- Infrastructure: `Postgres`, `TimescaleDB`, `Redis`, `NATS`
- Broker/data direction: provider-neutral contracts with `IBKR` through the local `voyz/ibeam:latest` runtime contract and IBKR/iBeam-backed market data
- Analysis direction: provider-neutral `ATrade.Analysis` contracts with `ATrade.Analysis.Lean` as the first optional analysis provider when the official LEAN runtime is configured locally

## Run Contract

The repository-wide startup contract is the repo-local `start` shim:

- Unix-like: `./start run`
- Windows PowerShell: `./start.ps1 run`
- Windows Command Prompt: `./start.cmd run`

All variants delegate to the Aspire AppHost so one command can bring up the
API, worker, frontend, and local infrastructure. Local bind-port overrides,
including the optional fixed Aspire dashboard UI port
(`ATRADE_ASPIRE_DASHBOARD_HTTP_PORT`, default `0` for ephemeral loopback) and
AppHost Postgres/TimescaleDB data-volume/password overrides, are kept in ignored
`.env` and documented in `scripts/README.md`. The .NET hosts resolve the local
runtime contract through `ATrade.ServiceDefaults`, which overlays
`.env.template`, ignored `.env`, and process environment values while keeping
credential-bearing values classified for Aspire secret-parameter handoff.

## Current Runtime Surface

The current runnable slice includes:

- `src/ATrade.AppHost` — Aspire graph for the API, IBKR worker, Next.js
  frontend, volume-backed Postgres, volume-backed TimescaleDB, Redis, NATS, the
  optional `voyz/ibeam:latest` `ibkr-gateway` container when ignored local `.env`
  credentials enable broker integration, and the optional `lean-engine` LEAN
  runtime container when ignored local `.env` selects LEAN Docker mode; the
  primary `postgres` data directory uses `ATRADE_POSTGRES_DATA_VOLUME` (default
  `atrade-postgres-data`) plus a stable local-dev `ATRADE_POSTGRES_PASSWORD`
  secret parameter so workspace preferences survive full local AppHost reboots;
  the `timescaledb` data directory uses `ATRADE_TIMESCALEDB_DATA_VOLUME`
  (default `atrade-timescaledb-data`) plus a stable local-dev
  `ATRADE_TIMESCALEDB_PASSWORD` secret parameter so fresh market-data cache rows
  survive full local AppHost reboots; the local iBeam Client Portal URL is HTTPS on the configured host gateway port,
  mapped to the container's internal Client Portal port `5000`, and the
  container receives a repo-local non-secret iBeam inputs mount so Client Portal
  accepts loopback/private Docker bridge callers used by Aspire.
- `src/ATrade.Brokers` — provider-neutral broker status, identity, account-mode, and capability contracts.
- `src/ATrade.Api` — browser-facing backend with:
  - `GET /health`
  - `GET /api/accounts/overview`
  - `GET /api/broker/ibkr/status`
  - `POST /api/orders/simulate`
  - `GET /api/market-data/trending`
  - `GET /api/market-data/search`
  - `GET /api/market-data/{symbol}/candles`
  - `GET /api/market-data/{symbol}/indicators`
  - `GET /api/analysis/engines`
  - `POST /api/analysis/run`
  - `GET /api/workspace/watchlist`
  - `PUT /api/workspace/watchlist`
  - `POST /api/workspace/watchlist`
  - `DELETE /api/workspace/watchlist/pins/{instrumentKey}`
  - `DELETE /api/workspace/watchlist/{symbol}`
  - `/hubs/market-data`
- `src/ATrade.MarketData.Ibkr` — IBKR/iBeam Client Portal market-data provider for contract search/detail lookup, scanner/trending-equivalent results, snapshots, historical bars, and safe unavailable states projected from the shared IBKR/iBeam readiness module.
- `src/ATrade.MarketData.Timescale` — provider-neutral TimescaleDB persistence and cache-aside for OHLCV candles and scanner/trending snapshots, with configurable freshness for browser-facing market-data endpoints.
- `src/ATrade.Analysis` — provider-neutral analysis engine contracts, registry, normalized request/result payloads, engine/source metadata, and explicit no-engine fallback behavior.
- `src/ATrade.Analysis.Lean` — optional LEAN analysis provider that generates analysis-only LEAN workspaces from ATrade OHLCV bars, invokes the configured official LEAN CLI or AppHost-managed Docker runtime, and returns provider-neutral signals/metrics/backtest summaries without order routing.
- `src/ATrade.Workspaces` — Postgres-backed workspace preference module for exact provider/market watchlist pins with stable `instrumentKey` / `pinKey` metadata, including IBKR search-result pins.
- `workers/ATrade.Ibkr.Worker` — safe paper-session/readiness monitoring shell for disabled, credentials-missing, configured-iBeam, connecting, authenticated, degraded, error, and rejected-live states.
- `frontend/` — Next.js paper-trading workspace with trending symbols, chart pages, SignalR fallback, backend-saved watchlists, and a provider-neutral analysis panel.

Current market data is served through `ATrade.Api` using a Timescale-first
cache-aside path over the `ATrade.MarketData.Ibkr` provider behind
`ATrade.MarketData` contracts. `ATrade.MarketData.ExactInstrumentIdentity` owns
backend normalization/key encoding for provider, provider symbol id, symbol,
exchange, currency, and asset class; search, trending, candle, indicator,
latest-update, Timescale cache, and watchlist flows carry that identity where
provider metadata is available while keeping legacy symbol-only HTTP paths
compatible. When the local iBeam/Gateway runtime is
configured with the HTTPS Client Portal URL (`https://127.0.0.1:<gateway-port>`),
the AppHost-mounted iBeam inputs config allows the local/private Docker bridge
source addresses that published-port requests use, and iBeam is authenticated
through ignored `.env` values, API endpoints return IBKR scanner, snapshot, and
historical bar data with source metadata. `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`
(default `30`) controls whether TimescaleDB rows for trending snapshots,
candles, and indicator candle inputs are fresh enough to serve directly as
`timescale-cache:{originalSource}` responses; because the AppHost TimescaleDB
data directory is volume-backed, those fresh rows can survive a full local
AppHost reboot and be served without another IBKR/iBeam provider call. Missing or
stale rows refresh from IBKR/iBeam, persist the provider response to TimescaleDB,
and return the provider response. When iBeam is disabled, missing credentials,
unauthenticated, timed out, or unreachable, a fresh persisted response can still serve the request; otherwise
the API and frontend surface safe provider-not-configured/provider-unavailable
states projected from the shared IBKR/iBeam readiness module instead of falling back to production mocks. Pinned instruments are backend-owned
workspace preferences persisted in the volume-backed AppHost-managed Postgres
database through `ATrade.Workspaces` and surfaced to the frontend through
`/api/workspace/watchlist` with stable `instrumentKey` / `pinKey` identity; they
survive full local AppHost stop/start cycles when the same Postgres data volume
and stable password are reused. Browser `localStorage` is only a
non-authoritative symbol-only cache / one-time manual migration source. Users can search IBKR/iBeam stocks through
`/api/market-data/search`, see explicit provider/market/exchange/currency/asset
class metadata with local market badges, open result chart pages that preserve
exact identity in query state when available, and pin exact provider-market
metadata (`provider`, provider symbol id / IBKR `conid`, name, exchange,
currency, and asset class) into the backend watchlist without a production
hard-coded symbol catalog. Analysis engine discovery/run contracts are available through
`/api/analysis/engines` and `/api/analysis/run`. With no provider selected they
return explicit `analysis-engine-not-configured` metadata with no fake signals;
when ignored local `.env` sets `ATRADE_ANALYSIS_ENGINE=Lean`, the API registers
`ATrade.Analysis.Lean`, runs LEAN over market-data-provider candles, and returns
provider-neutral signals/metrics/backtest summaries. With
`ATRADE_LEAN_RUNTIME_MODE=docker`, AppHost exposes a dashboard-visible
`lean-engine` resource, bind-mounts the generated workspace root, and passes the
managed container metadata to the API so execution uses `docker exec` against
that resource. Missing LEAN runtime, missing managed container metadata,
unavailable Docker/image/container, non-zero exits, or timeouts surface as safe
`analysis-engine-unavailable` responses without fake signals.

## Active Task Queue

Ready Taskplane packets live directly under `tasks/`; completed packets are
archived under `tasks/archive/`.

Ready implementation tasks are queued as `TP-042` through `TP-044` to fix chart
range semantics and redesign the frontend workspace/search navigation. The
recommended order is sequential because each task stabilizes a seam used by the
next.

Completed Taskplane packets through `TP-041` live under `tasks/archive/`.

## Repository Map

```text
ATrade/
├── README.md             # This overview
├── PLAN.md               # Current implementation plan
├── docs/                 # Indexed active documentation
├── scripts/              # Startup and local environment contracts
├── src/                  # .NET 10 backend modules and AppHost
├── workers/              # Long-running worker processes
├── frontend/             # Next.js application
├── tasks/                # Active Taskplane packets and archive
└── .pi/                  # Taskplane/Pi runtime config, runtime agents, and skill symlinks
```

Reusable `.pi/skills/` entries are opt-in Pi skills. `.pi/agents/` files are Taskplane runtime
agents used by the orchestrator.

## Documentation Rules

- Use `docs/INDEX.md` as the documentation discovery layer.
- Only documents marked `active` are implementation authority.
- `docs/architecture/provider-abstractions.md`, `docs/architecture/analysis-engines.md`, and `docs/architecture/paper-trading-workspace.md` define the provider seams, analysis engine contract, and paper-trading workspace contract.
- Durable code or runtime changes must update the relevant active docs in the same change.
- Secrets, IBKR credentials, account identifiers, tokens, and session cookies must stay out of git and belong only in ignored local `.env` files.
- No task may introduce real order placement or live-trading behavior unless a future task explicitly changes the safety contract and docs.

## Solution File Contract

`ATrade.slnx` is the authoritative solution file for repo-level .NET build,
test, and solution-list commands:

```bash
dotnet test ATrade.slnx --nologo --verbosity minimal
dotnet build ATrade.slnx --nologo --verbosity minimal
```

The legacy `ATrade.sln` remains temporarily as a non-authoritative compatibility
artifact for tools that have not adopted `.slnx`; active scripts, tests, docs,
and new Taskplane prompts should prefer `ATrade.slnx`.

## Verification Entry Points

Common verification scripts live under `tests/`:

- `tests/start-contract/start-wrapper-tests.sh`
- `tests/apphost/api-bootstrap-tests.sh`
- `tests/apphost/accounts-feature-bootstrap-tests.sh`
- `tests/apphost/ibkr-paper-safety-tests.sh`
- `tests/apphost/ibeam-runtime-contract-tests.sh`
- `tests/apphost/ibkr-market-data-provider-tests.sh`
- `tests/apphost/ibkr-symbol-search-tests.sh`
- `tests/apphost/market-data-feature-tests.sh`
- `tests/apphost/provider-abstraction-contract-tests.sh`
- `tests/apphost/analysis-engine-contract-tests.sh`
- `tests/apphost/lean-analysis-engine-tests.sh`
- `tests/apphost/postgres-watchlist-persistence-tests.sh`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `tests/apphost/frontend-workspace-workflow-module-tests.sh`

Task packets list their own targeted and full verification commands.

## License

MIT License — see `LICENSE`.
