# TP-059: Backtesting domain, persistence, and API — Status

**Current Step:** Step 0: Preflight
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-06
**Review Level:** 3
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

### Step 1: Create provider-neutral backtesting contracts and validation
**Status:** ⬜ Not Started

- [ ] Backtesting contracts and statuses created
- [ ] Built-in strategy IDs and JSON parameter bag validation implemented
- [ ] Run creation snapshots effective capital/source and blocks without capital
- [ ] Tests cover validation, capital snapshotting, direct-bar rejection, no custom code, and no order fields

---

### Step 2: Add Postgres persistence for saved backtest runs
**Status:** ⬜ Not Started

- [ ] Idempotent saved-run schema initialization added
- [ ] Repository supports create/list/get/status/cancel/retry operations
- [ ] Persistence excludes secrets, account identifiers, gateway URLs, tokens, cookies, and direct bars
- [ ] Repository tests added

---

### Step 3: Expose first-class backtest REST APIs
**Status:** ⬜ Not Started

- [ ] `AddBacktestingModule(...)` composed in API
- [ ] `POST /api/backtests` implemented
- [ ] `GET /api/backtests` and `GET /api/backtests/{id}` implemented
- [ ] `POST /api/backtests/{id}/cancel` and `/retry` implemented
- [ ] API/apphost contract tests added

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Targeted backtesting tests passing
- [ ] Backtesting API/apphost validation passing
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] New `docs/architecture/backtesting.md` created
- [ ] Docs index and architecture docs updated
- [ ] README/PLAN updated if affected
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
| 2026-05-05 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-05 22:59 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 22:59 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
