---
status: active
owner: onboarder
updated: 2026-04-22
summary: Index of agent roles and the conventions for adding a new role.
see_also:
  - AGENT.md
  - .claude/skills/onboarding-new-agent/SKILL.md
  - plans/README.md
---

# Agent Roles

This directory defines the autonomous workforce for ATrade.

Each role file describes:

- mission
- preferred model tier
- primary skills
- inputs and outputs
- escalation rules
- parallelism notes

## Default Roles

- `architect.md`
- `senior-engineer.md`
- `senior-test-engineer.md`
- `devops.md`
- `scrum-master.md`
- `code-reviewer.md`
- `handyman.md`
- `onboarder.md`

## Adding A New Role

Use `.claude/skills/onboarding-new-agent/SKILL.md`.

Every new role must include:

1. `.claude/agents/<role>.md`
2. `plans/<role>/CURRENT.md`
3. `plans/<role>/archive/`
4. updates to `docs/INDEX.md`

New roles are added only when recurring work does not fit an existing role cleanly.
