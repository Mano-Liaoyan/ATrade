---
status: active
owner: maintainer
updated: 2026-05-21
summary: Repository guidance and repo-local agent skills.
see_also:
  - README.md
  - PLAN.md
  - docs/INDEX.md
---

# ATrade Agent Guidance

## Current Coordination Model

- Implementation work is tracked in GitHub Issues and pull requests for
  `Mano-Liaoyan/ATrade`.
- `README.md` describes the current runnable surface and repository contract.
- `PLAN.md` describes the current implementation direction.
- `docs/INDEX.md` is the documentation discovery layer; only documents marked
  `active` are implementation authority.

## Repo-Local Agent Skills

Reusable prompt skills are available under `.agents/skills/`. These are opt-in
skills for the current agent session.

- `skills-lock.json` records installed skill sources and hashes.
- Keep `.agents/skills/` and `skills-lock.json` in sync when adding, updating,
  or removing repo-local skills.

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

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues for `Mano-Liaoyan/ATrade`. See `docs/agents/issue-tracker.md`.

### Triage labels

The default engineering-skill triage labels are used. See `docs/agents/triage-labels.md`.

### Domain docs

No central project context file is used. Use `docs/INDEX.md` to discover active docs; ADRs live under `docs/adr/` when added. See `docs/agents/domain.md`.

## Startup Order For Coding Sessions

1. Read `README.md` for the current repository overview.
2. Read `PLAN.md` for the active implementation direction.
3. Read `docs/INDEX.md` and then only the active docs needed for the task.
4. Read the relevant GitHub issue or PR when one is supplied.

## Guardrails

- Keep the `start run` contract intact across Unix and Windows shims.
- Keep secrets, IBKR credentials, account identifiers, tokens, and session cookies out of git.
- Real IBKR/iBeam and LEAN verification must use ignored local `.env` values and cleanly skip when the required local runtime is unavailable.
- Do not add real order placement or live-trading behavior in current defaults.
- Frontend desktop browser behavior is a major product guardrail: latest stable Safari, Firefox, Chrome, and Edge must behave consistently; page-level scrolling can remain disabled only if every overflowing rail/workspace/panel/table/module region owns visible internal/custom scroll affordances and no content is clipped or unreachable. Treat rail entries, visible-disabled modules such as NODE/ORDERS, detail panels, and wide tables as scroll-owned regions; Safari may hide native OS scrollbars, so use app-owned or explicitly styled tracks/thumbs where reachability matters. Mobile optimization is not in scope beyond preserving existing fallbacks.
- Durable code/runtime changes must update active documentation in the same change.
- Use `docs/INDEX.md` as the documentation discovery layer; only `active` docs are implementation authority.
