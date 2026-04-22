---
status: active
owner: architect
updated: 2026-04-22
summary: Thin pointer for Claude Code users to the authoritative repository contracts.
see_also:
  - AGENT.md
  - docs/INDEX.md
---

# CLAUDE.md

This file is intentionally thin.

The repository-wide operating contract now lives in `AGENT.md`, not here.

## Read Order

When working in this repository, use this order:

1. `AGENT.md`
2. `agents/<role>.md`
3. `skills/retrieve-plan/SKILL.md`
4. `plans/<role>/CURRENT.md`
5. `docs/INDEX.md` and only documents marked `active`
6. Task-specific skills under `skills/`

## Current Reality

- This repository is defining the next implementation, not preserving the previous one
- The target frontend is `Next.js`, not Blazor
- The target local orchestrator is `Aspire 13.2`
- The target startup contract is `go run`
- Existing legacy module docs remain in the repo for review, but they are not authoritative unless `docs/INDEX.md` marks them `active`

## Tooling Guidance

- Do not duplicate repo policy here; update `AGENT.md` instead
- Do not treat old top-level commands as valid unless they are still documented in `scripts/README.md`
- Use `.worktrees/` for isolated parallel delivery once feature branches start to be created
