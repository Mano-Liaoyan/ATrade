# TP-007: Reconcile planning and docs with the actual repo state — Status

**Current Step:** Step 0: Preflight
**Status:** ⏳ Ready
**Last Updated:** 2026-04-23
**Review Level:** 1
**Review Counter:** 0
**Iteration:** 0
**Size:** S

---

### Step 0: Preflight
**Status:** ⬜ Not started

- [ ] Read the active docs and planning files
- [ ] Identify stale status claims
- [ ] Identify stale `AGENT.md` references

---

### Step 1: Reconcile plan and status language
**Status:** ⬜ Not started

- [ ] Update `PLAN.md` milestone text where completed work is still shown as open
- [ ] Update `README.md` and `scripts/README.md` current-status wording where needed
- [ ] Keep complete versus scaffolded language precise

---

### Step 2: Fix doc-link and read-order drift
**Status:** ⬜ Not started

- [ ] Replace stale `AGENT.md` references with `AGENTS.md`
- [ ] Ensure read-order and `see_also` pointers resolve
- [ ] Avoid unintended authority/status changes

---

### Step 3: Refresh task-area context
**Status:** ⬜ Not started

- [ ] Update `tasks/CONTEXT.md` next task ID and future-work notes
- [ ] Keep context aligned with roadmap and active docs

---

### Step 4: Verification
**Status:** ⬜ Not started

- [ ] `grep -RIn "AGENT\\.md" README.md PLAN.md docs scripts tasks || true`
- [ ] Confirm remaining open `PLAN.md` items are truly pending
- [ ] Confirm the change stayed documentation-only

---

### Step 5: Delivery
**Status:** ⬜ Not started

- [ ] Commit with conventions

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-23 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None*

---

## Notes

*Goal: make the active docs and plan trustworthy again before the next implementation batch starts.*
