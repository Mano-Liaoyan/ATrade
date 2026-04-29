# TP-020: Persist pinned stock watchlists in Postgres — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-29
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Current localStorage-authoritative watchlist behavior confirmed
- [ ] API Postgres wiring confirmed

---

### Step 1: Add the workspace persistence module and schema
**Status:** ⬜ Not Started

- [ ] Workspaces project added to solution and referenced by API
- [ ] Postgres watchlist repository and schema initializer added
- [ ] Schema supports future provider/IBKR symbol metadata
- [ ] Temporary local user/workspace seam documented in code
- [ ] Targeted Workspaces tests/build pass

---

### Step 2: Expose backend watchlist API endpoints
**Status:** ⬜ Not Started

- [ ] Workspaces module registered in API
- [ ] Read/write/pin/unpin watchlist endpoints mapped
- [ ] Symbol validation and normalization added
- [ ] Stable error handling for invalid requests/database unavailability added
- [ ] Existing API endpoints preserved

---

### Step 3: Move the frontend watchlist to the backend source of truth
**Status:** ⬜ Not Started

- [ ] Frontend watchlist API client added
- [ ] Pin/unpin UI calls backend API
- [ ] localStorage demoted to cache or one-time migration source
- [ ] Backend unavailable/error states handled honestly
- [ ] Frontend build passes

---

### Step 4: Add restart-persistence verification
**Status:** ⬜ Not Started

- [ ] Postgres persistence shell test added
- [ ] API restart persistence verified against same database
- [ ] Duplicate and invalid-symbol behavior verified
- [ ] Frontend trading workspace tests updated for backend-owned pins
- [ ] Targeted persistence/frontend tests pass

---

### Step 5: Update docs for backend-owned preferences
**Status:** ⬜ Not Started

- [ ] Paper-trading workspace doc updated
- [ ] Modules doc updated for Workspaces/API/frontend ownership
- [ ] Overview/README reviewed and updated if stale

---

### Step 6: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Docker-dependent Postgres/runtime tests pass or cleanly skip
- [ ] All failures fixed
- [ ] Frontend build passes
- [ ] Solution build passes

---

### Step 7: Documentation & Delivery
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
