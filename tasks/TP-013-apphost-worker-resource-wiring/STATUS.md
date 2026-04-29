# TP-013: Wire the IBKR worker and AppHost resource consumers — Status

**Current Step:** Step 2: Add manifest verification for the new runtime graph
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
- [x] `ATrade.Ibkr.Worker` state confirmed
- [x] AppHost infrastructure consumer gap confirmed

---

### Step 1: Wire the worker and resource references in AppHost
**Status:** ✅ Complete

- [x] Add the IBKR worker project reference to AppHost
- [x] Assign named variables for managed infrastructure resources in AppHost
- [x] Add `ibkr-worker` to the AppHost graph
- [x] Reference expected infrastructure from `api` and `ibkr-worker`
- [x] Preserve frontend, port, and container-runtime safeguards
- [x] Targeted build passes

---

### Step 2: Add manifest verification for the new runtime graph
**Status:** 🟨 In Progress

- [ ] Create `tests/apphost/apphost-worker-resource-wiring-tests.sh`
- [ ] Verify manifest contains `ibkr-worker` plus the existing graph resources
- [ ] Verify manifest proves expected resource references for `api` and `ibkr-worker`
- [ ] Keep new verification engine-independent
- [ ] Targeted manifest test passes

---

### Step 3: Update docs and milestone state
**Status:** ⬜ Not Started

- [ ] `scripts/README.md` updated for worker/resource-consumer wiring
- [ ] `docs/architecture/overview.md` current-slice wording updated
- [ ] `docs/architecture/modules.md` dependency/runtime notes updated
- [ ] `PLAN.md` milestone state updated if implementation satisfies it
- [ ] `README.md` checked and updated if stale

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Runtime infrastructure test passes or cleanly skips when no engine is available
- [ ] All failures fixed
- [ ] Manifest preserves frontend local-port and infrastructure safeguards

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
| 2026-04-29 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-29 00:08 | Task started | Runtime V2 lane-runner execution |
| 2026-04-29 00:08 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
