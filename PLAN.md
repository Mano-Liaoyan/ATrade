---
status: active
owner: scrum-master
updated: 2026-04-22
summary: Bootstrap plan for the governance-first ATrade reboot.
see_also:
  - AGENT.md
  - scripts/README.md
  - docs/INDEX.md
---

# ATrade Bootstrap Plan

**Last updated:** 2026-04-22

## Current Focus

Extend the runnable bootstrap into real services, infrastructure resources, and coordination automation.

## Milestones

- [x] ~~Rewrite top-level repository identity around Aspire 13.2, Next.js, and autonomous agents~~
- [x] ~~Create the first baseline commit so git worktrees become available~~
- [x] ~~Bootstrap the repo-local `start run` wrapper contract and Linux-hosted AppHost path from `scripts/README.md`~~
- [ ] Verify `./start.ps1 run` and `./start.cmd run` on a Windows-hosted runtime or CI worker
- [ ] Add Aspire AppHost that orchestrates .NET services, Next.js, and infrastructure resources
- [ ] Author the first implementation-facing architecture and module docs for the new codebase
- [ ] Establish GitHub labels, issue templates, and Actions for autonomous coordination
- [ ] Scaffold the first .NET 10 backend projects and Next.js frontend

## Active Cross-Role Dependencies

- Architect must review legacy docs before they can become `active` again.
- Scrum Master must define GitHub coordination primitives before agents can run unattended at scale.

## Notes

- Only indexed `active` docs are authoritative. Legacy docs must be explicitly reintroduced and marked before use.
- The single-command local startup contract is `start run` on both Unix and Windows.
- Aspire 13.2 remains the preferred orchestrator and must manage Next.js in addition to .NET services.
- `.worktrees/` is now available for isolated parallel feature delivery.
