---
status: active
owner: maintainer
updated: 2026-05-06
summary: Current implementation plan after the ATrade paper workspace frontend reconstruction, paper-capital source, saved backtesting API seams, and terminal comparison surface.
see_also:
  - README.md
  - docs/INDEX.md
  - docs/design/atrade-terminal-ui.md
  - scripts/README.md
  - tasks/CONTEXT.md
---

# ATrade Current Plan

**Last updated:** 2026-05-06

## Current Focus

The provider-backed paper-trading workspace slice is runnable with IBKR/iBeam
market data, TimescaleDB cache-aside, durable Postgres watchlists, durable
Postgres local paper-capital fallback storage, durable Postgres saved backtest
run history, an API-hosted async backtest runner with SignalR job updates,
exact provider/market pins, configurable local AppHost ports,
optional AppHost-managed LEAN Docker runtime wiring, and the completed `TP-045`
through `TP-057` frontend reconstruction,
no-command cutover, layout simplification,
top-chrome/filter-density cleanup, stock chart visibility restoration, original
terminal theme foundation, module rail icon/collapse behavior, and visible
market-monitor table scrollbars. The current frontend surface is the
clean-room ATrade paper workspace: direct module/workflow navigation,
enabled/current workflow modules, visible-disabled future modules, purpose-matched
module rail icons with local icon-first collapse behavior, compact dense market
monitor with visible internal vertical/horizontal table scrollbars for wide
exact-identity and action columns, visibly sized chart/analysis/backtest
workspaces, provider diagnostics, a rail-first full-bleed single-primary
workspace layout
with no app-level brand header, visible global safety strip,
shell context/monitor/footer chrome, or page-level vertical scrolling, an
original black/graphite/amber institutional terminal
palette with red/green market states, and final cutover/no-command/simplified-layout/top-chrome
filter-density/chart-visibility/theme-refactor guardrails for clean-room,
no-order, truthful provider-state, and `ATrade.Api` browser boundaries. The
backend/backtesting MVP seams (`TP-058` through `TP-061`) add paper-capital
source selection, saved backtest APIs, API-hosted async execution, and built-in
strategy/rich result expansion through `ATrade.Api`: effective capital prefers a
safe authenticated IBKR paper balance, falls back to a user-configured local
Postgres ledger value, reports explicit unavailable/unconfigured state when
neither exists, and is snapshotted on saved backtest runs persisted in Postgres
before queued jobs are claimed, executed through market-data/analysis seams,
cancelled best-effort, and broadcast over `/hubs/backtests`. Saved runs now carry
server-validated `sma-crossover`, `rsi-mean-reversion`, and `breakout`
parameters, cost/slippage settings, buy-and-hold benchmark mode, and
provider-neutral summary/equity-curve/simulated-trade result envelopes without
custom code or order routing. `TP-062` adds the first user-facing terminal
BACKTEST module on top of those contracts: an effective/local paper-capital
panel, single-symbol SMA/RSI/breakout strategy form, SignalR live status,
Postgres-backed history/detail, cancel, retry-as-new-run behavior, and truthful
empty/unavailable states with no order controls or fake results. `TP-063` adds
completed-run-only saved-run comparison, side-by-side metrics, and persisted
strategy/buy-and-hold benchmark equity overlays without export, optimization,
fake demo data, direct provider access, or order-routing scope. The active
clean-room UI design authority remains `docs/design/atrade-terminal-ui.md`.

Current repository contracts remain:

- use `ATrade.slnx` as the authoritative solution reference for active build/test guidance
- keep the local IBKR/iBeam refresh transport on the HTTPS Client Portal contract
- keep paper-capital and saved backtest initialization/history behind `ATrade.Api`, with IBKR account ids used only internally and local fallback capital/backtest rows persisted in Postgres without secrets, gateway URLs, direct bars, custom code, or order-routing fields
- keep credentials, account identifiers, tokens, cookies, and live-trading behavior out of committed files and active defaults
- keep frontend/browser data access behind `ATrade.Api`; the frontend must not connect directly to Postgres or TimescaleDB
- keep durable runtime/code changes paired with active documentation updates

## Active Task Queue

The frontend reconstruction queue is complete through the rail-first
top-chrome/filter-density cleanup, stock chart visibility restoration, original
black/graphite/amber terminal theme foundation, module rail icon/collapse
behavior, and market-monitor visible scrollbar work:

