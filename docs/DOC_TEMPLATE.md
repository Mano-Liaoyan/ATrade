---
status: active
owner: architect
updated: 2026-04-22
summary: Template for repository documents that agents may discover and trust.
see_also:
  - docs/INDEX.md
  - AGENT.md
---

# Document Template

Use this shape for durable repository documentation.

```yaml
---
status: active
owner: <role>
updated: YYYY-MM-DD
summary: One-sentence summary of what the document explains.
see_also:
  - path/or/doc.md
---
```

## Requirements

1. `status` must be one of `active`, `legacy-review-pending`, or `obsolete`.
2. `owner` should be the responsible role or team.
3. `updated` must reflect the last meaningful edit date.
4. `summary` should help agents decide whether the doc is relevant.
5. `see_also` should point to adjacent documents.

## Notes

- Documents without frontmatter are tolerated only for preserved legacy material.
- If a legacy document is still useful, rewrite it into this shape before marking it `active`.
