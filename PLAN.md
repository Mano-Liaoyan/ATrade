---
status: active
owner: maintainer
updated: 2026-05-04
summary: Current implementation plan for the active ATrade Terminal frontend reconstruction queue.
see_also:
  - README.md
  - docs/INDEX.md
  - docs/design/atrade-terminal-ui.md
  - scripts/README.md
  - tasks/CONTEXT.md
---

# ATrade Current Plan

**Last updated:** 2026-05-04

## Current Focus

The provider-backed paper-trading workspace slice is runnable with IBKR/iBeam
market data, TimescaleDB cache-aside, durable Postgres watchlists, exact
provider/market pins, configurable local AppHost ports, optional
AppHost-managed LEAN Docker runtime wiring, and completed frontend refinement
work through `TP-044`. The current active queue is `TP-045` through `TP-050`,
focused on a full ATrade Terminal frontend reconstruction inspired by modern
institutional terminal UIs while preserving clean-room implementation,
paper-only safety, provider-neutral API boundaries, and current ATrade
workflows. The active clean-room UI design authority for this queue is
`docs/design/atrade-terminal-ui.md`.

Current repository contracts remain:

- use `ATrade.slnx` as the authoritative solution reference for active build/test guidance
- keep the local IBKR/iBeam refresh transport on the HTTPS Client Portal contract
- keep credentials, account identifiers, tokens, cookies, and live-trading behavior out of committed files and active defaults
- keep frontend/browser data access behind `ATrade.Api`; the frontend must not connect directly to Postgres or TimescaleDB
- keep durable runtime/code changes paired with active documentation updates

## Active Task Queue

Ready implementation tasks:

- `TP-045` — define the active ATrade Terminal UI design spec and clean-room visual guardrails
- `TP-046` — bootstrap the shadcn/Tailwind/Radix terminal UI stack and original ATrade primitives
- `TP-047` — build the terminal shell, deterministic command registry, module rail, and resizable layout persistence
- `TP-048` — rebuild search, trending, and watchlist as a dense terminal market monitor
- `TP-049` — rebuild chart and analysis as terminal workspaces inside the new shell
- `TP-050` — complete frontend cutover, cleanup, verification, and documentation updates

The next new Taskplane packet should use `TP-051`.

Completed task packets through `TP-044` are present in `tasks/`; completed
packets should be archived before or after the new redesign batch when convenient.

## Execution Order

Recommended orchestration order:

1. `TP-045` first, because the design spec becomes the active authority for visual, command, module, layout, and clean-room decisions.
2. `TP-046` after `TP-045`, because the Tailwind/shadcn/Radix-compatible terminal UI foundation must follow the approved spec.
3. `TP-047` after `TP-046`, because the shell, module registry, command input, and resizable layout depend on the UI primitives.
4. `TP-048` after `TP-047`, because the market monitor plugs into the terminal shell and command/module registry.
5. `TP-049` after `TP-048`, because chart/analysis actions must preserve market-monitor exact identity handoff.
6. `TP-050` last, because it is the full cutover, cleanup, safety, and documentation verification gate.

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

`TP-051`
