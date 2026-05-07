# General — Context

**Last Updated:** 2026-05-07
**Status:** Active
**Next Task ID:** TP-069

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
- AppHost-managed local infrastructure includes Postgres, TimescaleDB, Redis,
  and NATS.
- Provider-backed IBKR/iBeam market data, symbol search, backend watchlists,
  provider-neutral analysis/LEAN seams, the `ATrade.slnx` solution-file
  contract, the HTTPS local iBeam Client Portal transport contract,
  AppHost-managed LEAN Docker runtime wiring, durable AppHost Postgres
  watchlists, durable TimescaleDB cache rows, frontend workflow module seams,
  the completed `TP-045` through `TP-057` frontend reconstruction/polish wave,
  and the completed `TP-058` through `TP-063` paper-capital/backtesting MVP wave
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
  authoritative `instrumentKey` / `pinKey` values.

## Active Task Queue

Ready implementation tasks are queued for the frontend route/visibility UX batch:

- `TP-064` — frontend layout and browser visibility guardrails, including durable memory in `AGENTS.md`, `tasks/CONTEXT.md`, and the active UI design doc
- `TP-065` — canonical terminal route architecture for enabled/disabled modules and removal of the old `/symbols/[symbol]` route
- `TP-066` — `/chart` stored-stocks selector and first-watchlist-instrument default chart behavior without fake default symbols
- `TP-067` — purpose-built Home, Search, and Watchlist modules so the three pages no longer look like identical market-monitor clones
- `TP-068` — consolidated frontend route, visibility, chart-default, and page-purpose regression validation

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

The next new Taskplane packet should use `TP-069`.

Completed task packets through `TP-063` are present in `tasks/`; completed
packets should be archived when convenient.

## Taskplane Usage

This repository uses Taskplane task packets for implementation work.

- Run all ready tasks: `/orch all`
- Run one task: `/orch tasks/<TASK-ID>-<slug>/PROMPT.md`
- New tasks should use the next ID: `TP-069`
- New task prompts and verification commands should use `ATrade.slnx` for repo-level .NET build/test/list operations.
- Task packets must include `PROMPT.md` and `STATUS.md`
- Finished task directories should be moved to `tasks/archive/`

## Frontend Desktop Browser Visibility Guardrail

Frontend work must preserve consistent behavior across latest stable desktop
Safari, Firefox, Chrome, and Edge. Mobile optimization is not in scope for the
current frontend UX batch, beyond preserving existing responsive fallbacks.

The accepted shell contract is: keep the terminal as a full-viewport app with
page-level scrolling disabled, but make every overflowing region internally
reachable with visible/custom scroll affordances. Rail items, market-monitor
tables/detail panels, chart, analysis, backtest, status, help, and disabled
module content must not be clipped or unreachable; use module-owned scroll
regions rather than hiding overflow. Safari's native scrollbar behavior may hide
OS scrollbars, so key scroll-owned terminal regions should render app-owned or
explicitly styled visible scrollbar tracks/thumbs.

## Runtime Contract

The repo-level solution-file contract is `ATrade.slnx` for active .NET
build/test/list operations, including future task prompts. The legacy
`ATrade.sln` file is retained only as a temporary non-authoritative
compatibility artifact for older tooling.

The repo-local `start` shim is the single startup contract across platforms:

- Unix-like: `./start run`
- Windows PowerShell: `./start.ps1 run`
- Windows Command Prompt: `./start.cmd run`

All variants delegate to the Aspire AppHost.

## Key Files

| Category            | Path                                                      |
| ------------------- | --------------------------------------------------------- |
| Human overview      | `README.md`                                               |
| Current plan        | `PLAN.md`                                                 |
| Documentation index | `docs/INDEX.md`                                           |
| Startup contract    | `scripts/README.md`                                       |
| Active tasks        | `TP-064` through `TP-068` frontend route/visibility UX batch |
| Completed tasks     | `tasks/TP-042-*` through `tasks/TP-063-*`                 |
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
- [ ] Archive completed `TP-042` through `TP-063` task packets when convenient.
- [ ] Verify real IBKR/iBeam and LEAN behavior only through ignored `.env` values and documented optional runtime checks.
- [ ] Keep local iBeam Client Portal transport on HTTPS (`https://127.0.0.1:<gateway-port>`) and restrict self-signed certificate handling to loopback iBeam development traffic.