- `TP-045` — defined the active UI design spec and clean-room visual guardrails
- `TP-046` — bootstrapped the shadcn/Tailwind/Radix UI stack and original ATrade primitives
- `TP-047` — built the module shell, module rail, and resizable layout persistence
- `TP-048` — rebuilt search, trending, and watchlist as a dense market monitor
- `TP-049` — rebuilt chart and analysis workspaces inside the new shell
- `TP-050` — completed frontend cutover, cleanup, verification, and documentation updates
- `TP-051` — removed visible terminal branding plus the command input/parser/registry and added no-command validation
- `TP-052` — simplified the workspace to a full-bleed single-primary layout with no context/monitor/footer chrome, background grid, page-level scroll, or layout persistence
- `TP-053` — removed the remaining top app brand header/global safety strip and compacted market-monitor filters while preserving module safety surfaces
- `TP-054` — restored visible stock chart rendering with measured `lightweight-charts` sizing, non-collapsing chart layout, truthful empty/provider states, and chart visibility validation
- `TP-055` — refactored the frontend into an original black/graphite/amber institutional terminal palette, reduced cyan/blue-gradient dominance, aligned chart colors, and added theme validation
- `TP-056` — added purpose-matched icons for enabled and visible-disabled rail modules, local accessible icon-first rail collapse behavior, and rail validation
- `TP-057` — made the market monitor table own visible vertical and horizontal scrollbars for wide exact-identity/action columns and added scrollbar validation

`TP-058` delivered the paper-capital source packet for the backend/backtesting
MVP wave. `TP-059` added the first-class saved backtesting domain, Postgres
persistence, REST API, and contract validation. `TP-060` added the API-hosted
async runner, restart recovery, server-side market-data/analysis execution,
best-effort cancellation, and `/hubs/backtests` SignalR updates without changing
public REST route names. `TP-061` expanded the saved-run contract with SMA
crossover, RSI mean-reversion, and breakout built-ins, validated
parameters/costs/slippage, rich provider-neutral result envelopes, and
buy-and-hold benchmarks while keeping LEAN-only/no-custom-code/no-order
guardrails. `TP-062` added the enabled terminal BACKTEST rail module, API-only
backtest client/workflow, paper-capital-backed run form, live status, saved
history/detail, cancel, retry, and frontend backtest workspace validation.
`TP-063` added completed-run-only saved-run comparison, metrics table/cards,
persisted strategy/buy-and-hold equity overlays, and comparison validation.

No ready implementation tasks are currently queued. Completed task packets
through `TP-063` are present in `tasks/`; completed packets should be archived
when convenient. The next new Taskplane packet should use `TP-064`.

## Follow-Up Direction

Future frontend work should build on the direct module/workflow frame,
rail-first full-viewport workspace, compact market-monitor filters, visible
market-monitor table scrollbars, non-collapsing chart visibility contract,
original black/graphite/amber terminal palette, and accessible icon-first rail collapse behavior established by `ATradeTerminalApp`,
`frontend/types/terminal.ts`,
`TerminalWorkspaceLayout`, `terminalModuleRegistry`,
`terminalMarketMonitorWorkflow`, `terminalChartWorkspaceWorkflow`,
`terminalAnalysisWorkflow`, `terminalBacktestWorkflow`, and
`BacktestComparisonPanel`. New modules should remain visible-disabled until
backed by real `ATrade.Api` contracts, provider-neutral data, and
documentation/tests; do not reintroduce the removed command system, the old
shell/list-page paths, app-level brand header, visible global safety strip,
context/monitor/footer chrome, page-level scrolling, fake data, direct
provider/database access, or order-entry UI paths.

## Guardrails

- Keep the repo-local startup contract as `start run` on Unix and Windows.
- Use `ATrade.slnx` for repo-level .NET build/test/list guidance; retain `ATrade.sln` only as a temporary non-authoritative compatibility artifact.
- Keep secrets, IBKR credentials, account identifiers, tokens, and session cookies out of git.
- Real IBKR/iBeam and LEAN checks must use ignored `.env` values and cleanly skip when local runtimes or credentials are unavailable.
- Local `voyz/ibeam:latest` Client Portal traffic uses HTTPS on the configured gateway port; self-signed certificate trust must stay scoped to loopback iBeam development traffic.
- Do not add real order placement or live-trading behavior in this queued batch.
- Update active docs in the same change as durable code/runtime changes.

## Next Task ID

`TP-064`
