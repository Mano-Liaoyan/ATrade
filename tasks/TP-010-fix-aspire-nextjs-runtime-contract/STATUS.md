# TP-010: Fix the Aspire-managed Next.js runtime contract — Status

**Current Step:** Step 6: Verification
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-24
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Re-read the current AppHost frontend resource configuration
- [x] Confirm direct `frontend/` startup is clean and the defect is specific to the AppHost-managed path
- [x] Confirm there is currently no explicit Next.js config pinning Turbopack root

---

### Step 1: Fix frontend environment semantics
**Status:** ✅ Complete

- [x] Update the AppHost frontend resource so `next dev` runs with a valid Next.js `NODE_ENV`
- [x] Do not use custom environment names in `NODE_ENV`
- [x] Preserve richer app environment identity through a separate variable if needed

---

### Step 2: Fix workspace-root detection
**Status:** ✅ Complete

- [x] Add explicit Next.js config so Turbopack/workspace resolution points at `frontend/`
- [x] Make the fix durable even if an extra lockfile appears at the repo root later
- [x] Avoid relying on one-off manual cleanup

---

### Step 3: Preserve the startup contract
**Status:** ✅ Complete

- [x] Keep the frontend package scripts semantically intact unless a minimal change is required
- [x] Keep the AppHost-managed frontend resource on port 3000 with external exposure
- [x] Keep direct `cd frontend && npm run dev` working

---

### Step 4: Add verification
**Status:** ✅ Complete

- [x] Extend the frontend bootstrap test or add a dedicated runtime test
- [x] Verify direct startup still serves the home page markers
- [x] Verify the AppHost-managed frontend path no longer emits the `NODE_ENV` warning
- [x] Verify the AppHost-managed frontend path no longer emits the workspace-root warning

---

### Step 5: Update docs
**Status:** ✅ Complete

- [x] Update `scripts/README.md` if runtime semantics need to be explicit there
- [x] Update `README.md` / `PLAN.md` only if wording is now stale

---

### Step 6: Verification
**Status:** 🟨 In Progress

- [ ] `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- [ ] Run any new AppHost runtime verification added by this task
- [ ] Confirm the AppHost-managed frontend startup is warning-free for these issues

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
| 2026-04-24 08:45 | Task started | Runtime V2 lane-runner execution |
| 2026-04-24 08:45 | Step 0 started | Preflight |

---

## Blockers

*None yet*

---

## Notes

*Goal: make the AppHost-managed frontend launch behave like a correct Next.js development runtime, not a heuristic or machine-specific setup.*
*Step 1 decision: no separate frontend app-environment variable was added because nothing in the repo currently consumes a richer frontend runtime identity; the minimal durable fix is to pin AppHost-managed `NODE_ENV=development` and keep other environment semantics unchanged.*
*Step 5 decision: `README.md` and `PLAN.md` were re-checked after the runtime-contract fix and did not need wording changes because their current statements remain accurate at the existing level of abstraction.*
