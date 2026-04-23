---
status: active
owner: scrum-master
updated: 2026-04-23
summary: Bootstrap plan for the governance-first ATrade reboot.
see_also:
  - AGENT.md
  - scripts/README.md
  - docs/INDEX.md
---

# ATrade Bootstrap Plan

**Last updated:** 2026-04-23

## Current Focus

Extend the runnable bootstrap into deeper backend/frontend slices, worker shells, and AppHost-managed infrastructure resources.

## Milestones

- [x] ~~Rewrite top-level repository identity around Aspire 13.2, Next.js, and autonomous agents~~
- [x] ~~Create the first baseline commit so git worktrees become available~~
- [x] ~~Bootstrap the repo-local `start run` wrapper contract and Linux-hosted AppHost path from `scripts/README.md`~~
- [x] ~~Verify `./start.ps1 run` and `./start.cmd run` on a Windows-hosted runtime or CI worker~~
- [x] ~~Bootstrap the first Aspire AppHost graph for `ATrade.Api` plus the Next.js home page~~
- [x] ~~Author the first implementation-facing architecture and module docs for the new codebase~~
- [x] ~~Establish GitHub labels, issue templates, and Actions for autonomous coordination~~
- [x] ~~Scaffold the first .NET 10 backend projects and Next.js frontend~~
- [ ] Extend the AppHost graph with workers and infrastructure resources
- [ ] Add the first backend feature modules and worker shells on top of the bootstrap slice

## Active Cross-Role Dependencies

- Senior Engineer and DevOps must extend the current AppHost graph with infrastructure resources and future workers without breaking the cross-platform `start run` contract.
- Architect and Scrum Master must keep the roadmap, task inventory, and active docs aligned as the first feature-module slices are staged.

## Notes

- Only indexed `active` docs are authoritative. Legacy docs must be explicitly reintroduced and marked before use.
- The single-command local startup contract is `start run` on both Unix and Windows.
- Aspire 13.2 remains the preferred orchestrator and currently manages `ATrade.Api` plus the Next.js home page; Postgres, TimescaleDB, Redis, NATS, and future workers remain later milestones.
- `.worktrees/` is now available for isolated parallel feature delivery.
