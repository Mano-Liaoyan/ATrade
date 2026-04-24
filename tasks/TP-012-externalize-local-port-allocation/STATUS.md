# TP-012: Externalize local port allocation into a repo `.env` contract — Status

**Current Step:** Step 0: Preflight
**Status:** ⏳ Not started
**Last Updated:** 2026-04-24
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** M

---

### Step 0: Preflight
**Status:** ⏳ Not started

- [ ] Inventory current port literals and classify them correctly
- [ ] Confirm whether a repo `.env` contract already exists
- [ ] Confirm how AppHost and tests currently obtain their ports

---

### Step 1: Define the `.env` contract
**Status:** ⏳ Not started

- [ ] Choose the committed template/local-file shape
- [ ] Define clear variables for developer-controlled ports
- [ ] Preserve intentionally ephemeral internal ports where appropriate
- [ ] Document fallback behavior when `.env` is absent

---

### Step 2: Wire AppHost and startup paths to the env contract
**Status:** ⏳ Not started

- [ ] Update AppHost/startup code to read the env-driven port values
- [ ] Centralize the relevant frontend/api/infra runtime path configuration
- [ ] Avoid regressing TP-010 / TP-011 fixes

---

### Step 3: Wire tests to the same source of truth
**Status:** ⏳ Not started

- [ ] Update affected test harnesses to use the shared env contract
- [ ] Remove stale duplicated port assumptions where appropriate
- [ ] Keep CI deterministic

---

### Step 4: Verification
**Status:** ⏳ Not started

- [ ] Prove the `.env` contract is actually consumed
- [ ] Verify direct API/frontend startup still works
- [ ] Verify AppHost manifest/runtime checks still pass
- [ ] Verify at least one changed env port propagates correctly

---

### Step 5: Documentation
**Status:** ⏳ Not started

- [ ] Update `scripts/README.md`
- [ ] Update `README.md` / `PLAN.md` only if wording would otherwise be stale

---

### Step 6: Final verification
**Status:** ⏳ Not started

- [ ] Run the affected tests
- [ ] Confirm the repo still boots with defaults
- [ ] Confirm the env contract is the single source of truth for developer-controlled local ports

---

### Step 7: Delivery
**Status:** ⏳ Not started

- [ ] Commit with conventions

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
| 2026-04-24 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None yet*

---

## Notes

*Goal: make local port allocation env-driven and centralized without freezing ports that should remain dynamic by design.*
