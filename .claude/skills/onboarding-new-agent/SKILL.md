---
name: onboarding-new-agent
description: Use when repeated work no longer fits existing roles and the repository needs a new agent charter, plan scaffold, discoverability updates, and overlap checks.
---

# Onboarding New Agent

## Overview

Add a new role only when repeated work clearly does not fit an existing role.

**Core principle:** add the smallest new role that closes a recurring gap without creating overlap chaos.

## When to Use

- repeated work is being misrouted between roles
- an existing role has become too broad
- a new recurring responsibility needs its own plan and model tier

Do not use this skill for one-off work. Use an issue or an existing role instead.

## Workflow

1. Confirm the gap is recurring, not incidental.
2. Check whether updating an existing role would solve it more simply.
3. Create `.claude/agents/<role>.md`.
4. Create `plans/<role>/CURRENT.md` from `plans/TEMPLATE.md`.
5. Create `plans/<role>/archive/`.
6. Update `.claude/agents/README.md`.
7. Update `docs/INDEX.md`.
8. Add supporting skills only if the role needs reusable guidance not already covered.

## Required Outputs

- one new role charter
- one new live plan
- one archive directory
- one docs index update

## Common Mistakes

- creating a role for a single temporary task
- cloning an existing role under a new name without a clearer boundary
- forgetting discoverability updates in `docs/INDEX.md`
- adding a role without defining its preferred model tier
