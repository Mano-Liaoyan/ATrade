# TP-071: Compose startup cutover for Aspire-launched app services — Status

**Current Step:** Step 6: Testing & Verification
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-10
**Review Level:** 2
**Review Counter:** 11
**Iteration:** 2
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied

---

### Step 1: Flip the default startup contract to Compose-managed infrastructure
**Status:** ✅ Complete

- [x] Update defaults for Compose-managed infrastructure with Aspire-launched app services
- [x] Invoke Compose helper `up` before AppHost in Unix and PowerShell start scripts
- [x] Preserve Podman-first, Docker-fallback, and exact `ATRADE_COMPOSE_COMMAND` behavior
- [x] Leave Compose running when AppHost exits
- [x] Preserve cross-platform wrapper semantics
- [x] R002: Gate Compose startup on `ATRADE_INFRASTRUCTURE_MODE=compose` in Unix and PowerShell scripts
- [x] R002: Revert unrelated `frontend/next-env.d.ts` generated change

---

### Step 2: Make the default AppHost graph dashboard-honest
**Status:** ✅ Complete

- [x] Make Compose infrastructure mode the default AppHost path
- [x] Ensure default Aspire manifest/dashboard omits infra container resources
- [x] Preserve secret-safe connection string and paper/LEAN handoff
- [x] Document any explicit legacy/fallback AppHost-managed infra mode as non-default
- [x] R005: Explicitly set `ATRADE_INFRASTRUCTURE_MODE=apphost` for legacy manifest validation

---

### Step 3: Migrate startup and AppHost validation
**Status:** ✅ Complete

- [x] Update start-wrapper tests for Compose-before-AppHost behavior
- [x] Update AppHost manifest/resource tests for no default infra resources
- [x] Update iBeam and LEAN tests for Compose profile ownership
- [x] Keep Windows wrapper validation aligned with Unix behavior

---

### Step 4: Migrate runtime persistence and infrastructure tests
**Status:** ✅ Complete

- [x] Update infrastructure runtime validation for Compose-managed containers
- [x] Update Postgres watchlist persistence validation for Compose volumes
- [x] Update Timescale cache persistence validation for Compose volumes
- [x] Ensure live runtime tests clean up only isolated test resources and skip when needed

---

### Step 5: Documentation and durable memory update
**Status:** ✅ Complete

- [x] Update README, PLAN, scripts README, and architecture overview
- [x] Update architecture modules doc if affected
- [x] Update verification inventories
- [x] Consider ADR and index it if created
- [x] Update tasks/CONTEXT runtime memory and next task state

---

### Step 6: Testing & Verification
**Status:** 🟨 In Progress

- [x] Compose contract tests passing
- [x] Start wrapper tests passing
- [x] AppHost manifest validation passing
- [x] AppHost worker/resource wiring validation passing
- [x] iBeam runtime contract validation passing
- [x] LEAN runtime validation passing
- [x] Compose/AppHost infra runtime validation passing or clearly skipped
- [x] Postgres watchlist volume validation passing or clearly skipped
- [x] Timescale cache volume validation passing or clearly skipped
- [x] FULL test suite passing
- [x] Build passes

---

### Step 7: Delivery
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
| 2026-05-09 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-10 06:13 | Task started | Runtime V2 lane-runner execution |
| 2026-05-10 06:13 | Step 0 started | Preflight |
| 2026-05-10 08:13 | Worker iter 1 | killed (wall-clock timeout) in 7200s, tools: 230 |
| 2026-05-10 08:13 | Step 6 started | Testing & Verification |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
| 2026-05-10 06:23 | Review R001 | plan Step 1: APPROVE |
| 2026-05-10 06:35 | Review R002 | code Step 1: REVISE |
| 2026-05-10 06:43 | Review R003 | code Step 1: APPROVE |
| 2026-05-10 06:52 | Review R004 | plan Step 2: APPROVE |
| 2026-05-10 07:02 | Review R005 | code Step 2: REVISE |
| 2026-05-10 07:07 | Review R006 | code Step 2: APPROVE |
| 2026-05-10 07:17 | Review R007 | plan Step 3: APPROVE |
| 2026-05-10 07:41 | Review R008 | code Step 3: APPROVE |
| 2026-05-10 07:48 | Review R009 | plan Step 4: APPROVE |
| 2026-05-10 08:05 | Review R011 | plan Step 5: APPROVE |
