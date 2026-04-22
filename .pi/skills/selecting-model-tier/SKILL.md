---
name: selecting-model-tier
description: Use when assigning or reviewing model tiers for agent roles and the tradeoff between reasoning quality, speed, cost, and blast radius must be explicit.
---

# Selecting Model Tier

## Overview

Choose the cheapest model tier that safely fits the role.

**Core principle:** higher blast radius means higher reasoning tier.

## Tiers

- `quality`: for architecture, critical implementation, testing, and review
- `balanced`: for routine engineering and automation with moderate risk
- `cheap`: for trivial, low-risk, high-volume coordination or cleanup

## Selection Rules

Pick `quality` when the role:

- makes architecture decisions
- writes core logic
- owns regression detection
- reviews high-impact changes

Pick `balanced` when the role:

- handles operational automation
- assembles governance artifacts
- works on medium-risk procedural tasks

Pick `cheap` when the role:

- handles trivial fixes
- performs lightweight coordination
- has low blast radius and clear escalation points

## Common Mistakes

- using a cheap tier for review of risky changes
- using a high-cost tier for trivial cleanup that the Handyman could do
- failing to revisit the tier when a role's scope grows
