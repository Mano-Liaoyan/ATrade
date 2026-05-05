---
status: active
owner: maintainer
updated: 2026-05-05
summary: Current implementation plan after the ATrade paper workspace frontend reconstruction, no-command cutover, simplified workspace layout, and restored stock chart visibility.
see_also:
  - README.md
  - docs/INDEX.md
  - docs/design/atrade-terminal-ui.md
  - scripts/README.md
  - tasks/CONTEXT.md
---

# ATrade Current Plan

**Last updated:** 2026-05-05

## Current Focus

The provider-backed paper-trading workspace slice is runnable with IBKR/iBeam
market data, TimescaleDB cache-aside, durable Postgres watchlists, exact
provider/market pins, configurable local AppHost ports, optional
AppHost-managed LEAN Docker runtime wiring, and the completed `TP-045` through
`TP-054` frontend reconstruction, no-command cutover, layout simplification,
top-chrome/filter-density cleanup, and stock chart visibility restoration. The
current frontend surface is the clean-room ATrade paper workspace: direct
module/workflow navigation,
enabled/current workflow modules, visible-disabled future modules, compact dense
market monitor, visibly sized chart/analysis workspaces, provider diagnostics,
a rail-first full-bleed single-primary workspace layout with no app-level brand header,
visible global safety strip, shell context/monitor/footer chrome, or page-level
vertical scrolling, and final cutover/no-command/simplified-layout/top-chrome
filter-density/chart-visibility guardrails for clean-room, no-order, truthful
provider-state, and `ATrade.Api` browser
boundaries. The active clean-room UI design authority remains
`docs/design/atrade-terminal-ui.md`.

Current repository contracts remain:

- use `ATrade.slnx` as the authoritative solution reference for active build/test guidance
- keep the local IBKR/iBeam refresh transport on the HTTPS Client Portal contract
- keep credentials, account identifiers, tokens, cookies, and live-trading behavior out of committed files and active defaults
- keep frontend/browser data access behind `ATrade.Api`; the frontend must not connect directly to Postgres or TimescaleDB
- keep durable runtime/code changes paired with active documentation updates

## Active Task Queue

The frontend reconstruction queue is complete/follow-up-ready through the
rail-first top-chrome/filter-density cleanup and stock chart visibility restoration:

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

The next new Taskplane packet should use `TP-055`.

Completed task packets through `TP-054` are present in `tasks/`; completed
packets should be archived when convenient. The orchestrator handles active task
folder archival after merge.

## Follow-Up Direction

Future frontend work should build on the direct module/workflow frame,
rail-first full-viewport workspace, compact market-monitor filters, and
non-collapsing chart visibility contract established by `ATradeTerminalApp`,
`frontend/types/terminal.ts`,
`TerminalWorkspaceLayout`, `terminalModuleRegistry`,
`terminalMarketMonitorWorkflow`, `terminalChartWorkspaceWorkflow`, and
`terminalAnalysisWorkflow`. New modules should remain visible-disabled until
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

`TP-055`
