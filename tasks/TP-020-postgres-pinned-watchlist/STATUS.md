# TP-020: Persist pinned stock watchlists in Postgres — Status

**Current Step:** Step 2: Expose backend watchlist API endpoints
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-29
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied
- [x] Current localStorage-authoritative watchlist behavior confirmed
- [x] API Postgres wiring confirmed

---

### Step 1: Add the workspace persistence module and schema
**Status:** ✅ Complete

- [x] Workspaces project added to solution and referenced by API
- [x] Postgres watchlist repository and schema initializer added
- [x] Schema supports future provider/IBKR symbol metadata
- [x] Temporary local user/workspace seam documented in code
- [x] Targeted Workspaces tests/build pass

---

### Step 2: Expose backend watchlist API endpoints
**Status:** 🟨 In Progress

- [x] Workspaces module registered in API
- [x] Read/write/pin/unpin watchlist endpoints mapped
- [x] Symbol validation and normalization added
- [x] Stable error handling for invalid requests/database unavailability added
- [x] Existing API endpoints preserved

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
| 2026-04-29 20:42 | Task started | Runtime V2 lane-runner execution |
| 2026-04-29 20:42 | Step 0 started | Preflight |
| 2026-04-29 22:15 | Step 0 complete | Required paths verified; TP-018/TP-019 outputs confirmed; current frontend watchlist localStorage authority and AppHost API Postgres reference confirmed. |
| 2026-04-29 22:15 | Step 1 started | Workspace persistence module and schema |
| 2026-04-29 21:34 | Task started | Runtime V2 lane-runner execution |
| 2026-04-29 22:20 | Step 1 complete | Workspaces module/schema/repository/tests added; targeted tests/build passed (17 tests). |
| 2026-04-29 22:20 | Step 2 started | Backend watchlist API endpoints. |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
