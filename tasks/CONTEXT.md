# General — Context

**Last Updated:** 2026-05-10
**Status:** Active
**Next Task ID:** TP-073

---

## Project Overview

ATrade is a personal swing and position trading platform implemented as a
.NET 10 / Next.js modular monolith and orchestrated locally by Aspire 13.2.

Use `README.md` for the human-facing overview and `PLAN.md` for the current
implementation queue.

## Current Repository State

- `src/ATrade.AppHost` launches the local Aspire graph.
- `src/ATrade.Api` exposes health, accounts overview, safe IBKR status,
  simulated orders, market-data HTTP endpoints, analysis endpoints, backend
  workspace watchlist endpoints, and a market-data SignalR hub.
- `workers/ATrade.Ibkr.Worker` provides the current safe IBKR worker shell.
- `frontend/` contains the Next.js paper-trading workspace.
- Compose-managed local infrastructure includes Postgres, TimescaleDB, Redis,
  and NATS; Aspire AppHost launches API, worker, and frontend by default.
- Provider-backed IBKR/iBeam market data, symbol search, backend watchlists,
  provider-neutral analysis/LEAN seams, the `ATrade.slnx` solution-file
  contract, the HTTPS local iBeam Client Portal transport contract,
  Compose-managed LEAN Docker runtime wiring, durable Compose Postgres
  watchlists, durable TimescaleDB cache rows, frontend workflow module seams,
  the completed `TP-045` through `TP-057` frontend reconstruction/polish wave,
  the completed `TP-058` through `TP-063` paper-capital/backtesting MVP wave,
  the completed `TP-064` through `TP-068` frontend route/visibility UX wave,
  the completed `TP-069` through `TP-071` Compose startup cutover wave, and the
  completed `TP-072` Exact Instrument Identity provider-neutral key deepening
  are present.

## Domain Vocabulary

- **Exact Instrument Identity** — the backend-owned provider-neutral identity
  tuple for a tradable or chartable instrument: provider, provider symbol id,
  symbol, exchange, currency, and asset class, normalized by
  `ATrade.MarketData.ExactInstrumentIdentity`. Provider-backed market-data
  search, trending, candle, indicator, latest-update, Timescale cache, and
  watchlist flows carry this identity where available. Backend-owned persisted
  keys derive from the normalized tuple and retain the legacy
  `instrumentKey` / `pinKey` segment shape; frontend code may compute
  provisional keys only for optimistic UI state until the backend returns
  authoritative `instrumentKey` / `pinKey` values. Canonical ATrade route and
  frontend query handoff should use the provider-neutral identity tuple
  (`provider`, `providerSymbolId`, `symbol`, `exchange`, `currency`, and
  `assetClass`). Backend-owned `instrumentKey` / `pinKey` values should also
  derive from that provider-neutral tuple only. IBKR `conid` values are
  IBKR-specific provider metadata and aliases for the IBKR provider symbol id,
  not a separate provider-neutral identity dimension. Existing `ibkrConid`-
  bearing keys are legacy inputs only; compatibility code may accept them in
  order to normalize to the provider-neutral key shape, but new canonical keys
  should not emit an `ibkrConid` segment. Frontend optimistic UI may compute
  provisional keys from the same provider-neutral tuple, but backend-returned
  `instrumentKey` / `pinKey` values remain authoritative. Route/query parsing
  remains an API/frontend adapter concern; those adapters should translate
  request shape into the provider-neutral tuple before crossing the Exact
  Instrument Identity module seam. Saved backtest runs should persist and
  display the full provider-neutral Exact Instrument Identity tuple rather than
  symbol-only history with optional provider metadata. Runtime `instrumentKey`
  construction must go through the Exact Instrument Identity implementation;
  SQL migrations/repositories should not manually reconstruct canonical key
  strings except for unavoidable one-off legacy repair.

## Active Task Queue

No ready implementation tasks are currently queued after completion of `TP-072` Exact Instrument Identity provider-neutral key deepening. The next new Taskplane packet should use `TP-073`.

The most recent completed work includes:

- `TP-055` — refactored the frontend into an original black/graphite/amber ATrade terminal palette
- `TP-056` — added purpose-matched module rail icons and accessible collapsible rail behavior
- `TP-057` — made the market-monitor table own visible vertical and horizontal scrollbars
- `TP-058` — added the paper-capital source contract with IBKR/iBeam balance preference, local Postgres fallback, and safe account redaction
- `TP-059` — created the first-class Backtesting backend module, saved-run persistence, and REST APIs
- `TP-060` — added the durable async backtest runner, restart recovery, cancellation, and SignalR job updates
- `TP-061` — expanded built-in strategy support and rich backtest results for SMA, RSI, and breakout strategies
- `TP-062` — added the BACKTEST terminal module with run form, capital settings, SignalR status, history, cancel, and retry
- `TP-063` — added saved-run comparison and equity/benchmark overlays in the BACKTEST module
- `TP-064` — added frontend layout/browser visibility guardrails and durable desktop scroll-ownership memory
- `TP-065` — added canonical terminal route architecture and removed the old `/symbols/[symbol]` route without redirect/alias behavior
- `TP-066` — added `/chart` Stored stocks defaults without fake demo symbols
- `TP-067` — made Home, Search, and Watchlist purpose-built instead of identical market-monitor wrappers
- `TP-068` — added consolidated frontend route, visibility, chart-default, and page-purpose regression validation
- `TP-069` — added the Compose runtime foundation with stable local infra ports and helper scripts
- `TP-070` — added opt-in AppHost external Compose infrastructure mode
- `TP-071` — cut over default startup to Compose-managed infrastructure with Aspire-launched app services
- `TP-072` — deepened Exact Instrument Identity so canonical keys and saved backtest identity use provider-neutral fields and legacy `ibkrConid` inputs normalize forward

