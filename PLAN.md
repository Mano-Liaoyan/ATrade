---
status: active
owner: maintainer
updated: 2026-04-30
summary: Current implementation plan for the provider-backed ATrade paper-trading workspace upgrade and follow-up runtime cleanup.
see_also:
  - README.md
  - docs/INDEX.md
  - scripts/README.md
  - tasks/CONTEXT.md
---

# ATrade Current Plan

**Last updated:** 2026-04-30

## Current Focus

A new follow-up batch (`TP-028` through `TP-032`) is queued to harden the
provider-backed paper-trading workspace around real IBKR/iBeam market data,
TimescaleDB persistence, durable/exact watchlist pins, and local AppHost
configuration. Current repository contracts are:

- use `ATrade.slnx` as the authoritative solution reference for active build/test guidance
- keep the local IBKR/iBeam refresh transport on the HTTPS Client Portal contract
- keep credentials, account identifiers, tokens, cookies, and live-trading behavior out of committed files and active defaults
- keep frontend/browser data access behind `ATrade.Api`; the frontend must not connect directly to Postgres or TimescaleDB

## Active Task Queue

Ready implementation tasks:

- `TP-028` — fix IBKR/iBeam scanner request `411 Length Required` failures on `/api/market-data/trending`
- `TP-029` — add the TimescaleDB market-data persistence foundation and configurable freshness option
- `TP-030` — serve market-data endpoints from fresh TimescaleDB rows first, then refresh from IBKR/iBeam and persist on miss/stale data
- `TP-031` — fix watchlist restart persistence and make search pins exact to provider/market identity with market badges
- `TP-032` — make the Aspire dashboard UI port configurable through `.env`

The next new Taskplane packet should use `TP-033`.

Completed task packets `TP-019` through `TP-027` remain under `tasks/` with
`.DONE` markers pending archival. Older completed packets are archived under
`tasks/archive/`.

## Execution Order

Recommended orchestration order:

1. Wave 1 can run in parallel where file scopes allow: `TP-028`, `TP-029`, `TP-031`, and `TP-032`.
2. Wave 2: `TP-030` after both `TP-028` and `TP-029` are complete.

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

`TP-033`
