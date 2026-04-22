---
name: documenting-changes
description: Use when a durable repository artifact is added or changed and the corresponding docs, frontmatter, and documentation index must stay synchronized.
---

# Documenting Changes

## Overview

Documentation changes ship with the repository change, not later.

**Core principle:** if another agent will need the information later, document it now and index it now.

## When to Use

- adding a new durable file, module, service, script contract, or workflow
- materially changing how something works or where it lives
- obsoleting a document that agents might still find

## Workflow

1. Decide whether the change needs a new doc or an update to an existing doc.
2. Ensure the doc has frontmatter matching `docs/DOC_TEMPLATE.md`.
3. Update the content summary and references.
4. Update `docs/INDEX.md` in the same change.
5. Mark stale docs `obsolete` or `legacy-review-pending`.

## Quick Reference

| Change | Minimum docs action |
|--------|---------------------|
| New durable artifact | new doc or indexed entry |
| Behavior change | update relevant doc + index |
| Obsoleted workflow | mark stale doc and stop referencing it |

## Common Mistakes

- updating code without updating `docs/INDEX.md`
- silently leaving stale docs discoverable
- creating docs without frontmatter
