---
status: active
owner: maintainer
updated: 2026-04-30
summary: Repository guidance and introduction of repo-local Pi skills.
see_also:
  - README.md
  - PLAN.md
  - docs/INDEX.md
  - tasks/CONTEXT.md
---

# ATrade Agent Guidance

In the `.pi/agents/` directory , thereare Taskplane runtime agents used by the
orchestrator (`task-worker`, `task-reviewer`, `task-merger`, and `supervisor`).

## Current Coordination Model

- Implementation work is tracked as Taskplane packets under `tasks/`.
- Ready active tasks currently run from `TP-028` through `TP-032`.
- Completed task packets `TP-019` through `TP-027` remain under `tasks/` with `.DONE` markers pending archival; older completed packets are archived under `tasks/archive/`.
- The next task ID is recorded in `tasks/CONTEXT.md`.

## Repo-local Pi Skills

Reusable prompt skills are intentionally available under `.pi/skills/`. These are opt-in
skills for the current agent session, while implementation work remains coordinated
through Taskplane packets.

- `.pi/skills/*` entries are symlinks to committed skill definitions under
  `.agents/skills/`.
- `skills-lock.json` records their upstream source and hashes.
- Keep `.pi/skills/`, `.agents/skills/`, and `skills-lock.json` in sync when
  adding, updating, or removing skills.

Current installed skills include:

- `setup-matt-pocock-skills` — configure issue-tracker, triage-label, and
  domain-doc context before using engineering or issue-workflow skills.
- `grill-with-docs` and `zoom-out` — domain/documentation-aware planning and
  codebase orientation.
- `diagnose`, `tdd`, and `improve-codebase-architecture` — bug investigation,
  test-first changes, and architecture refactoring support.
- `to-prd`, `to-issues`, and `triage` — PRD, issue, and triage workflow helpers.
- `caveman`, `grill-me`, and `write-a-skill` — productivity and skill-authoring
  helpers.

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
