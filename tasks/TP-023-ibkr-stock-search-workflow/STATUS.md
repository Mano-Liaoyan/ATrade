# TP-023: Add IBKR stock search and pin-any-symbol workflow — Status

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
- [ ] Production mocked symbol catalog removal confirmed
- [ ] Watchlist schema provider metadata support confirmed

---

### Step 1: Add backend IBKR stock search contracts and endpoints
**Status:** ⬜ Not Started

- [ ] Provider-neutral search contract added or extended
- [ ] IBKR/iBeam search maps provider-neutral results
- [ ] Search API endpoint added with limits/errors
- [ ] Search avoids hard-coded production allowlists
- [ ] Targeted provider/API tests pass

---

### Step 2: Connect search results to persisted watchlists
**Status:** ⬜ Not Started

- [ ] Watchlist command model stores provider metadata
- [ ] Existing rows remain compatible and can be enriched
- [ ] Duplicate handling uses provider/conid when available
- [ ] Search-result pin/restart tests added
- [ ] Targeted Workspaces tests pass

---

### Step 3: Add frontend search and pin UX
**Status:** ⬜ Not Started

- [ ] `SymbolSearch` component added
- [ ] Frontend search client/types added
- [ ] Users can search, open, and pin IBKR results
- [ ] Loading/no-results/provider-error states handled
- [ ] Frontend build passes

---

### Step 4: Add IBKR stock search verification
**Status:** ⬜ Not Started

- [ ] IBKR symbol search shell test added
- [ ] No hard-coded production search allowlist verified
- [ ] Fake IBKR result mapping verified
- [ ] No-credential error behavior verified
- [ ] Frontend search controls verified

---

### Step 5: Update docs for IBKR search
**Status:** ⬜ Not Started

- [ ] Paper-trading workspace doc updated
- [ ] Modules doc updated
- [ ] Provider abstractions doc updated
- [ ] README reviewed and updated if stale

---

### Step 6: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Docker/iBeam-dependent runtime tests pass or cleanly skip
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
