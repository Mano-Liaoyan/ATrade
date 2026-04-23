# TP-007: Reconcile planning and docs with the actual repo state — Status

**Current Step:** Step 2: Fix doc-link and read-order drift
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-23
**Review Level:** 1
**Review Counter:** 0
**Iteration:** 1
**Size:** S

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Read the active docs and planning files
- [x] Identify stale status claims
- [x] Identify stale `AGENT.md` references

---

### Step 1: Reconcile plan and status language
**Status:** ✅ Complete

- [x] Update `PLAN.md` milestone text where completed work is still shown as open
- [x] Update `README.md` and `scripts/README.md` current-status wording where needed
- [x] Keep complete versus scaffolded language precise

---

### Step 2: Fix doc-link and read-order drift
**Status:** 🟨 In Progress

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
| `PLAN.md` still shows AppHost, architecture docs, GitHub coordination, and first backend/frontend scaffolds as open even though those slices now exist. | Reconcile milestone status language in Step 1. | `PLAN.md`; verified against `src/`, `frontend/`, `docs/architecture/*`, `.github/*`, and current README/scripts docs |
| `README.md` and `tasks/CONTEXT.md` still describe `src/` and `frontend/` as aspirational despite the current AppHost + `ATrade.Api` + Next.js bootstrap slice. | Update current-state wording in Steps 1 and 3. | `README.md`, `tasks/CONTEXT.md` |
| Multiple active docs still point to `AGENT.md` even though the repository contract file is `AGENTS.md`. | Replace stale references in Step 2 without changing document status/authority. | `README.md`, `PLAN.md`, `scripts/README.md`, `plans/**/*.md`, `.pi/agents/README.md` |
| `PLAN.md` now distinguishes completed bootstrap work from the still-open AppHost-infra / feature-module follow-up milestones. | Verified and checked off in Step 1. | `PLAN.md` |
| `README.md` and `scripts/README.md` now describe the current runnable slice as real-but-limited rather than implying the repo is only conceptual. | Verified and checked off in Step 1. | `README.md`, `scripts/README.md` |
| Status language now consistently distinguishes the current AppHost + API + Next.js bootstrap from still-pending workers, infra resources, and deeper feature modules. | Verified and checked off in Step 1. | `PLAN.md`, `README.md`, `scripts/README.md` |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-23 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-23 05:57 | Task started | Runtime V2 lane-runner execution |
| 2026-04-23 05:57 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Goal: make the active docs and plan trustworthy again before the next implementation batch starts.*
