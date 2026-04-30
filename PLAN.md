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

The provider-backed paper-trading workspace batch (`TP-019` through `TP-025`)
and follow-up runtime cleanup tasks (`TP-026` / `TP-027`) have landed. Current
repository contracts are:

- use `ATrade.slnx` as the authoritative solution reference for active build/test guidance
- keep the local IBKR/iBeam refresh transport on the HTTPS Client Portal contract
- keep credentials, account identifiers, tokens, cookies, and live-trading behavior out of committed files and active defaults

## Active Task Queue

No ready implementation task is currently queued. The next new Taskplane packet
should use `TP-028`.

Completed task packets `TP-019` through `TP-027` remain under `tasks/` with
`.DONE` markers pending archival. Older completed packets are archived under
`tasks/archive/`.

## Execution Order

The `TP-019` through `TP-027` batch is complete. Archive completed task packets
when orchestration cleanup time allows, then queue follow-up work starting at
`TP-028`.

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

`TP-028`
