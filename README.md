---
status: active
owner: maintainer
updated: 2026-05-06
summary: Human-facing overview of the current ATrade application, run contract, and active Taskplane work queue.
see_also:
  - PLAN.md
  - docs/INDEX.md
  - scripts/README.md
  - docs/architecture/overview.md
  - docs/design/atrade-terminal-ui.md
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
- Broker/data direction: provider-neutral contracts with `IBKR` through the local `voyz/ibeam:latest` runtime contract, IBKR/iBeam-backed market data, and a paper-capital source that prefers authenticated IBKR paper balances before local fallback capital
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
  secret parameter so workspace preferences and local paper-capital fallback
  values survive full local AppHost reboots;
  the `timescaledb` data directory uses `ATRADE_TIMESCALEDB_DATA_VOLUME`
  (default `atrade-timescaledb-data`) plus a stable local-dev
  `ATRADE_TIMESCALEDB_PASSWORD` secret parameter so fresh market-data cache rows
  survive full local AppHost reboots; the local iBeam Client Portal URL is HTTPS on the configured host gateway port,
  mapped to the container's internal Client Portal port `5000`, and the
  container receives a repo-local non-secret iBeam inputs mount so Client Portal
  accepts loopback/private Docker bridge callers used by Aspire.
- `src/ATrade.Brokers` — provider-neutral broker status, identity, account-mode, and capability contracts.
- `src/ATrade.Accounts` — bootstrap-safe account overview plus the effective paper-capital contract, Postgres-backed local paper-capital fallback, and IBKR-first capital-source selection for future backtests.
- `src/ATrade.Api` — browser-facing backend with:
  - `GET /health`
  - `GET /api/accounts/overview`
  - `GET /api/accounts/paper-capital`
  - `PUT /api/accounts/local-paper-capital`
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
- `frontend/` — Next.js ATrade paper-trading workspace with enabled/disabled module registry and rail, direct module/workflow navigation, a rail-first full-bleed single-primary workspace layout with no app-level brand header, visible global safety strip, shell context/monitor/footer chrome, or page-level vertical scrolling, an original black/graphite/amber institutional terminal palette with red/green market states, a compact-filtered dense market monitor for trending/search/watchlist rows, visibly sized chart/indicator/analysis workspaces with SignalR-to-HTTP fallback, provider diagnostics, backend-saved exact watchlists, exact chart/analysis handoff, and provider-neutral analysis states.

Current market data is served through `ATrade.Api` using a Timescale-first
cache-aside path over the `ATrade.MarketData.Ibkr` provider behind
`ATrade.MarketData` contracts. `ATrade.MarketData.ExactInstrumentIdentity` owns
backend normalization/key encoding for provider, provider symbol id, symbol,
exchange, currency, and asset class; `ATrade.MarketData.ChartRangePresets` owns
chart lookback ranges from now (`1min`, `5mins`, `1h`, `6h`, `1D`, `1m`, `6m`,
`1y`, `5y`, and `all` / All time); search, trending, candle, indicator,
latest-update, Timescale cache, and watchlist flows carry exact identity where
provider metadata is available while keeping legacy symbol-only HTTP paths
compatible. When the local iBeam/Gateway runtime is
configured with the HTTPS Client Portal URL (`https://127.0.0.1:<gateway-port>`),
the AppHost-mounted iBeam inputs config allows the local/private Docker bridge
source addresses that published-port requests use, and iBeam is authenticated
through ignored `.env` values, API endpoints return IBKR scanner, snapshot, and
historical bar data with source metadata. `ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES`
(default `30`) controls whether TimescaleDB rows for trending snapshots,
candles, and indicator candle inputs are fresh enough to serve directly as
`timescale-cache:{originalSource}` responses for the requested normalized chart
range; because the AppHost TimescaleDB data directory is volume-backed, those
fresh rows can survive a full local
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
exact identity in query state when available and render a visible `CandlestickChart`
when provider candles exist (empty/provider-unavailable states remain explicit
with no synthetic bars), and pin exact provider-market
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

Paper-capital selection is available through `GET /api/accounts/paper-capital`
and `PUT /api/accounts/local-paper-capital`. The effective-capital payload uses
`source = "ibkr-paper-balance"` only when the configured paper iBeam session is
authenticated and a positive Client Portal account-summary balance is available;
it otherwise falls back to the Postgres-backed local paper ledger, or reports
`source = "unavailable"` with safe messages when neither source exists. Browser
payloads, logs, docs, and tests must not expose IBKR account identifiers,
credentials, gateway URLs, tokens, cookies, or session details.

## Active Task Queue

Ready Taskplane packets live directly under `tasks/`; completed packets are
archived under `tasks/archive/`.

The `TP-045` through `TP-055` frontend reconstruction, no-command cutover,
layout-simplification, chart-visibility restoration, and theme-foundation batch
now covers the active design spec, shadcn/Tailwind/Radix UI foundation,
module/workflow shell, dense market monitor, chart/analysis workspaces, final
cutover verification, removal of the visible terminal branding plus command
input/parser, the simplified rail-first full-bleed single-primary workspace
layout, removal of the remaining app-level brand header/global safety strip,
compact market-monitor filters, visible stock chart rendering, and the original
black/graphite/amber ATrade terminal palette validation. The current frontend
surface is the direct module/workflow ATrade paper workspace. The active
backend/backtesting MVP wave starts with `TP-058` paper-capital source work and
should build on module rail navigation plus explicit workflow actions rather
than the retired old shell/list
route wrappers, a command system, cyan/blue-gradient-dominant styling, or the
removed app-level, context, monitor, footer, and top-safety chrome.

Completed Taskplane packets through `TP-055` are present in `tasks/`; `TP-058`
is currently staged as an active paper-capital source packet. Completed packets
should be archived when convenient. During orchestrated runs the runtime handles
post-merge archival for active task folders.

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
- `docs/design/atrade-terminal-ui.md` defines the active clean-room ATrade paper workspace UI target for the frontend reconstruction queue.
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
- `tests/apphost/paper-capital-source-tests.sh`
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- `tests/apphost/frontend-terminal-cutover-tests.sh`
- `tests/apphost/frontend-terminal-ui-stack-tests.sh`
- `tests/apphost/frontend-terminal-theme-refactor-tests.sh`
- `tests/apphost/frontend-chart-range-preset-tests.sh`
- `tests/apphost/frontend-stock-chart-visibility-tests.sh`
- `tests/apphost/frontend-terminal-chart-analysis-tests.sh`
- `tests/apphost/frontend-symbol-search-exploration-tests.sh`
- `tests/apphost/frontend-terminal-market-monitor-tests.sh`
- `tests/apphost/frontend-no-command-shell-tests.sh`
- `tests/apphost/frontend-simplified-workspace-layout-tests.sh`
- `tests/apphost/frontend-top-chrome-filter-density-tests.sh`
- `tests/apphost/frontend-terminal-shell-ui-tests.sh`
- `tests/apphost/frontend-trading-workspace-tests.sh`
- `tests/apphost/frontend-workspace-workflow-module-tests.sh`

Task packets list their own targeted and full verification commands.

## License

MIT License — see `LICENSE`.
