---
status: active
owner: architect
updated: 2026-04-22
summary: Repository documentation index and authority map for human readers and autonomous agents.
see_also:
  - README.md
  - AGENT.md
  - docs/DOC_TEMPLATE.md
---

# Documentation Index

Only documents marked `active` are authoritative for implementation decisions.

## Authority Rules

- `active`: authoritative and discoverable
- `legacy-review-pending`: preserved for review but not authoritative
- `obsolete`: historical only, do not use for new work

## Top-Level Docs

| Path | Summary | Owner | Status | Updated | See also |
|------|---------|-------|--------|---------|----------|
| `README.md` | Human-facing overview of the new ATrade repository contract | architect | active | 2026-04-22 | `AGENT.md`, `PLAN.md` |
| `AGENT.md` | Repository-wide operating contract for the autonomous workforce | architect | active | 2026-04-22 | `agents/README.md`, `plans/README.md` |
| `PLAN.md` | Bootstrap milestones for the repository reboot | scrum-master | active | 2026-04-22 | `AGENT.md`, `scripts/README.md` |
| `CLAUDE.md` | Thin pointer to the current repo contract and read order | architect | active | 2026-04-22 | `AGENT.md`, `docs/INDEX.md` |

## Governance Docs

| Path | Summary | Owner | Status | Updated | See also |
|------|---------|-------|--------|---------|----------|
| `agents/README.md` | Index of role charters and new-role requirements | onboarder | active | 2026-04-22 | `AGENT.md`, `skills/onboarding-new-agent/SKILL.md` |
| `plans/README.md` | Explains per-role plans and archive rules | scrum-master | active | 2026-04-22 | `plans/TEMPLATE.md`, `PLAN.md` |
| `plans/TEMPLATE.md` | Template for role-local current plans | scrum-master | active | 2026-04-22 | `plans/README.md` |
| `docs/DOC_TEMPLATE.md` | Frontmatter and structure template for durable docs | architect | active | 2026-04-22 | `AGENT.md` |
| `scripts/README.md` | Design for the future cross-platform `go run` contract | devops | active | 2026-04-22 | `PLAN.md`, `AGENT.md` |

## Role Charters

| Path | Summary | Owner | Status | Updated | See also |
|------|---------|-------|--------|---------|----------|
| `agents/architect.md` | System design and boundary-setting charter | architect | active | 2026-04-22 | `plans/architect/CURRENT.md` |
| `agents/senior-engineer.md` | Implementation charter for approved architecture | senior-engineer | active | 2026-04-22 | `plans/senior-engineer/CURRENT.md` |
| `agents/senior-test-engineer.md` | TDD and regression-safety charter | senior-test-engineer | active | 2026-04-22 | `plans/senior-test-engineer/CURRENT.md` |
| `agents/devops.md` | Startup, AppHost, and CI/CD charter | devops | active | 2026-04-22 | `plans/devops/CURRENT.md` |
| `agents/scrum-master.md` | Issue and PR coordination charter | scrum-master | active | 2026-04-22 | `plans/scrum-master/CURRENT.md` |
| `agents/code-reviewer.md` | Correctness-first review charter | code-reviewer | active | 2026-04-22 | `plans/code-reviewer/CURRENT.md` |
| `agents/handyman.md` | Cheap trivial-work charter | handyman | active | 2026-04-22 | `plans/handyman/CURRENT.md` |
| `agents/onboarder.md` | New-role creation charter | onboarder | active | 2026-04-22 | `plans/onboarder/CURRENT.md` |

## Role Plans

| Path | Summary | Owner | Status | Updated | See also |
|------|---------|-------|--------|---------|----------|
| `plans/architect/CURRENT.md` | Live Architect priorities | architect | active | 2026-04-22 | `agents/architect.md` |
| `plans/senior-engineer/CURRENT.md` | Live Senior Engineer priorities | senior-engineer | active | 2026-04-22 | `agents/senior-engineer.md` |
| `plans/senior-test-engineer/CURRENT.md` | Live Senior Test Engineer priorities | senior-test-engineer | active | 2026-04-22 | `agents/senior-test-engineer.md` |
| `plans/devops/CURRENT.md` | Live DevOps priorities | devops | active | 2026-04-22 | `agents/devops.md` |
| `plans/scrum-master/CURRENT.md` | Live Scrum Master priorities | scrum-master | active | 2026-04-22 | `agents/scrum-master.md` |
| `plans/code-reviewer/CURRENT.md` | Live Code Reviewer priorities | code-reviewer | active | 2026-04-22 | `agents/code-reviewer.md` |
| `plans/handyman/CURRENT.md` | Live Handyman priorities | handyman | active | 2026-04-22 | `agents/handyman.md` |
| `plans/onboarder/CURRENT.md` | Live Onboarder priorities | onboarder | active | 2026-04-22 | `agents/onboarder.md` |

## Skills

| Path | Summary | Owner | Status | Updated | See also |
|------|---------|-------|--------|---------|----------|
| `skills/karpathy-guidelines/SKILL.md` | General anti-overengineering and surgical-change guidance | architect | active | 2026-04-21 | `AGENT.md` |
| `skills/retrieve-plan/SKILL.md` | Role-first plan retrieval workflow | architect | active | 2026-04-22 | `plans/README.md` |
| `skills/update-plan/SKILL.md` | Role-first plan update and archive workflow | scrum-master | active | 2026-04-22 | `plans/README.md` |
| `skills/parallel-worktree-development/SKILL.md` | Parallel GitHub and worktree workflow for independent issues | architect | active | 2026-04-22 | `AGENT.md` |
| `skills/onboarding-new-agent/SKILL.md` | Add new agent roles safely and consistently | onboarder | active | 2026-04-22 | `agents/README.md` |
| `skills/documenting-changes/SKILL.md` | Keep docs and index aligned with repository changes | architect | active | 2026-04-22 | `docs/DOC_TEMPLATE.md` |
| `skills/selecting-model-tier/SKILL.md` | Choose quality, balanced, or cheap model tiers by blast radius and cost | architect | active | 2026-04-22 | `agents/README.md` |
| `skills/github-coordination/SKILL.md` | Coordinate issues, labels, draft PRs, and blocked work | scrum-master | active | 2026-04-22 | `AGENT.md` |

## Legacy Documentation

No legacy implementation docs are included in this baseline snapshot.

If old documents are restored later, they must be added here as `legacy-review-pending` before agents may treat them as historical context.
