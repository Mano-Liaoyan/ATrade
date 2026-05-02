---
status: active
owner: maintainer
updated: 2026-05-02
summary: Current implementation plan for the ATrade paper-trading workspace architecture deepening queue.
see_also:
  - README.md
  - docs/INDEX.md
  - scripts/README.md
  - tasks/CONTEXT.md
---

# ATrade Current Plan

**Last updated:** 2026-05-02

## Current Focus

The provider-backed paper-trading workspace slice is runnable with IBKR/iBeam
market data, TimescaleDB cache-aside, durable Postgres watchlists, exact
provider/market pins, configurable local AppHost ports, and optional
AppHost-managed LEAN Docker runtime wiring. The next queued batch (`TP-036`
through `TP-041`) is an architecture deepening program focused on making the
runtime contract, Exact Instrument Identity, market-data reads, IBKR/iBeam
session readiness, backend intake modules, and frontend workflow modules deeper
and easier to test.

Current repository contracts remain:

- use `ATrade.slnx` as the authoritative solution reference for active build/test guidance
- keep the local IBKR/iBeam refresh transport on the HTTPS Client Portal contract
- keep credentials, account identifiers, tokens, cookies, and live-trading behavior out of committed files and active defaults
- keep frontend/browser data access behind `ATrade.Api`; the frontend must not connect directly to Postgres or TimescaleDB
- keep durable runtime/code changes paired with active documentation updates

## Active Task Queue

Ready implementation tasks:

- `TP-036` — deepen the local runtime contract module and fix committed runtime/default drift
- `TP-037` — deepen the Exact Instrument Identity module across market data, Timescale, Workspaces, and frontend pins
- `TP-038` — deepen the market-data read module into an async, cache-aware read seam
- `TP-039` — deepen the shared IBKR/iBeam session readiness module for broker, market-data, and worker callers
- `TP-040` — deepen analysis and workspace watchlist intake modules so `ATrade.Api` delegates domain ordering
- `TP-041` — deepen frontend workspace workflow modules for watchlist, search, chart, and stream fallback orchestration

The next new Taskplane packet should use `TP-042`.

Completed task packets `TP-019` through `TP-035` remain under `tasks/` with
`.DONE` markers pending archival. Older completed packets are archived under
`tasks/archive/`.

## Execution Order

Recommended orchestration order:

1. `TP-036` first, because it stabilizes safe local runtime defaults and shared contract loading.
2. `TP-037` after `TP-036`, because Exact Instrument Identity becomes the shared provider/market identity language for later tasks.
3. `TP-038` after `TP-037`, because the market-data read seam should preserve the deepened identity model.
4. `TP-039` after `TP-038`, because IBKR/iBeam readiness adapts the provider modules after the read seam stabilizes.
5. `TP-040` after `TP-038` and `TP-039`, because backend intake modules consume both stable market-data reads and stable provider errors.
6. `TP-041` after `TP-040`, because frontend workflows should follow stable backend identity/intake behavior.

The orchestrator dependency sections in each `PROMPT.md` are the machine-readable
source for batch ordering.

## Guardrails

- Keep the repo-local startup contract as `start run` on Unix and Windows.
- Use `ATrade.slnx` for repo-level .NET build/test/list guidance; retain `ATrade.sln` only as a temporary non-authoritative compatibility artifact.
- Keep secrets, IBKR credentials, account identifiers, tokens, and session cookies out of git.
- Real IBKR/iBeam and LEAN checks must use ignored `.env` values and cleanly skip when local runtimes or credentials are unavailable.
- Local `voyz/ibeam:latest` Client Portal traffic uses HTTPS on the configured gateway port; self-signed certificate trust must stay scoped to loopback iBeam development traffic.
- Do not add real order placement or live-trading behavior in this queued batch.
- Update active docs in the same change as durable code/runtime changes.

## Next Task ID

`TP-042`
