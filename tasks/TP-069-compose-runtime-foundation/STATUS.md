# TP-069: Compose runtime foundation — Status

**Current Step:** Step 4: Add contract validation
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-10
**Review Level:** 2
**Review Counter:** 8
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
**Status:** ✅ Complete

- [x] Add committed Compose command/project and stable infra port variables
- [x] Preserve `.env.template` → `.env` → process env precedence
- [x] Extend `LocalRuntimeContract` defaults/known variables/tests
- [x] Keep secret-bearing variables classified and out of committed values
- [x] R002: Reword `.env.template` exclusions so Compose host ports are not contradicted
- [x] R002: Add matching `scripts/README.md` Compose variable documentation asserted by shell tests

---

### Step 2: Add the Compose infrastructure definition
**Status:** ✅ Complete

- [x] Create default Postgres, TimescaleDB, Redis, and NATS Compose services
- [x] Preserve durable named volume contract for Postgres and TimescaleDB
- [x] Mirror pids-limit and Timescale tuning safeguards where Compose supports them
- [x] Add optional `ibkr` and `lean` profile services using existing runtime variables

---

### Step 3: Add reusable Compose helper scripts
**Status:** ✅ Complete

- [x] Add Unix helper with local runtime env loading and Compose actions
- [x] Add PowerShell helper with equivalent Windows behavior
- [x] Implement `ATRADE_COMPOSE_COMMAND`, Podman-default, Docker-fallback command selection
- [x] Implement automatic `ibkr` and `lean` profile selection without leaking secrets

---

### Step 4: Add contract validation
**Status:** 🟨 In Progress

- [x] Add Compose contract tests for command selection, profiles, ports, volumes, and safety
- [x] Keep live Compose checks optional/skippable when no engine is installed
- [x] Update existing runtime contract tests for intentional new variables

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
| R002 | Code | Step 1 | REVISE | .reviews/R002-code-step1.md |
| R003 | Code | Step 1 | APPROVE | .reviews/R003-code-step1.md |
| R004 | Plan | Step 2 | APPROVE | .reviews/R004-plan-step2.md |
| R005 | Code | Step 2 | APPROVE | .reviews/R005-code-step2.md |
| R006 | Plan | Step 3 | APPROVE | .reviews/R006-plan-step3.md |
| R007 | Code | Step 3 | APPROVE | .reviews/R007-code-step3.md |
| R008 | Plan | Step 4 | APPROVE | .reviews/R008-plan-step4.md |

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
| 2026-05-10 03:46 | Step 1 code review | R002 REVISE; revision checkboxes added |
| 2026-05-10 03:53 | Step 1 code review | R003 APPROVE |
| 2026-05-10 03:54 | Step 1 completed | Runtime contract Compose variables approved |
| 2026-05-10 03:54 | Step 2 started | Compose infrastructure definition |
| 2026-05-10 03:55 | Step 2 plan review | R004 APPROVE |
| 2026-05-10 04:06 | Step 2 code review | R005 APPROVE |
| 2026-05-10 04:06 | Step 2 completed | Compose infrastructure definition approved |
| 2026-05-10 04:06 | Step 3 started | Compose helper scripts |
| 2026-05-10 04:07 | Step 3 plan review | R006 APPROVE |
| 2026-05-10 04:23 | Step 3 code review | R007 APPROVE |
| 2026-05-10 04:23 | Step 3 completed | Compose helper scripts approved |
| 2026-05-10 04:23 | Step 4 started | Compose contract validation |
| 2026-05-10 04:24 | Step 4 plan review | R008 APPROVE |

---

## Blockers

*None*

---

## Notes

- 2026-05-10 03:35 — Review R001 plan Step 1: APPROVE
- 2026-05-10 03:46 — Review R002 code Step 1: REVISE
- 2026-05-10 03:53 — Review R003 code Step 1: APPROVE
- 2026-05-10 03:55 — Review R004 plan Step 2: APPROVE
- 2026-05-10 04:06 — Review R005 code Step 2: APPROVE
- 2026-05-10 04:07 — Review R006 plan Step 3: APPROVE
- 2026-05-10 04:23 — Review R007 code Step 3: APPROVE
- 2026-05-10 04:24 — Review R008 plan Step 4: APPROVE
- R002 suggestions: consider additional Compose project-name edge coverage and exact scripts/README wording reuse; not blocking.
| 2026-05-10 04:28 | Review R008 | plan Step 4: APPROVE |
