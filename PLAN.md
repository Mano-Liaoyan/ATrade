---
status: active
owner: maintainer
updated: 2026-05-04
summary: Current implementation plan after the ATrade Terminal frontend reconstruction queue.
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
`TP-050` ATrade Terminal frontend reconstruction. The current frontend surface is
the clean-room ATrade Terminal: deterministic command navigation, enabled/current
workflow modules, visible-disabled future modules, dense market monitor,
terminal chart/analysis workspaces, provider diagnostics, resizable local-only
layout persistence, and final cutover guardrails for clean-room, no-order, and
`ATrade.Api` browser boundaries. The active clean-room UI design authority
remains `docs/design/atrade-terminal-ui.md`.

Current repository contracts remain:

- use `ATrade.slnx` as the authoritative solution reference for active build/test guidance
- keep the local IBKR/iBeam refresh transport on the HTTPS Client Portal contract
- keep credentials, account identifiers, tokens, cookies, and live-trading behavior out of committed files and active defaults
- keep frontend/browser data access behind `ATrade.Api`; the frontend must not connect directly to Postgres or TimescaleDB
- keep durable runtime/code changes paired with active documentation updates

## Active Task Queue

The terminal reconstruction queue is complete/follow-up-ready:

- `TP-045` — defined the active ATrade Terminal UI design spec and clean-room visual guardrails
- `TP-046` — bootstrapped the shadcn/Tailwind/Radix terminal UI stack and original ATrade primitives
- `TP-047` — built the terminal shell, deterministic command registry, module rail, and resizable layout persistence
- `TP-048` — rebuilt search, trending, and watchlist as a dense terminal market monitor
- `TP-049` — rebuilt chart and analysis as terminal workspaces inside the new shell
- `TP-050` — completed frontend cutover, cleanup, verification, and documentation updates

The next new Taskplane packet should use `TP-051`.

Completed task packets through `TP-044` are present in `tasks/`; completed
packets should be archived when convenient. The orchestrator handles active task
folder archival after merge.

## Follow-Up Direction

Future frontend work should build on the terminal frame established by
`ATradeTerminalApp`, `frontend/types/terminal.ts`, `terminalModuleRegistry`,
`terminalCommandRegistry`, `terminalMarketMonitorWorkflow`,
`terminalChartWorkspaceWorkflow`, and `terminalAnalysisWorkflow`. New modules
should remain visible-disabled until backed by real `ATrade.Api` contracts,
provider-neutral data, and documentation/tests; do not reintroduce old shell,
list-page, fake-data, direct provider/database, or order-entry UI paths.

## Guardrails

- Keep the repo-local startup contract as `start run` on Unix and Windows.
- Use `ATrade.slnx` for repo-level .NET build/test/list guidance; retain `ATrade.sln` only as a temporary non-authoritative compatibility artifact.
- Keep secrets, IBKR credentials, account identifiers, tokens, and session cookies out of git.
- Real IBKR/iBeam and LEAN checks must use ignored `.env` values and cleanly skip when local runtimes or credentials are unavailable.
- Local `voyz/ibeam:latest` Client Portal traffic uses HTTPS on the configured gateway port; self-signed certificate trust must stay scoped to loopback iBeam development traffic.
- Do not add real order placement or live-trading behavior in this queued batch.
- Update active docs in the same change as durable code/runtime changes.

## Next Task ID

`TP-051`
