---
name: retrieve-plan
description: Use when any agent starts work and needs its role-specific current plan, the root bootstrap plan, and the authoritative active documents before making decisions.
---

# Retrieve Plan

## Overview

Read the correct plan before starting work.

The repository has two planning levels:

- `plans/<role>/CURRENT.md` — the role's live plan and resume notes
- `PLAN.md` — the root bootstrap and cross-role milestone plan

**Core principle:** agents start from their own role plan, then read the root plan for shared context.

## When to Use

- Every new session
- Before claiming an issue or PR
- Before proposing work to another agent
- Before answering status questions
- Before resuming blocked or previously paused work

## How to Retrieve

1. Identify the role first.

   Example role IDs:
   - `architect`
   - `senior-engineer`
   - `senior-test-engineer`
   - `devops`
   - `scrum-master`
   - `code-reviewer`
   - `handyman`
   - `onboarder`

2. Read `plans/<role>/CURRENT.md`.
3. Read `PLAN.md`.
4. Read `docs/INDEX.md`.
5. Only follow documents whose status is `active`.
6. If a task references a draft PR or GitHub issue, read that last for task-local state.

## What to Extract

Hold these in context:

- The role's current focus
- The role's blockers and resume notes
- Cross-role milestones from `PLAN.md`
- Any issue or PR references already assigned to the role
- Which docs are `active`
- Which docs are `legacy-review-pending` or `obsolete` and therefore non-authoritative

## How to Resolve Ambiguity

- If `plans/<role>/CURRENT.md` does not exist, stop and route the problem to the Onboarder or Architect.
- If the role plan and `PLAN.md` disagree, the role plan controls immediate work and `PLAN.md` must be updated later.
- If a referenced document is not marked `active` in `docs/INDEX.md`, treat it as historical context only.
- If a cloned role is in use, such as multiple code reviewers, the shared role plan still applies and the issue/PR carries the instance-specific state.

## Quick Reference

| Need | Read |
|------|------|
| Immediate role work | `plans/<role>/CURRENT.md` |
| Shared repository milestones | `PLAN.md` |
| Authoritative docs list | `docs/INDEX.md` |
| Role charter | `.pi/agents/<role>.md` |
| Task-specific state | linked issue or draft PR |

## Integration with Other Skills

- Load `retrieve-plan` first.
- Then apply `karpathy-guidelines` as the general operating rule.
- If the work splits into independent tracks, use `parallel-worktree-development`.
- When work finishes or pauses, use `update-plan`.

## Common Mistakes

- Starting from `README.md` instead of the role plan
- Treating `legacy-review-pending` docs as current truth
- Skipping `PLAN.md` and missing a cross-role dependency
- Forgetting to read the linked issue or draft PR when resuming blocked work
