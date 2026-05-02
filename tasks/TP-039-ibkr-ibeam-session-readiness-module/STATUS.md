# TP-039: Deepen the IBKR/iBeam session readiness module — Status

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

### Step 1: Create the shared IBKR/iBeam readiness interface
**Status:** ⬜ Not Started

> ⚠️ Hydrate: Expand checkboxes when entering this step based on final readiness result shape and existing tests.

- [ ] Shared readiness module evaluates paper guard, local runtime contract, auth status, transport, and safe diagnostics
- [ ] New readiness matrix test file added
- [ ] Existing provider-neutral broker status values and safe messages preserved
- [ ] Targeted broker tests passing

---

### Step 2: Adapt broker, market-data, and worker callers
**Status:** ⬜ Not Started

- [ ] Broker status projects shared readiness result
- [ ] Market-data status/request guards project shared readiness result
- [ ] Worker monitoring uses readiness module without duplicating tree
- [ ] Targeted broker, worker, and market-data tests passing

---

### Step 3: Preserve transport, auth, and redaction safety
**Status:** ⬜ Not Started

- [ ] Loopback HTTPS iBeam certificate handling remains narrow
- [ ] Client Portal user-agent and scanner content-length behavior remain intact
- [ ] Diagnostics and logs remain secret/account safe
- [ ] Targeted iBeam runtime and paper-safety scripts passing

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
