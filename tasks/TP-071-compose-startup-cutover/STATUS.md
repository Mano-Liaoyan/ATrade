# TP-071: Compose startup cutover for Aspire-launched app services — Status

**Current Step:** Step 0: Preflight
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-10
**Review Level:** 2
**Review Counter:** 4
**Iteration:** 1
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
**Status:** 🟨 In Progress

- [x] Make Compose infrastructure mode the default AppHost path
- [x] Ensure default Aspire manifest/dashboard omits infra container resources
- [x] Preserve secret-safe connection string and paper/LEAN handoff
- [x] Document any explicit legacy/fallback AppHost-managed infra mode as non-default

---

### Step 3: Migrate startup and AppHost validation
**Status:** ⬜ Not Started

- [ ] Update start-wrapper tests for Compose-before-AppHost behavior
- [ ] Update AppHost manifest/resource tests for no default infra resources
- [ ] Update iBeam and LEAN tests for Compose profile ownership
- [ ] Keep Windows wrapper validation aligned with Unix behavior

---

### Step 4: Migrate runtime persistence and infrastructure tests
**Status:** ⬜ Not Started

- [ ] Update infrastructure runtime validation for Compose-managed containers
- [ ] Update Postgres watchlist persistence validation for Compose volumes
- [ ] Update Timescale cache persistence validation for Compose volumes
- [ ] Ensure live runtime tests clean up only isolated test resources and skip when needed

---

### Step 5: Documentation and durable memory update
**Status:** ⬜ Not Started

- [ ] Update README, PLAN, scripts README, and architecture overview
- [ ] Update architecture modules doc if affected
- [ ] Update verification inventories
- [ ] Consider ADR and index it if created
- [ ] Update tasks/CONTEXT runtime memory and next task state

---

### Step 6: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Compose contract tests passing
- [ ] Start wrapper tests passing
- [ ] AppHost manifest validation passing
- [ ] AppHost worker/resource wiring validation passing
- [ ] iBeam runtime contract validation passing
- [ ] LEAN runtime validation passing
- [ ] Compose/AppHost infra runtime validation passing or clearly skipped
- [ ] Postgres watchlist volume validation passing or clearly skipped
- [ ] Timescale cache volume validation passing or clearly skipped
- [ ] FULL test suite passing
- [ ] Build passes

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
