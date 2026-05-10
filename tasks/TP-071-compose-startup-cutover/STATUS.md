# TP-071: Compose startup cutover for Aspire-launched app services — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-09
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

---

### Step 1: Flip the default startup contract to Compose-managed infrastructure
**Status:** ⬜ Not Started

- [ ] Update defaults for Compose-managed infrastructure with Aspire-launched app services
- [ ] Invoke Compose helper `up` before AppHost in Unix and PowerShell start scripts
- [ ] Preserve Podman-first, Docker-fallback, and exact `ATRADE_COMPOSE_COMMAND` behavior
- [ ] Leave Compose running when AppHost exits
- [ ] Preserve cross-platform wrapper semantics

---

### Step 2: Make the default AppHost graph dashboard-honest
**Status:** ⬜ Not Started

- [ ] Make Compose infrastructure mode the default AppHost path
- [ ] Ensure default Aspire manifest/dashboard omits infra container resources
- [ ] Preserve secret-safe connection string and paper/LEAN handoff
- [ ] Document any explicit legacy/fallback AppHost-managed infra mode as non-default

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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
