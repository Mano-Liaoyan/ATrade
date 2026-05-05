# TP-050: Complete terminal cutover, cleanup, and verification — Status

**Current Step:** Step 1: Audit active frontend routes and legacy leftovers
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-05
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied

---

### Step 1: Audit active frontend routes and legacy leftovers
**Status:** 🟨 In Progress

> ⚠️ Hydrate: Expand after reading the completed TP-047 through TP-049 implementation state.

- [ ] Verify active routes render only through the new terminal frame
- [ ] Delete obsolete legacy rendering components/CSS no longer imported
- [ ] Remove stale old copy/test markers from active frontend code/tests
- [ ] Add cutover assertions for no old-shell imports/copy and terminal markers present

---

### Step 2: Verify full functional replacement behavior
**Status:** ⬜ Not Started

- [ ] Verify all supported commands open/focus correct terminal modules
- [ ] Verify current workflows remain reachable in terminal UI
- [ ] Verify future modules are visible-disabled with no fake data/order controls
- [ ] Verify resizable layout persistence and responsive fallback

---

### Step 3: Enforce clean-room, safety, and browser-boundary guardrails
**Status:** ⬜ Not Started

- [ ] Assert no copied Fincept/Bloomberg active assets/branding references
- [ ] Assert no order-entry/live/simulated-submit UI or direct provider/database access
- [ ] Verify frontend uses ATrade.Api clients for data/provider/analysis behavior
- [ ] Verify no secrets/account identifiers/tokens/session cookies are introduced

---

### Step 4: Update docs, plan, and verification inventory
**Status:** ⬜ Not Started

- [ ] Update paper-trading workspace architecture for current terminal UI
- [ ] Update modules doc for terminal ownership and retired old shell
- [ ] Update analysis docs if user-facing analysis states changed
- [ ] Update README verification list and PLAN completion/follow-up state

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Cutover validation passing
- [ ] All terminal frontend validations passing
- [ ] Existing frontend validations passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

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
| 2026-05-04 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-05 11:28 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 11:28 | Step 0 started | Preflight |
| 2026-05-05 13:29 | Step 0 completed | Required paths and dependencies verified; frontend npm dependencies installed with npm ci |
| 2026-05-05 13:29 | Step 1 started | Audit active frontend routes and legacy leftovers |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
