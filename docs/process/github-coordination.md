---
status: active
owner: maintainer
updated: 2026-04-29
summary: Lightweight GitHub and Taskplane coordination contract after removal of the old role-based workforce.
see_also:
  - ../../README.md
  - ../../PLAN.md
  - ../../tasks/CONTEXT.md
  - ../INDEX.md
---

# GitHub And Taskplane Coordination

ATrade now coordinates implementation through Taskplane task packets under
`tasks/`. The old role-based workforce labels and per-role plans are no longer
part of the active operating model.

## Source Of Truth

| Need | Source |
|------|--------|
| Current active work | `PLAN.md` |
| Task area state and next ID | `tasks/CONTEXT.md` |
| Executable task instructions | `tasks/<TASK-ID>-<slug>/PROMPT.md` |
| Task execution state | `tasks/<TASK-ID>-<slug>/STATUS.md` |
| Finished task history | `tasks/archive/<TASK-ID>-<slug>/` |
| Active documentation | `docs/INDEX.md` |

## Task Flow

1. Create or update a Taskplane packet for implementation work.
2. Keep dependencies in the packet's `## Dependencies` section.
3. Keep file scope in the packet's `## File Scope` section so the orchestrator can avoid conflicts.
4. Run work through `/orch <path/to/PROMPT.md>` or `/orch all`.
5. When a task completes, leave its `.DONE` marker in place and move the whole task directory to `tasks/archive/`.
6. Update `PLAN.md` and `tasks/CONTEXT.md` when the active queue changes.

## GitHub Labels

GitHub labels may still be useful for human-visible issue/PR state, but they are
not a replacement for Taskplane packet state.

Recommended workflow labels:

- `agent:ready`
- `agent:in-progress`
- `agent:blocked`
- `agent:needs-human`
- `agent:review`
- `agent:merged`
- `agent:docs-required`

The old `role:*` label taxonomy is deprecated with the removal of the
role-based workforce files.

## Blocked Work

Blocked work must be resumable from repository files, not chat history.

When blocked:

1. Record the blocker in the task's `STATUS.md`.
2. Add a concise unblock note to the related issue or PR if one exists.
3. Mark the issue or PR with `agent:blocked` or `agent:needs-human` if GitHub is in use.
4. Continue with another ready task when possible.

When unblocked, update `STATUS.md`, remove/adjust the GitHub blocker label, and
resume from the task packet.

## Documentation

Durable runtime, architecture, or workflow changes must update active docs in
the same change. Use `docs/INDEX.md` to find active docs and add new docs to the
index when introduced.
