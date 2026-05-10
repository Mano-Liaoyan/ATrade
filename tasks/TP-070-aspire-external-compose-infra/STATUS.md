# TP-070: Aspire external Compose infrastructure mode — Status

**Current Step:** Step 3: Add opt-in manifest and wiring tests
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-10
**Review Level:** 2
**Review Counter:** 6
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

### Step 1: Model opt-in Compose infrastructure mode
**Status:** ✅ Complete

- [x] Add/finalize infrastructure mode setting while preserving current default
- [x] Build localhost Postgres, TimescaleDB, Redis, and NATS connection strings from shared runtime values
- [x] Keep database passwords secret in manifests through parameter/reference-expression plumbing
- [x] Validate/normalize ports and mode values consistently

---

### Step 2: Add external-infra AppHost graph behavior
**Status:** ✅ Complete

- [x] In Compose mode, omit AppHost infra container resources
- [x] In Compose mode, keep API, IBKR worker, and frontend as Aspire resources
- [x] Inject external connection strings into API/worker resources
- [x] Preserve paper-trading and LEAN environment handoff
- [x] Preserve existing AppHost-managed infrastructure behavior outside Compose mode

---

### Step 3: Add opt-in manifest and wiring tests
**Status:** ✅ Complete

- [x] Add/update Compose-mode manifest tests asserting infra resources are absent
- [x] Assert app resources and external connection string env are present
- [x] Assert manifests do not expose raw database/broker secrets
- [x] Keep current default AppHost manifest expectations passing until cutover

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] AppHost manifest validation passing
- [ ] AppHost worker/resource wiring validation passing
- [ ] iBeam runtime validation passing if affected
- [ ] LEAN runtime validation passing if affected
- [ ] Local runtime contract tests passing if affected
- [ ] FULL test suite passing
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
| 2026-05-09 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-10 05:04 | Task started | Runtime V2 lane-runner execution |
| 2026-05-10 05:04 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
| 2026-05-10 05:09 | Review R001 | plan Step 1: APPROVE |
| 2026-05-10 05:18 | Review R002 | code Step 1: APPROVE |
| 2026-05-10 05:24 | Review R003 | plan Step 2: APPROVE |
| 2026-05-10 05:33 | Review R004 | code Step 2: APPROVE |
| 2026-05-10 05:38 | Review R005 | plan Step 3: APPROVE |
| 2026-05-10 05:48 | Review R006 | code Step 3: APPROVE |
