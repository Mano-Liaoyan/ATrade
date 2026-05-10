# TP-070: Aspire external Compose infrastructure mode — Status

**Current Step:** Step 0: Preflight
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-10
**Review Level:** 2
**Review Counter:** 0
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
**Status:** ⬜ Not Started

- [ ] Add/finalize infrastructure mode setting while preserving current default
- [ ] Build localhost Postgres, TimescaleDB, Redis, and NATS connection strings from shared runtime values
- [ ] Keep database passwords secret in manifests through parameter/reference-expression plumbing
- [ ] Validate/normalize ports and mode values consistently

---

### Step 2: Add external-infra AppHost graph behavior
**Status:** ⬜ Not Started

- [ ] In Compose mode, omit AppHost infra container resources
- [ ] In Compose mode, keep API, IBKR worker, and frontend as Aspire resources
- [ ] Inject external connection strings into API/worker resources
- [ ] Preserve paper-trading and LEAN environment handoff
- [ ] Preserve existing AppHost-managed infrastructure behavior outside Compose mode

---

### Step 3: Add opt-in manifest and wiring tests
**Status:** ⬜ Not Started

- [ ] Add/update Compose-mode manifest tests asserting infra resources are absent
- [ ] Assert app resources and external connection string env are present
- [ ] Assert manifests do not expose raw database/broker secrets
- [ ] Keep current default AppHost manifest expectations passing until cutover

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
