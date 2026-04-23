# TP-009: Scaffold first feature-module shells and the IBKR worker shell — Status

**Current Step:** Step 1: Scaffold feature-module shells
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-23
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 1
**Size:** M

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Read the module docs, solution, and project patterns
- [x] Confirm the target module/worker projects do not yet exist
- [x] Confirm `workers/` does not yet contain a real worker project

---

### Step 1: Scaffold feature-module shells
**Status:** 🟨 In Progress

- [ ] Create minimal compileable shells for `ATrade.Accounts`, `ATrade.Orders`, and `ATrade.MarketData`
- [ ] Add one tiny placeholder type per project
- [ ] Keep namespaces and project names aligned with docs

---

### Step 2: Scaffold the IBKR worker shell
**Status:** ⬜ Not started

- [ ] Create `workers/ATrade.Ibkr.Worker`
- [ ] Keep the worker compileable and intentionally inert
- [ ] Reference shared defaults only where appropriate
- [ ] Avoid broker, NATS, and database wiring

---

### Step 3: Wire the solution, not the runtime graph
**Status:** ⬜ Not started

- [ ] Add all new projects to `ATrade.sln`
- [ ] Keep `src/ATrade.AppHost/Program.cs` unchanged unless build-only scaffolding truly requires otherwise
- [ ] Keep runtime behavior otherwise unchanged

---

### Step 4: Add lightweight verification
**Status:** ⬜ Not started

- [ ] Create `tests/scaffolding/project-shells-tests.sh`
- [ ] Verify expected files exist and are listed in `ATrade.sln`
- [ ] Verify the solution builds

---

### Step 5: Update docs and plan
**Status:** ⬜ Not started

- [ ] Update `docs/architecture/modules.md`
- [ ] Update other current-state docs only where needed
- [ ] Update `PLAN.md` if milestone wording changes

---

### Step 6: Verification
**Status:** ⬜ Not started

- [ ] `dotnet build ATrade.sln`
- [ ] `bash tests/scaffolding/project-shells-tests.sh`
- [ ] Confirm docs do not overstate functionality

---

### Step 7: Delivery
**Status:** ⬜ Not started

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
| 2026-04-23 05:57 | Task started | Runtime V2 lane-runner execution |
| 2026-04-23 05:57 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Goal: turn the documented module map into real repository structure without taking on feature behavior yet.*