The next new Taskplane packet should use `TP-073`.

Completed task packets through `TP-072` are present in `tasks/`; completed
packets should be archived when convenient. During orchestrated runs the runtime
handles post-merge archival for active task folders.

## Taskplane Usage

This repository uses Taskplane task packets for implementation work.

- Run all ready tasks: `/orch all`
- Run one task: `/orch tasks/<TASK-ID>-<slug>/PROMPT.md`
- New tasks should use the next ID: `TP-073`
- New task prompts and verification commands should use `ATrade.slnx` for repo-level .NET build/test/list operations.
- Task packets must include `PROMPT.md` and `STATUS.md`
- Finished task directories should be moved to `tasks/archive/`

## Frontend Desktop Browser Visibility Guardrail

Frontend work must preserve consistent behavior across latest stable desktop
Safari, Firefox, Chrome, and Edge. Mobile optimization is not in scope for the
current frontend UX batch, beyond preserving existing responsive fallbacks.

The accepted shell contract is: keep the terminal as a full-viewport app with
page-level scrolling disabled, but make every overflowing region internally
reachable with visible/custom scroll affordances. Rail items, including late-list
visible-disabled entries such as NODE and ORDERS; the primary workspace;
market-monitor tables/detail panels; chart, analysis, backtest, status, help,
and disabled module content must not be clipped or unreachable. Use
module-owned scroll regions rather than hiding overflow. Safari's native
scrollbar behavior may hide OS scrollbars, so key scroll-owned terminal regions
must render app-owned or explicitly styled visible scrollbar tracks/thumbs that
remain apparent in Safari, Firefox, Chrome, and Edge.

## Runtime Contract

The repo-level solution-file contract is `ATrade.slnx` for active .NET
build/test/list operations, including future task prompts. The legacy
`ATrade.sln` file is retained only as a temporary non-authoritative
compatibility artifact for older tooling.

The repo-local `start` shim is the single startup contract across platforms:

- Unix-like: `./start run`
- Windows PowerShell: `./start.ps1 run`
- Windows Command Prompt: `./start.cmd run`

All variants start Compose infrastructure first and then delegate to the Aspire AppHost for API, worker, and frontend. Infrastructure containers do not appear in the default Aspire dashboard and remain running after AppHost exits.

## Key Files

| Category            | Path                                                      |
| ------------------- | --------------------------------------------------------- |
| Human overview      | `README.md`                                               |
| Current plan        | `PLAN.md`                                                 |
| Documentation index | `docs/INDEX.md`                                           |
| Startup contract    | `scripts/README.md`                                       |
| Active tasks        | None currently queued; next packet should use `TP-073`    |
| Completed tasks     | `tasks/TP-042-*` through `tasks/TP-072-*`                 |
| Archived tasks      | `tasks/archive/TP-002-*` through `tasks/archive/TP-041-*` |
| Taskplane config    | `.pi/taskplane-config.json`                               |
| AppHost             | `src/ATrade.AppHost/Program.cs`                           |
| API                 | `src/ATrade.Api/Program.cs`                               |
| Frontend            | `frontend/`                                               |

## Documentation Rules

- Use `docs/INDEX.md` as the documentation discovery layer.
- Only documents marked `active` are implementation authority.
- Durable runtime/code changes must update relevant docs in the same change.
- Do not commit secrets, IBKR credentials, account identifiers, tokens, or session cookies.
- Do not add real order placement or live-trading behavior in the current task queue.

## Technical Debt / Future Work

- [ ] Review the frontend dependency audit from TP-018 (`lightweight-charts` and `@microsoft/signalr` reported moderate npm advisories) without forcing breaking upgrades.
- [ ] Review TP-046 frontend npm audit advisories for `next` and `postcss` after the terminal UI stack bootstrap; do not force breaking upgrades inside the reconstruction queue.
- [x] Archive completed `TP-019` through `TP-041` task packets before starting the previous queued run.
- [ ] Archive completed `TP-042` through `TP-072` task packets when convenient.
- [ ] Verify real IBKR/iBeam and LEAN behavior only through ignored `.env` values and documented optional runtime checks.
- [ ] Keep local iBeam Client Portal transport on HTTPS (`https://127.0.0.1:<gateway-port>`) and restrict self-signed certificate handling to loopback iBeam development traffic.
