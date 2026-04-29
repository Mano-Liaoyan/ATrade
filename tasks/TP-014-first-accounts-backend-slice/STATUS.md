# TP-014: Add the first read-only Accounts backend slice — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-29
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] `ATrade.Accounts` marker-only state confirmed
- [ ] `ATrade.Api` health-only state confirmed

---

### Step 1: Implement the read-only Accounts module behavior
**Status:** ⬜ Not Started

- [ ] Add deterministic Accounts overview response types
- [ ] Add bootstrap-safe Accounts overview service/provider
- [ ] Add minimal Accounts module DI registration
- [ ] Preserve a compile-time module anchor if useful
- [ ] Keep persistence, broker/data clients, and fake trading data out of scope
- [ ] Targeted Accounts project build passes

---

### Step 2: Expose the Accounts overview through the API
**Status:** ⬜ Not Started

- [ ] Add API project reference to `ATrade.Accounts`
- [ ] Register Accounts module during API startup
- [ ] Map `GET /api/accounts/overview`
- [ ] Preserve `GET /health`
- [ ] Targeted API smoke check passes

---

### Step 3: Add feature-slice verification
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/accounts-feature-bootstrap-tests.sh`
- [ ] Verify API references Accounts and solution builds
- [ ] Assert `/health` returns `ok`
- [ ] Assert `/api/accounts/overview` returns expected JSON markers
- [ ] Assert endpoint has no external service requirement
- [ ] Targeted feature test passes

---

### Step 4: Update docs and milestone state
**Status:** ⬜ Not Started

- [ ] `docs/architecture/modules.md` current-state notes updated
- [ ] `docs/architecture/overview.md` current backend slice updated
- [ ] `README.md` current status updated if stale
- [ ] `PLAN.md` backend-feature milestone updated if implementation satisfies it
- [ ] `scripts/README.md` checked and updated if affected

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Runtime infrastructure test passes or cleanly skips when no engine is available
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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
