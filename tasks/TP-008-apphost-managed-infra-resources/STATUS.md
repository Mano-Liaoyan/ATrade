# TP-008: Extend AppHost with managed infrastructure resources — Status

**Current Step:** Step 6: Delivery
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-23
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Read the AppHost, docs, and existing apphost test files
- [x] Confirm the AppHost currently declares only `api` and `frontend`
- [x] Confirm no existing test already covers infra-resource declarations

---

### Step 1: Declare managed infrastructure resources
**Status:** ✅ Complete

- [x] Update AppHost package/project surface as needed
- [x] Add named Aspire-managed resources for `Postgres`, `TimescaleDB`, `Redis`, and `NATS`
- [x] Be explicit about the local `TimescaleDB` representation
- [x] Use stable resource names for future wiring

---

### Step 2: Preserve the current bootstrap graph
**Status:** ✅ Complete

- [x] Keep `ATrade.Api` and the frontend in the graph
- [x] Avoid speculative consumers of the new resources
- [x] Keep broker logic, market-data logic, and worker wiring out of scope

---

### Step 3: Add verification
**Status:** ✅ Complete

- [x] Create `tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [x] Verify the published manifest includes infra resources and still includes `api` / `frontend`
- [x] Keep the primary verification path container-engine-independent

---

### Step 4: Update docs and plan
**Status:** ✅ Complete

- [x] Update `scripts/README.md`
- [x] Update `docs/architecture/overview.md`
- [x] Update `PLAN.md` if the milestone status changes
- [x] Update other current-state docs only where needed

---

### Step 5: Verification
**Status:** ✅ Complete

- [x] `dotnet build ATrade.sln`
- [x] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [x] Confirm docs and plan text match the resulting graph

---

### Step 6: Delivery
**Status:** 🟨 In Progress

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
| 2026-04-23 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-23 06:06 | Task started | Runtime V2 lane-runner execution |
| 2026-04-23 06:06 | Step 0 started | Preflight |
| 2026-04-23 06:12 | Step 0 completed | Read active docs, confirmed AppHost currently declares only `api` and `frontend`, and confirmed no existing tests cover infra resources |
| 2026-04-23 06:12 | Step 1 started | Declare managed infrastructure resources |
| 2026-04-23 06:14 | Step 1 completed | Added Aspire-managed `postgres`, `timescaledb`, `redis`, and `nats` resources plus AppHost hosting packages |
| 2026-04-23 06:14 | Step 2 started | Preserve the current bootstrap graph |
| 2026-04-23 06:15 | Step 2 completed | Verified `Program.cs` still declares `api` and `frontend` and adds no worker, broker, market-data, or `WithReference(...)` consumers |
| 2026-04-23 06:15 | Step 3 started | Add verification |
| 2026-04-23 06:17 | Step 3 completed | Added manifest-based AppHost infrastructure verification script and passed it without needing a container engine |
| 2026-04-23 06:17 | Step 4 started | Update docs and plan |
| 2026-04-23 06:23 | Step 4 completed | Updated `scripts/README.md`, `docs/architecture/overview.md`, `PLAN.md`, `README.md`, and `docs/architecture/modules.md` to reflect the infrastructure-aware AppHost graph |
| 2026-04-23 06:23 | Step 5 started | Verification |
| 2026-04-23 06:26 | Step 5 completed | `dotnet build ATrade.sln` and `bash tests/apphost/apphost-infrastructure-manifest-tests.sh` passed; docs and plan language matches the manifest graph |
| 2026-04-23 06:26 | Step 6 started | Delivery |

---

## Blockers

*None*

---

## Notes

*Goal: make the Aspire AppHost graph match the infrastructure contract already described by the active architecture docs.*
