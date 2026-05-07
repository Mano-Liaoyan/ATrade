# TP-067: Purpose-built Home, Search, and Watchlist modules — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-07
**Review Level:** 1
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

---

### Step 1: Split page composition by purpose
**Status:** ⬜ Not Started

- [ ] Extract or restructure Home/Search/Watchlist module rendering into distinct compositions
- [ ] Keep shared workflow/table/filter/detail primitives reusable underneath where helpful
- [ ] Preserve exact identity, bounded search, backend watchlist authority, unavailable states, and no-order guardrails

---

### Step 2: Implement a dashboard-focused Home module
**Status:** ⬜ Not Started

- [ ] Render Home as provider/API status, paper safety, quick actions, and compact market/watchlist context
- [ ] Use compact truthful previews instead of a full generic market monitor clone
- [ ] Keep Home copy/headings distinct from Search and Watchlist

---

### Step 3: Implement search-first and watchlist-first modules
**Status:** ⬜ Not Started

- [ ] Render Search as prominent bounded stock search with ranked results, filters, and actions
- [ ] Render Watchlist as saved-stocks-first with backend pins, manage/remove, identity metadata, and workflow actions
- [ ] Avoid duplicated titles/descriptions/default layout between Home, Search, and Watchlist

---

### Step 4: Add purpose-built module validation
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/frontend-purpose-built-home-search-watchlist-tests.sh`
- [ ] Update existing shared tests only where strings or structure changed
- [ ] Keep validation provider/runtime independent

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Purpose-built module validation passing
- [ ] Terminal market monitor validation passing
- [ ] Symbol search exploration validation passing
- [ ] Trading workspace validation passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 6: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] Distinct Home/Search/Watchlist docs updated
- [ ] README/PLAN verification/current-surface text updated if affected
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged

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
| 2026-05-07 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
