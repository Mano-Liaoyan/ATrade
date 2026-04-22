---
status: active
owner: architect
updated: 2026-04-23
summary: Documentation discovery layer for the ATrade repository; lists every tracked doc and its lifecycle status.
see_also:
  - ../README.md
  - ../AGENTS.md
  - ../PLAN.md
---

# ATrade Documentation Index

This file is the documentation discovery layer required by `AGENTS.md` →
*Documentation Contract*. Every tracked document in the repository must be
listed here with its `status`. Only documents marked `active` may be used
as implementation authority; `legacy-review-pending` and `obsolete`
documents are retained for history and must not drive implementation
decisions.

## Active Documents

| Document | Owner | Summary |
|----------|-------|---------|
| [`../README.md`](../README.md) | architect | Human-facing overview of the rebooted ATrade repository and its core operating contracts. |
| [`../AGENTS.md`](../AGENTS.md) | architect | Repository-wide operating contract for the autonomous ATrade workforce. |
| [`../PLAN.md`](../PLAN.md) | scrum-master | Bootstrap plan for the governance-first ATrade reboot. |
| [`../scripts/README.md`](../scripts/README.md) | devops | Bootstrap status and contract for the cross-platform `start run` entrypoints. |
| [`tooling/taskplane-runtime-artifacts.md`](tooling/taskplane-runtime-artifacts.md) | devops | Defines which Taskplane and Pi files are committed project config versus local runtime artifacts that must stay ignored. |
| [`architecture/overview.md`](architecture/overview.md) | architect | Target high-level architecture for the ATrade modular monolith, Aspire 13.2 orchestration, and the `start run` contract. |
| [`architecture/modules.md`](architecture/modules.md) | architect | Target module map for the ATrade modular monolith covering `src/`, `workers/`, and `frontend/` with first-phase IBKR and Polygon focus. |

## Legacy-Review-Pending Documents

*None.* Legacy docs from the pre-reboot repository were removed from the
top level and have not been reintroduced. If any are restored, they must
be indexed here with `status: legacy-review-pending` before agents may
consult them.

## Obsolete Documents

*None.*

## Conventions

- Every tracked document carries frontmatter with `status`, `owner`,
  `updated`, `summary`, and `see_also` (see `AGENTS.md` → *Documentation
  Contract*).
- Durable repository changes must include a doc update in the same
  change.
- New docs are added to the *Active Documents* table in the same PR that
  introduces them.
- Stale docs are moved to *Legacy-Review-Pending Documents* or *Obsolete
  Documents* and their frontmatter `status` updated to match.
