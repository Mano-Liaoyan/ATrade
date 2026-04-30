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
has landed. Current follow-up work keeps the repository contracts aligned:

- make `ATrade.slnx` the authoritative solution reference for active build/test guidance
- fix the local IBKR/iBeam refresh transport contract
- keep credentials, account identifiers, tokens, cookies, and live-trading behavior out of committed files and active defaults

## Active Task Queue

| Task | Status | Depends on | Summary |
|------|--------|------------|---------|
| `TP-026` | In progress | `TP-025` | Migrate active solution references to authoritative `ATrade.slnx`. |
| `TP-027` | Ready after deps | `TP-026` | Fix the local IBKR/iBeam refresh transport contract. |

Completed task packets `TP-019` through `TP-025` remain under `tasks/` with
`.DONE` markers pending archival. Older completed packets are archived under
`tasks/archive/`.

## Execution Order

1. Complete `TP-026` so active scripts, docs, and future task prompts prefer `ATrade.slnx`.
2. Run `TP-027` after `TP-026` so the iBeam refresh transport fix lands on the updated solution-file contract.

The orchestrator dependency sections in each `PROMPT.md` are the machine-readable
source for batch ordering.

## Guardrails

- Keep the repo-local startup contract as `start run` on Unix and Windows.
- Use `ATrade.slnx` for repo-level .NET build/test/list guidance; retain `ATrade.sln` only as a temporary non-authoritative compatibility artifact.
- Keep secrets, IBKR credentials, account identifiers, tokens, and session cookies out of git.
- Real IBKR/iBeam and LEAN checks must use ignored `.env` values and cleanly skip when local runtimes or credentials are unavailable.
- Do not add real order placement or live-trading behavior in this queued batch.
- Update active docs in the same change as durable code/runtime changes.

## Next Task ID

`TP-028`
