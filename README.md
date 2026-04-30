---
status: active
owner: maintainer
updated: 2026-04-30
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
queue for solution-reference cleanup and the next provider-backed trading
workspace runtime fix.

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
API, worker, frontend, and local infrastructure.

## Current Runtime Surface

The current runnable slice includes:

- `src/ATrade.AppHost` — Aspire graph for the API, IBKR worker, Next.js frontend, Postgres, TimescaleDB, Redis, NATS, and the optional `voyz/ibeam:latest` `ibkr-gateway` container when ignored local `.env` credentials enable broker integration; the local iBeam Client Portal URL is HTTPS on the configured gateway port.
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
  - `DELETE /api/workspace/watchlist/{symbol}`
  - `/hubs/market-data`
- `src/ATrade.MarketData.Ibkr` — IBKR/iBeam Client Portal market-data provider for contract search/detail lookup, scanner/trending-equivalent results, snapshots, historical bars, and safe unavailable states.
- `src/ATrade.Analysis` — provider-neutral analysis engine contracts, registry, normalized request/result payloads, engine/source metadata, and explicit no-engine fallback behavior.
- `src/ATrade.Analysis.Lean` — optional LEAN analysis provider that generates analysis-only LEAN workspaces from ATrade OHLCV bars, invokes the configured official LEAN CLI/Docker runtime, and returns provider-neutral signals/metrics/backtest summaries without order routing.
- `src/ATrade.Workspaces` — Postgres-backed workspace preference module for pinned watchlists and provider-ready symbol metadata, including IBKR search-result pins.
- `workers/ATrade.Ibkr.Worker` — safe paper-session/status monitoring shell for disabled, credentials-missing, configured-iBeam, connecting, authenticated, degraded, error, and rejected-live states.
- `frontend/` — Next.js paper-trading workspace with trending symbols, chart pages, SignalR fallback, backend-saved watchlists, and a provider-neutral analysis panel.

Current market data is served through the `ATrade.MarketData.Ibkr` provider
behind `ATrade.MarketData` contracts. When the local iBeam/Gateway runtime is
configured with the HTTPS Client Portal URL (`https://127.0.0.1:<gateway-port>`)
and authenticated through ignored `.env` values, API endpoints return IBKR
scanner, snapshot, and historical bar data with source metadata. When iBeam
is disabled, missing credentials, unauthenticated, or unreachable, the API and
frontend surface safe provider-not-configured/provider-unavailable states instead
of falling back to production mocks. Pinned symbols are backend-owned workspace
preferences persisted in the AppHost-managed Postgres database through
`ATrade.Workspaces` and surfaced to the frontend through
`/api/workspace/watchlist`; browser `localStorage` is only a non-authoritative
cache / one-time migration source. Users can search IBKR/iBeam stocks through
`/api/market-data/search`, open result chart pages, and pin provider metadata
(`provider`, provider symbol id / IBKR `conid`, name, exchange, currency, and
asset class) into the backend watchlist without a production hard-coded symbol
catalog. Analysis engine discovery/run contracts are available through
`/api/analysis/engines` and `/api/analysis/run`. With no provider selected they
return explicit `analysis-engine-not-configured` metadata with no fake signals;
when ignored local `.env` sets `ATRADE_ANALYSIS_ENGINE=Lean`, the API registers
`ATrade.Analysis.Lean`, runs LEAN over market-data-provider candles, and returns
provider-neutral signals/metrics/backtest summaries. Missing LEAN runtime or
timeouts surface as safe `analysis-engine-unavailable` responses.

## Active Task Queue

Taskplane packets live directly under `tasks/` while pending archival.

No ready implementation task is currently queued. Completed Taskplane packets
`TP-019` through `TP-027` currently remain under `tasks/` with `.DONE` markers
pending archival; older completed packets live under `tasks/archive/`.

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

Task packets list their own targeted and full verification commands.

## License

MIT License — see `LICENSE`.
