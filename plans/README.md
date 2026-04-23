---
status: active
owner: scrum-master
updated: 2026-04-22
summary: Explains the per-role planning system, archive rule, and plan file lifecycle.
see_also:
  - ../AGENTS.md
  - ../PLAN.md
  - ../.pi/skills/retrieve-plan/SKILL.md
  - ../.pi/skills/update-plan/SKILL.md
---

# Plans

This directory holds live role plans and their archives.

## Layout

- `plans/<role>/CURRENT.md` is the live plan for that role.
- `plans/<role>/archive/` stores rolled plans.
- `plans/TEMPLATE.md` is the starting point for any new role.

## Rules

1. Every role reads `CURRENT.md` before working.
2. Every role updates `CURRENT.md` before stopping.
3. When a current plan approaches 150 lines, archive it.
4. The archive filename should be `YYYY-MM-DD-<slug>.md`.
5. Carry forward only active items and the latest resume note.

## Relationship To `PLAN.md`

- `plans/<role>/CURRENT.md` is role-local and operational.
- `PLAN.md` is shared and milestone-oriented.

Role plans are updated more often than the root plan.
