---
status: active
owner: devops
updated: 2026-04-23
summary: Defines which Taskplane and Pi files are committed project config versus local runtime artifacts that must stay ignored.
see_also:
  - ../INDEX.md
  - ../../README.md
  - ../../AGENTS.md
---

# Taskplane Runtime Artifacts

ATrade keeps **Taskplane/Pi project configuration** in version control, but it
must not commit **local runtime state**, diagnostics, or per-operator UI
preferences.

This distinction matters because Taskplane writes a large amount of execution
state under `.pi/` and `tasks/` while batches run. Those files are useful for a
single operator during execution or failure recovery, but they are not durable
repository truth.

## Commit These Files

These files are part of the repository contract and should remain tracked:

- `.pi/agents/` — role and execution-agent prompts
- `.pi/skills/` — repository workflow skills
- `.pi/taskplane-config.json` — project-specific Taskplane execution config
- `tasks/CONTEXT.md` — task area context and next ID counter
- `tasks/<TASK-ID>-<slug>/PROMPT.md` — task packets
- `tasks/<TASK-ID>-<slug>/STATUS.md` — durable execution/resume state for a task
- `tasks/<TASK-ID>-<slug>/.DONE` — durable completion marker when present

## Ignore These Files

These files are local runtime artifacts or caches and should stay untracked:

- `.pi/batch-state.json` and `.pi/batch-history.json`
- `.pi/taskplane.json`
- `.pi/dashboard-preferences.json`
- `.pi/diagnostics/`
- `.pi/mailbox/`
- `.pi/runtime/`
- `.pi/supervisor/`
- `.pi/telemetry/`
- `.pi/verification/`
- `tasks/dependencies.json`

## Why They Stay Untracked

### `.pi/` runtime directories

The runtime, mailbox, supervisor, telemetry, verification, and diagnostics
folders are execution byproducts. They can be useful for live supervision or
post-failure inspection, but they are machine-local and batch-local.
Committing them would add noise, stale recovery data, and timestamp churn.

### `.pi/taskplane.json`

This file is Taskplane runtime metadata created by the tool itself. It records
installation and migration state, not project behavior.

### `.pi/dashboard-preferences.json`

This file stores local dashboard/UI preferences for the current operator. It is
not repository policy.

### `tasks/dependencies.json`

This file is a generated dependency cache used to speed task discovery. It is
not the source of truth for task intent; task dependencies belong in each
packet's `PROMPT.md`.

## Cleanup Guidance

When a batch is complete and no recovery work is needed, it is safe to remove
local runtime artifacts covered by the ignore rules above. Keep the committed
Taskplane config and task packets; discard the transient execution traces.
