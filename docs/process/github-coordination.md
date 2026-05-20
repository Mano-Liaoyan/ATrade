---
status: active
owner: maintainer
updated: 2026-05-21
summary: Lightweight GitHub coordination contract for repository work.
see_also:
  - ../../README.md
  - ../../PLAN.md
  - ../INDEX.md
---

# GitHub Coordination

ATrade coordinates implementation through GitHub Issues, pull requests, active
repository docs, and local verification commands.

## Source Of Truth

| Need | Source |
|------|--------|
| Current implementation direction | `PLAN.md` |
| Human-facing repository overview | `README.md` |
| Issue and PR state | GitHub Issues and pull requests in `Mano-Liaoyan/ATrade` |
| Active documentation | `docs/INDEX.md` |

## Work Flow

1. Use a GitHub issue or PR for durable work state when the work needs tracking.
2. Keep acceptance criteria, blockers, and verification notes in the issue or PR.
3. Use `docs/INDEX.md` to find active docs for the area being changed.
4. Update active docs in the same change as durable runtime, architecture, or workflow changes.
5. Run the relevant local verification before claiming completion.

## GitHub Labels

The default engineering-skill triage labels are configured in
`docs/agents/triage-labels.md`:

- `needs-triage`
- `needs-info`
- `ready-for-agent`
- `ready-for-human`
- `wontfix`

Additional workflow labels may be useful for human-visible issue/PR state:

- `agent:ready`
- `agent:in-progress`
- `agent:blocked`
- `agent:needs-human`
- `agent:review`
- `agent:merged`
- `agent:docs-required`

## Blocked Work

Blocked work must be resumable from repository files and GitHub discussion, not
chat history.

When blocked:

1. Record the blocker in the related issue or PR.
2. Add a concise unblock note with the decision or input needed.
3. Mark the issue or PR with `agent:blocked` or `agent:needs-human` when those labels are in use.
4. Continue with another ready issue when possible.

When unblocked, update the issue or PR, remove or adjust the blocker label, and
resume from the recorded acceptance criteria.

## Documentation

Durable runtime, architecture, or workflow changes must update active docs in
the same change. Use `docs/INDEX.md` to find active docs and add new docs to the
index when introduced.
