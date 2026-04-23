---
status: active
owner: scrum-master
updated: 2026-04-23
summary: Repository-side GitHub coordination contract for labels, sizing, blocked work, and resume flow.
see_also:
  - ../../AGENTS.md
  - ../../PLAN.md
  - ../../.github/labels.yml
  - ../../.github/ISSUE_TEMPLATE/implementation.yml
  - ../../.github/ISSUE_TEMPLATE/coordination.yml
  - ../../.github/PULL_REQUEST_TEMPLATE.md
---

# GitHub Coordination Primitives

This document turns the repository-wide guidance in [`AGENTS.md`](../../AGENTS.md)
and the live bootstrap direction in [`PLAN.md`](../../PLAN.md) into durable
GitHub primitives that agents and humans can follow without relying on chat
history.

## Coordination Surface

The repository-local coordination kit is:

- [`../../.github/labels.yml`](../../.github/labels.yml) for the shared label manifest
- [`../../.github/ISSUE_TEMPLATE/implementation.yml`](../../.github/ISSUE_TEMPLATE/implementation.yml) for implementation-ready work
- [`../../.github/ISSUE_TEMPLATE/coordination.yml`](../../.github/ISSUE_TEMPLATE/coordination.yml) for governance and workflow changes
- [`../../.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md) for PR handoff, verification, and resume notes

## Workflow-State Labels

Use issue labels as the source of truth for workflow state.

| Label | Meaning | When to apply |
|-------|---------|---------------|
| `agent:ready` | The issue is ready to be claimed. | Initial queued state after triage. |
| `agent:claimed` | A role has claimed the work. | As soon as an agent takes ownership and starts branch/worktree setup. |
| `agent:in-progress` | Work is actively happening. | During implementation, documentation, or verification work. |
| `agent:needs-human` | Work is blocked on a human answer or approval. | When the next step needs explicit human input. |
| `agent:blocked` | Work cannot proceed because of a non-human dependency. | When another issue, environment dependency, or prerequisite is missing. |
| `agent:resume-ready` | Previously blocked work can resume. | After the missing approval or dependency is resolved. |
| `agent:review` | Work is ready for reviewer attention. | After implementation and verification are complete. |
| `agent:merged` | The issue landed in the target branch. | After the PR is merged and cleanup is complete. |
| `agent:docs-required` | Durable changes still need required docs updates. | When code or governance changes are ahead of docs. |
| `agent:trivial` | The issue is intentionally lightweight and low risk. | For small cleanup work that still needs tracking. |

## Role Labels

Use exactly one owning role label on the issue at a time unless work is in an
explicit handoff state.

| Label | Typical ownership |
|-------|-------------------|
| `role:architect` | Architecture direction, repo contracts, or design decisions |
| `role:senior-engineer` | Implementation-ready product or repository changes |
| `role:senior-test-engineer` | Test strategy, harnesses, or verification-heavy work |
| `role:devops` | Infrastructure, CI, scripts, and environment contracts |
| `role:scrum-master` | Issue flow, planning, coordination, and process documentation |
| `role:code-reviewer` | Review passes, regression checks, and merge readiness |
| `role:handyman` | Small, low-risk cleanup or repo maintenance |
| `role:onboarder` | New role creation, skill scaffolding, and workforce bootstrap |

## Issue Sizing Rules

Size issues so one responsible agent can make forward progress in one branch and
one worktree without creating coordination debt.

| Size | Intended scope | Guidance |
|------|----------------|----------|
| `S` | Small, tightly scoped work | Usually one file or one narrow behavior/document update; target roughly half a day or less. |
| `M` | Default PR-sized slice | A focused change spanning a few related files with clear verification; target about one to two days. |
| `L` | Broad but still reviewable work | Crosses multiple files or docs and may require multiple verification steps; should still fit one branch with low overlap. |
| `XL` | Too large for unattended flow | Split before implementation into smaller issues whenever possible; use only as a temporary planning bucket, not the steady-state execution size. |

Sizing rules of thumb:

1. Prefer `M` as the default issue size for active implementation.
2. If an issue would require multiple independent reviewers or touches many unrelated areas, split it.
3. If the issue cannot be explained with one success-criteria block and one verification plan, it is probably `XL` and should be decomposed.
4. Blocked work should keep its original size unless the unblock reveals that the issue needs to be split.

## Blocked-Work and Resume Flow

Blocked work must remain resumable and visible in GitHub.

1. Start from `agent:ready`.
2. Move to `agent:claimed` when a role takes ownership.
3. Move to `agent:in-progress` once the responsible agent is actively working.
4. If a human decision is required, move the issue to `agent:needs-human` and leave:
   - a short unblock question on the issue or draft PR
   - a resume note in the relevant role plan
   - the current implementation context in the PR template or issue comments
5. If the blocker is external but not a human approval, move the issue to `agent:blocked` and record the dependency.
6. When the blocker clears, move the issue to `agent:resume-ready` so the next agent knows the work can continue.
7. Resume by re-reading the issue, draft PR, role plan, and active docs, then return the issue to `agent:in-progress`.
8. After verification, move to `agent:review`; after merge, move to `agent:merged`.

The key rule is to keep blockers out of private chat history. The issue, draft
PR, and role plan should all agree on the current state.

## Template Usage

- Use the implementation issue template for code-bearing or doc-bearing delivery work.
- Use the coordination issue template for governance, planning, and workflow updates.
- Use the PR template to capture linked issue, size, owning role, documentation impact, verification evidence, and resume notes.
- Keep [`docs/INDEX.md`](../INDEX.md) updated whenever durable docs change.

## Source Links

These coordination primitives are derived from the active repository contracts:

- [`AGENTS.md`](../../AGENTS.md)
- [`PLAN.md`](../../PLAN.md)
- [`docs/INDEX.md`](../INDEX.md)
- [`../../.github/labels.yml`](../../.github/labels.yml)
- [`../../.github/ISSUE_TEMPLATE/implementation.yml`](../../.github/ISSUE_TEMPLATE/implementation.yml)
- [`../../.github/ISSUE_TEMPLATE/coordination.yml`](../../.github/ISSUE_TEMPLATE/coordination.yml)
- [`../../.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md)
