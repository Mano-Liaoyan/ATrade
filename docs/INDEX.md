---
status: active
owner: maintainer
updated: 2026-05-04
summary: Documentation discovery layer for active ATrade repository docs.
see_also:
  - ../README.md
  - ../AGENTS.md
  - ../PLAN.md
---

# ATrade Documentation Index

This file is the documentation discovery layer for the repository. Only
documents listed as `active` should guide implementation work.

## Active Documents

| Document                                                                             | Owner      | Summary                                                                                                                                 |
| ------------------------------------------------------------------------------------ | ---------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| [`../README.md`](../README.md)                                                       | maintainer | Human-facing overview of the current ATrade application, run contract, and active Taskplane work queue.                                 |
| [`../AGENTS.md`](../AGENTS.md)                                                       | maintainer | Repository guidance and introduction of repo-local Pi skills.                                                                           |
| [`../PLAN.md`](../PLAN.md)                                                           | maintainer | Current implementation plan for the provider-backed ATrade paper-trading workspace upgrade.                                             |
| [`../scripts/README.md`](../scripts/README.md)                                       | maintainer | Bootstrap status and contract for the cross-platform `start run` entrypoints.                                                           |
| [`design/atrade-terminal-ui.md`](design/atrade-terminal-ui.md)                       | maintainer | Active clean-room ATrade Terminal UI design authority for the frontend reconstruction queue.                                             |
| [`tooling/taskplane-runtime-artifacts.md`](tooling/taskplane-runtime-artifacts.md)   | maintainer | Defines which Taskplane and Pi files are committed project config versus local runtime artifacts, including repo-local Pi skills.       |
| [`architecture/overview.md`](architecture/overview.md)                               | maintainer | Target high-level architecture for the ATrade modular monolith, Aspire 13.2 orchestration, and the `start run` contract.                |
| [`architecture/provider-abstractions.md`](architecture/provider-abstractions.md)       | maintainer | Provider-neutral broker and market-data contract for swapping ATrade providers without changing API or frontend payloads.               |
| [`architecture/analysis-engines.md`](architecture/analysis-engines.md)                 | maintainer | Provider-neutral analysis engine contract for backtesting, signal, and metric providers without coupling API/frontend payloads to LEAN. |
| [`architecture/modules.md`](architecture/modules.md)                                 | maintainer | Target module map for the ATrade modular monolith covering `src/`, `workers`, and `frontend` with provider-neutral broker/data seams.    |
| [`architecture/paper-trading-workspace.md`](architecture/paper-trading-workspace.md) | maintainer | Authoritative paper-trading workspace architecture and paper-only configuration contract for the staged IBKR-backed trading UI slice.   |
| [`process/github-coordination.md`](process/github-coordination.md)                   | maintainer | Lightweight GitHub and Taskplane coordination contract after removal of the old role-based workforce.                                   |

## Legacy-Review-Pending Documents

*None.*

## Obsolete Documents

*None.*

## Conventions

- Durable repository changes should update the relevant active documentation in the same change.
- New docs must be added to the active table when introduced.
- Stale docs should be moved to *Legacy-Review-Pending Documents* or *Obsolete Documents* with matching frontmatter status.
- Completed Taskplane packets live under `../tasks/archive/` and are not active implementation authority.
