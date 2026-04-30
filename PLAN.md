---
status: active
owner: maintainer
updated: 2026-04-30
summary: Current implementation plan for the provider-backed ATrade paper-trading workspace upgrade.
see_also:
  - README.md
  - docs/INDEX.md
  - scripts/README.md
  - tasks/CONTEXT.md
---

# ATrade Current Plan

**Last updated:** 2026-04-30

## Current Focus

Deliver the provider-backed paper-trading workspace upgrade queued in `TP-019`
through `TP-025`, plus current maintenance follow-ups for solution metadata and
local iBeam transport (`TP-026` / `TP-027`):

- provider-neutral broker and market-data abstractions
- Postgres-persisted pinned symbols/watchlists
- `voyz/ibeam:latest` IBKR runtime with credentials read only from ignored `.env`
- real IBKR/iBeam market data and stock search
- provider-neutral analysis contracts
- LEAN as the first analysis engine provider

## Active Task Queue

| Task | Status | Depends on | Summary |
|------|--------|------------|---------|
| `TP-019` | Ready | `TP-016`, `TP-017` | Introduce provider-neutral broker and market-data abstractions. |
| `TP-020` | Ready after deps | `TP-018`, `TP-019` | Persist pinned stock watchlists in Postgres. |
| `TP-021` | Ready after deps | `TP-019` | Wire `voyz/ibeam:latest` and the ignored `.env` IBKR login contract. |
| `TP-022` | Ready after deps | `TP-019`, `TP-021` | Replace production mocked market data with the IBKR/iBeam provider. |
| `TP-023` | Ready after deps | `TP-020`, `TP-022` | Add IBKR stock search and pin-any-symbol workflow. |
| `TP-024` | Ready after deps | `TP-019`, `TP-022` | Add provider-neutral analysis engine abstraction and API contract. |
| `TP-025` | Ready after deps | `TP-022`, `TP-024` | Integrate LEAN as the first analysis engine provider. |
| `TP-026` | Ready | None | Migrate solution references and verification guidance to `ATrade.slnx`. |
| `TP-027` | In progress | None | Fix authenticated local iBeam refresh transport failures by using the HTTPS Client Portal contract. |

Completed task packets are archived under `tasks/archive/` after orchestrator merge.

## Execution Order

1. Run `TP-019` first to establish provider abstractions.
2. After `TP-019`, run `TP-020` and `TP-021` when their file-scope conflicts allow.
3. Run `TP-022` after `TP-021` to replace production market-data mocks.
4. Run `TP-023` after `TP-020` and `TP-022`.
5. Run `TP-024` after `TP-022`.
6. Run `TP-025` after `TP-024`.
7. Run `TP-026` / `TP-027` as maintenance follow-ups when their lanes are available.

The orchestrator dependency sections in each `PROMPT.md` are the machine-readable
source for batch ordering.

## Guardrails

- Keep the repo-local startup contract as `start run` on Unix and Windows.
- Keep secrets, IBKR credentials, account identifiers, tokens, and session cookies out of git.
- Real IBKR/iBeam and LEAN checks must use ignored `.env` values and cleanly skip when local runtimes or credentials are unavailable.
- Local `voyz/ibeam:latest` Client Portal traffic uses HTTPS on the configured gateway port; self-signed certificate trust must stay scoped to loopback iBeam development traffic.
- Do not add real order placement or live-trading behavior in this queued batch.
- Update active docs in the same change as durable code/runtime changes.

## Next Task ID

`TP-028`
