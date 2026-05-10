---
status: active
owner: maintainer
updated: 2026-05-10
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
- No ready implementation tasks are currently queued after completion of `TP-072` Exact Instrument Identity provider-neutral key deepening.
- `TP-064` through `TP-068` completed the frontend route/visibility UX batch; `TP-069` through `TP-071` completed the Compose-managed infrastructure startup cutover; `TP-072` deepened provider-neutral Exact Instrument Identity keys and saved backtest identity.
- Completed task packets through `TP-072` are present in `tasks/`; completed packets should be archived when convenient.
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
- `ask-and-plan` — clarify rough requirements one question at a time with
  recommendations, then stage small Taskplane task packets with dependencies,
  verification, and durable memory updates when requested.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues for `Mano-Liaoyan/ATrade`. See `docs/agents/issue-tracker.md`.

### Triage labels

The default engineering-skill triage labels are used. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `tasks/CONTEXT.md` is the repo domain context, with active docs discovered through `docs/INDEX.md`; ADRs live under `docs/adr/` when added. See `docs/agents/domain.md`.

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
- Frontend desktop browser behavior is a major product guardrail: latest stable Safari, Firefox, Chrome, and Edge must behave consistently; page-level scrolling can remain disabled only if every overflowing rail/workspace/panel/table/module region owns visible internal/custom scroll affordances and no content is clipped or unreachable. Treat rail entries, visible-disabled modules such as NODE/ORDERS, detail panels, and wide tables as scroll-owned regions; Safari may hide native OS scrollbars, so use app-owned or explicitly styled tracks/thumbs where reachability matters. Mobile optimization is not in scope for the current frontend UX batch beyond preserving existing fallbacks.
- Durable code/runtime changes must update active documentation in the same change.
- Use `docs/INDEX.md` as the documentation discovery layer; only `active` docs are implementation authority.
