# TP-069: Compose runtime foundation — Status

**Current Step:** Step 1: Extend the local runtime contract for Compose-managed infrastructure
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-10
**Review Level:** 2
**Review Counter:** 1
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

### Step 1: Extend the local runtime contract for Compose-managed infrastructure
**Status:** 🟨 In Progress

- [x] Add committed Compose command/project and stable infra port variables
- [x] Preserve `.env.template` → `.env` → process env precedence
- [x] Extend `LocalRuntimeContract` defaults/known variables/tests
- [x] Keep secret-bearing variables classified and out of committed values

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
| R001 | Plan | Step 1 | APPROVE | .reviews/R001-plan-step1.md |

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-05-09 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-10 03:28 | Task started | Runtime V2 lane-runner execution |
| 2026-05-10 03:28 | Step 0 started | Preflight |
| 2026-05-10 03:30 | Step 0 completed | Required files and dependencies verified |
| 2026-05-10 03:30 | Step 1 started | Runtime contract extension |
| 2026-05-10 03:31 | Step 1 plan review | APPROVE |
| 2026-05-10 03:35 | Step 1 targeted test | `dotnet test tests/ATrade.ServiceDefaults.Tests/ATrade.ServiceDefaults.Tests.csproj --nologo --verbosity minimal` passed |

---

## Blockers

*None*

---

## Notes

- 2026-05-10 03:35 — Review R001 plan Step 1: APPROVE
