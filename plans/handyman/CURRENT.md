---
status: active
owner: handyman
updated: 2026-04-23
summary: Live plan for the Handyman role.
see_also:
  - ../../AGENTS.md
  - ../../PLAN.md
  - ../../.pi/agents/handyman.md
---

# Handyman Current Plan

**Last updated:** 2026-04-23

## Current Focus

Stay available for low-risk cleanup and mechanical repository maintenance.

## Active Checklist

- [ ] Fix trivial link or formatting drift when found
- [ ] Handle tiny docs cleanups that do not need higher-tier roles
- [ ] Escalate immediately if a task grows beyond trivial scope

## Blockers

- None

## Resume From Here

- Pick issues labeled `agent:trivial` once GitHub coordination is live
- Keep trivial workspace-hygiene cleanup isolated to ignored runtime state and small doc/index updates

## Recent Progress

- Cleaned Taskplane/Pi runtime clutter from the working tree, kept `.pi/taskplane-config.json` as durable project config, and documented which `.pi/` and `tasks/` artifacts stay local-only.

## Verification

- `git status --short`
- `git check-ignore -v .pi/runtime/test .pi/taskplane.json tasks/dependencies.json`

## References

- `AGENTS.md`
- `.pi/agents/handyman.md`

## Archive

- None yet
