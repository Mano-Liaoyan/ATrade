---
status: active
owner: maintainer
updated: 2026-04-29
summary: Repository guidance after removal of the old role-based autonomous workforce files.
see_also:
  - README.md
  - PLAN.md
  - docs/INDEX.md
  - tasks/CONTEXT.md
---

# ATrade Agent Guidance

The old role-based autonomous workforce has been removed from this repository.
Do not look for per-role plans, repo-local workforce skills, or role charters;
those files intentionally no longer exist.

## Current Coordination Model

- Implementation work is tracked as Taskplane packets under `tasks/`.
- Active tasks currently start at `TP-019` and run through `TP-025`.
- Completed task packets are archived under `tasks/archive/`.
- The next task ID is recorded in `tasks/CONTEXT.md`.

## Startup Order For Coding Sessions

1. Read `README.md` for the current repository overview.
2. Read `PLAN.md` for the active work queue.
3. Read `tasks/CONTEXT.md` for Taskplane state and the next task ID.
4. Read `docs/INDEX.md` and then only the active docs needed for the task.
5. Read the relevant task packet (`PROMPT.md` / `STATUS.md`) before changing code.

## Guardrails

- Keep the `start run` contract intact across Unix and Windows shims.
- Keep secrets, IBKR credentials, account identifiers, tokens, and session cookies out of git.
- Real IBKR/iBeam and LEAN verification must use ignored local `.env` values and cleanly skip when the required local runtime is unavailable.
- Do not add real order placement or live-trading behavior in the current queued work.
- Durable code/runtime changes must update active documentation in the same change.
- Use `docs/INDEX.md` as the documentation discovery layer; only `active` docs are implementation authority.

## Remaining `.pi/agents` Files

The remaining `.pi/agents/` files are Taskplane runtime agents used by the
orchestrator (`task-worker`, `task-reviewer`, `task-merger`, and `supervisor`).
They are not the removed role-based ATrade workforce.
