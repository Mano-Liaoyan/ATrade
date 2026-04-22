---
status: active
owner: architect
updated: 2026-04-22
summary: Repository-wide operating contract for the autonomous ATrade workforce.
see_also:
  - README.md
  - PLAN.md
  - docs/INDEX.md
---

# ATrade Agent Contract

## Purpose

This repository is designed to be developed by an autonomous, parallel, documentation-first workforce.

The contract in this file is repository-wide and authoritative for all agents unless a direct user instruction overrides it.

## Non-Negotiables

Every agent must follow these rules:

1. Read its role plan before starting work.
2. Use `karpathy-guidelines` as the default behavioral baseline.
3. Use `retrieve-plan` before acting and `update-plan` before stopping.
4. Treat `docs/INDEX.md` as the documentation discovery layer.
5. Use only documents marked `active` as implementation authority.
6. Update documentation in the same change that introduces durable repository changes.
7. Prefer parallel work through isolated git worktrees once the repository has a baseline commit.
8. Continue with other ready work when blocked on human approval.

## Startup Sequence

Every agent starts with this sequence:

1. Identify its role.
2. Read `.pi/agents/<role>.md`.
3. Load `.pi/skills/retrieve-plan/SKILL.md`.
4. Read `plans/<role>/CURRENT.md`.
5. Read `PLAN.md`.
6. Read `docs/INDEX.md` and only then consult any `active` docs referenced there.
7. Load any task-specific skills.

## Workforce Roles

The default workforce is:

- `architect`
- `senior-engineer`
- `senior-test-engineer`
- `devops`
- `scrum-master`
- `code-reviewer`
- `handyman`
- `onboarder`

Each role has a charter in `.pi/agents/` and a live plan in `plans/<role>/CURRENT.md`.

## Operating Loop

Every role follows the same loop:

1. Retrieve plan.
2. Claim one issue or PR-sized unit of work.
3. Move the work into an isolated worktree when worktrees are available.
4. Implement or review using the appropriate skills.
5. Update docs for durable repository changes.
6. Update the role plan.
7. Hand work back through GitHub issue and PR state.

## Model Tier Policy

Roles choose from three model tiers:

- `quality`: highest reasoning depth, slower, more expensive
- `balanced`: solid quality for everyday engineering work
- `cheap`: low-cost, fast, reserved for narrow low-risk work

The exact model names are not hard-coded here. Each role file declares its preferred tier. The `.pi/skills/selecting-model-tier/SKILL.md` rubric governs exceptions.

## Parallelism

Parallelism is the default once git worktrees are available.

- One active issue maps to one branch and one worktree.
- One worktree has one responsible agent at a time.
- Multiple agents may review in parallel only when they are not changing the same branch state.
- When tasks overlap heavily, they must be sequenced deliberately.

Use `.pi/skills/parallel-worktree-development/SKILL.md` whenever 2 or more independent issues can proceed in parallel.

## GitHub-Native Coordination

GitHub is the shared scheduler and audit trail.

- Issues represent units of work.
- Draft PRs represent in-flight code state.
- Labels represent workflow state.
- Actions represent CI and automation triggers.

Recommended workflow labels:

- `agent:ready`
- `agent:claimed`
- `agent:in-progress`
- `agent:needs-human`
- `agent:blocked`
- `agent:resume-ready`
- `agent:review`
- `agent:merged`
- `agent:docs-required`
- `agent:trivial`

Recommended role labels:

- `role:architect`
- `role:senior-engineer`
- `role:senior-test-engineer`
- `role:devops`
- `role:scrum-master`
- `role:code-reviewer`
- `role:handyman`
- `role:onboarder`

## Plans

Plan ownership is per role.

- Active file: `plans/<role>/CURRENT.md`
- Archive path: `plans/<role>/archive/YYYY-MM-DD-<slug>.md`
- Shared milestones: `PLAN.md`

Plan rules:

- Read the role plan before work.
- Update the role plan after work.
- Keep `CURRENT.md` under about 150 lines.
- Archive before the file becomes unwieldy.
- Preserve resume notes when blocked.

## Documentation Contract

Documentation is mandatory work.

Whenever a durable repository artifact is added or materially changed, the same change must also:

1. add or update a document with frontmatter
2. update `docs/INDEX.md`
3. mark stale docs `obsolete` or `legacy-review-pending`

Required frontmatter fields:

- `status`
- `owner`
- `updated`
- `summary`
- `see_also`

Allowed document statuses:

- `active`
- `legacy-review-pending`
- `obsolete`

Agents must not use `legacy-review-pending` or `obsolete` docs as implementation authority.

## Worktree Bootstrap Rule

The first baseline commit establishes the minimum starting point for worktree-driven delivery.

After that baseline exists:

- use `.worktrees/` for isolated parallel implementation
- keep one active issue per worktree
- do not treat the main working tree as the default place for parallel feature work

## Skill Policy

All agents follow the repository skill stack.

- Always use `karpathy-guidelines` as the general operating rule.
- Always use `retrieve-plan` before work.
- Always use `update-plan` before stopping.
- Use role- and task-specific skills as required.

## Role Evolution

The workforce may evolve.

A new role is added only when repeated work does not fit an existing role cleanly.

The flow is:

1. Architect identifies the recurring gap.
2. Scrum Master opens an issue for role creation.
3. Onboarder creates the role charter, plan scaffold, and any required skills.
4. Code Reviewer reviews the governance change.
5. The new role enters rotation.

Use `.pi/skills/onboarding-new-agent/SKILL.md` for that process.

## Human Escalation

Human escalation is required for:

- secrets or credential handling
- money-moving or trading-policy changes
- destructive data migrations
- licensing changes
- new third-party services with cost or compliance implications
- any case where the user explicitly requests approval

When blocked on approval:

1. update the issue label to `agent:needs-human`
2. leave a precise unblock note
3. update the role plan resume note
4. switch to another ready item if one exists

## Review Policy

No meaningful change is considered done until a code-reviewer agent or equivalent review pass has checked it.

Reviewers focus on:

- correctness
- regression risk
- missing tests
- missing docs
- mismatch with the Architect's intent

## Single Command Contract

The target startup contract for the repository is the repo-local `start` shim.

That contract must be implemented on both Unix and Windows and must delegate to Aspire AppHost so one command brings up the backend, workers, frontend, and infrastructure.

Canonical invocations:

- Unix-like: `./start run`
- Windows: `./start.ps1 run` or `./start.cmd run`

Within repository documentation, `start run` refers to this shim contract, not the Windows shell built-in. Use explicit relative paths on Windows.

The design lives in `scripts/README.md`.

## Final Rule

Agents optimize for forward progress without losing auditability.

If progress is not recorded in plans, issues, PRs, and docs, it does not count as durable work.
