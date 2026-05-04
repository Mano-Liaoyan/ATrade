---
status: active
owner: maintainer
updated: 2026-05-04
summary: Current implementation plan for the active ATrade paper-trading workspace UI refinement queue.
see_also:
  - README.md
  - docs/INDEX.md
  - scripts/README.md
  - tasks/CONTEXT.md
---

# ATrade Current Plan

**Last updated:** 2026-05-04

## Current Focus

The provider-backed paper-trading workspace slice is runnable with IBKR/iBeam
market data, TimescaleDB cache-aside, durable Postgres watchlists, exact
provider/market pins, configurable local AppHost ports, optional
AppHost-managed LEAN Docker runtime wiring, and completed architecture-deepening
work from `TP-002` through `TP-041` now archived under `tasks/archive/`. The
current active queue is `TP-042` through `TP-044`, focused on correcting chart
range semantics and improving the frontend workspace/search navigation before
the next run starts.

Current repository contracts remain:

- use `ATrade.slnx` as the authoritative solution reference for active build/test guidance
- keep the local IBKR/iBeam refresh transport on the HTTPS Client Portal contract
- keep credentials, account identifiers, tokens, cookies, and live-trading behavior out of committed files and active defaults
- keep frontend/browser data access behind `ATrade.Api`; the frontend must not connect directly to Postgres or TimescaleDB
- keep durable runtime/code changes paired with active documentation updates

## Active Task Queue

Ready implementation tasks:

- `TP-042` — correct chart range presets so chart time controls mean lookback ranges from now
- `TP-043` — redesign workspace navigation with a terminal-style shell inspired by finance-terminal information architecture
- `TP-044` — make stock search results easier to explore with bounded, ranked, filterable result UI

The next new Taskplane packet should use `TP-045`.

Completed task packets through `TP-041` are archived under `tasks/archive/`.

## Execution Order

Recommended orchestration order:

1. `TP-042` first, because chart range semantics should live behind the frontend workflow and market-data seams before UI layout changes.
2. `TP-043` after `TP-042`, because the redesigned shell repositions chart controls after their semantics are corrected.
3. `TP-044` after `TP-043`, because the search exploration UI should fit the new shell.

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

`TP-045`
