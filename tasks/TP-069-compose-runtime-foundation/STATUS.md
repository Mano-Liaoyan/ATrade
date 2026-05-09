# TP-069: Compose runtime foundation — Status

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

### Step 1: Extend the local runtime contract for Compose-managed infrastructure
**Status:** ⬜ Not Started

- [ ] Add committed Compose command/project and stable infra port variables
- [ ] Preserve `.env.template` → `.env` → process env precedence
- [ ] Extend `LocalRuntimeContract` defaults/known variables/tests
- [ ] Keep secret-bearing variables classified and out of committed values

---

### Step 2: Add the Compose infrastructure definition
**Status:** ⬜ Not Started

- [ ] Create default Postgres, TimescaleDB, Redis, and NATS Compose services
- [ ] Preserve durable named volume contract for Postgres and TimescaleDB
- [ ] Mirror pids-limit and Timescale tuning safeguards where Compose supports them
- [ ] Add optional `ibkr` and `lean` profile services using existing runtime variables

---

### Step 3: Add reusable Compose helper scripts
**Status:** ⬜ Not Started

- [ ] Add Unix helper with local runtime env loading and Compose actions
- [ ] Add PowerShell helper with equivalent Windows behavior
- [ ] Implement `ATRADE_COMPOSE_COMMAND`, Podman-default, Docker-fallback command selection
- [ ] Implement automatic `ibkr` and `lean` profile selection without leaking secrets

---

### Step 4: Add contract validation
**Status:** ⬜ Not Started

- [ ] Add Compose contract tests for command selection, profiles, ports, volumes, and safety
- [ ] Keep live Compose checks optional/skippable when no engine is installed
- [ ] Update existing runtime contract tests for intentional new variables

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Compose contract tests passing
- [ ] Local runtime contract tests passing
- [ ] Apphost local runtime shell contract tests passing if affected
- [ ] Paper-trading config contract tests passing if affected
- [ ] FULL test suite passing
- [ ] Build passes

---

### Step 6: Documentation & Delivery
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
