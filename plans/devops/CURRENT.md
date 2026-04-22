---
status: active
owner: devops
updated: 2026-04-22
summary: Live plan for the DevOps role.
see_also:
  - AGENT.md
  - PLAN.md
  - .claude/agents/devops.md
---

# DevOps Current Plan

**Last updated:** 2026-04-22

## Current Focus

Implement the next bootstrap layer now that the repository has a worktree-capable baseline.

## Active Checklist

- [x] ~~Create the first baseline commit for the repository~~
- [ ] Implement the `start run` cross-platform script contract
- [ ] Add Aspire AppHost orchestration for .NET services, Next.js, and infra containers
- [ ] Establish GitHub Actions and labels for autonomous coordination

## Blockers

- None

## Resume From Here

- Implement the script contract documented in `scripts/README.md`, then wire Aspire AppHost to own the full local graph

## References

- `scripts/README.md`
- `PLAN.md`

## Archive

- None yet
