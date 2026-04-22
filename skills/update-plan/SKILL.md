---
name: update-plan
description: Use when an agent completes, pauses, or re-scopes work and must record progress in its role plan, archive long plans, and update shared milestones without losing resume context.
---

# Update Plan

## Overview

After work changes state, update the right plan files.

**Core principle:** update the role plan first, then update `PLAN.md` only if the change affects a shared milestone.

## When to Use

- After completing a task
- After hitting a blocker
- After asking for human approval
- After resuming paused work and changing the next step
- After adding or obsoleting documentation

## Files to Update

- Always: `plans/<role>/CURRENT.md`
- Sometimes: `PLAN.md`
- If docs changed: `docs/INDEX.md`

## Required Updates In `plans/<role>/CURRENT.md`

Record:

1. What just changed
2. What remains next
3. What blocks progress, if anything
4. Where the active branch, issue, or draft PR lives
5. What verification was run for this task type

## Completion Format

Use checkbox + strikethrough for fully completed checklist items.

```markdown
- [ ] Implement `start run` script shim
- [x] ~~Bootstrap repo-level agent governance docs~~
```

## Blocked Format

If human approval or another dependency blocks the work, add a short resume note.

```markdown
## Blockers

- Waiting on human approval for issue `#42`: approve Aspire AppHost resource layout

## Resume From Here

- After approval, update `src/ATrade.AppHost/Program.cs` and reopen draft PR `#108`
```

## Root Plan Updates

Update `PLAN.md` only when a shared milestone changes.

Examples:

- A new repo-wide phase starts
- A milestone finishes
- A cross-role blocker appears or clears
- The single-command startup contract changes

## Archival Rule

If `plans/<role>/CURRENT.md` approaches 150 lines:

1. Move the old contents to `plans/<role>/archive/YYYY-MM-DD-<slug>.md`
2. Create a fresh `CURRENT.md`
3. Carry forward only the still-active items and the latest resume note
4. Add a link to the archive file in the new `CURRENT.md`

## Documentation Updates

If the task added or changed a durable artifact:

- add or update the corresponding document
- update `docs/INDEX.md`
- mark stale docs `obsolete` or `legacy-review-pending`

Do not leave documentation drift for later.

## Update the Timestamp

Always update the `Last updated` line in every plan you touched.

```markdown
**Last updated:** YYYY-MM-DD
```

## Verification Before Updating

Match verification to the task type before marking it done.

For code changes:

1. Relevant tests passed
2. Build or lint passed where applicable
3. The behavior was manually or automatically verified

For documentation-only changes:

1. Links and file paths were checked
2. `docs/INDEX.md` matches the files that now exist
3. Obsolete or pending docs were marked correctly

If verification is incomplete, record that explicitly and leave the item unchecked.

## Quick Reference

| Situation | Update |
|-----------|--------|
| Finished task | check + strike through in role plan |
| Waiting for approval | blockers + resume note in role plan |
| Shared milestone changed | update `PLAN.md` |
| Plan nearing 150 lines | archive and roll forward |
| Durable docs changed | update `docs/INDEX.md` |

## Anti-Patterns

| Don't | Do instead |
|-------|------------|
| Update only `PLAN.md` | Update the role plan first |
| Leave blocked work in memory | Write a resume note |
| Let `CURRENT.md` grow forever | Archive near 150 lines |
| Treat docs as optional | Update docs and index in the same change |
| Mark tasks done without evidence | Record the verification you actually ran |
