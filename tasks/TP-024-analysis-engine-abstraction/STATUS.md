# TP-024: Add provider-neutral analysis engine abstraction and API contract — Status

**Current Step:** Step 0: Preflight
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-29
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied
- [x] Absence of current analysis/LEAN project confirmed
- [x] Normalized real market-data bars available through provider contracts

---

### Step 1: Create the analysis module contracts
**Status:** ⬜ Not Started

- [ ] Analysis project added to solution
- [ ] Provider-neutral engine/request/result contracts defined
- [ ] Market-data inputs use ATrade normalized bars/symbols
- [ ] Results include source/engine metadata
- [ ] No-configured-engine behavior added
- [ ] Targeted Analysis tests/build pass

---

### Step 2: Add analysis API contracts without LEAN runtime coupling
**Status:** ⬜ Not Started

- [ ] Analysis module registered in API
- [ ] Engine discovery/run endpoints added
- [ ] Default not-configured response added
- [ ] API/core contracts have no LEAN references
- [ ] Existing API behavior preserved

---

### Step 3: Add analysis contract verification
**Status:** ⬜ Not Started

- [ ] Analysis contract shell test added
- [ ] Project/solution/contracts verified
- [ ] API no-engine behavior verified
- [ ] No LEAN reference in API/core contracts verified
- [ ] Targeted analysis contract tests pass

---

### Step 4: Document the analysis engine seam
**Status:** ⬜ Not Started

- [ ] Analysis engine architecture doc created and indexed
- [ ] Provider abstractions doc cross-linked
- [ ] Paper-trading workspace LEAN seam updated
- [ ] Modules doc updated for `ATrade.Analysis`
- [ ] README reviewed and updated if stale

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Docker/iBeam-dependent runtime tests pass or cleanly skip
- [ ] All failures fixed
- [ ] Solution build passes

---

### Step 6: Documentation & Delivery
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
| 2026-04-29 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-29 22:46 | Task started | Runtime V2 lane-runner execution |
| 2026-04-29 22:46 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
