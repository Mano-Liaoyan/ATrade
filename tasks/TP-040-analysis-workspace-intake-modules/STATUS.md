# TP-040: Deepen analysis and workspace intake modules — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-02
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

---

### Step 1: Move analysis request construction into Analysis intake
**Status:** ⬜ Not Started

> ⚠️ Hydrate: Expand checkboxes when entering this step based on final intake interface shape and updated market-data read seam.

- [ ] Analysis intake owns request defaults, candle acquisition, identity resolution, invalid-request mapping, and engine handoff
- [ ] `ATrade.Api` analysis route simplified to HTTP binding/projection
- [ ] New Analysis request intake test file added
- [ ] Targeted Analysis and LEAN tests passing

---

### Step 2: Move watchlist request handling into Workspaces intake
**Status:** ⬜ Not Started

- [ ] Workspaces intake owns schema initialization ordering, identity use, normalization, exact unpin validation, and stable errors
- [ ] `ATrade.Api` watchlist routes simplified to HTTP binding/projection
- [ ] New Workspaces watchlist intake test file added
- [ ] Targeted Workspaces tests passing

---

### Step 3: Keep HTTP behavior stable and simplify route code
**Status:** ⬜ Not Started

- [ ] Existing analysis/watchlist paths, status codes, and payload fields verified compatible
- [ ] Provider/analysis/storage error mapping remains stable and explicit
- [ ] Temporary local workspace identity seam remains contained and documented
- [ ] Targeted AppHost analysis/watchlist scripts passing

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Integration tests passing or cleanly skipped where applicable
- [ ] All failures fixed
- [ ] Build passes

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
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
| 2026-05-02 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
