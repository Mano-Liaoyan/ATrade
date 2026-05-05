# TP-059: Backtesting domain, persistence, and API — Status

**Current Step:** Step 3: Expose first-class backtest REST APIs
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-06
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 2
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
**Status:** ✅ Complete

- [x] Backtesting contracts and statuses created
- [x] Built-in strategy IDs and JSON parameter bag validation implemented
- [x] Run creation snapshots effective capital/source and blocks without capital
- [x] Tests cover validation, capital snapshotting, direct-bar rejection, no custom code, and no order fields

---

### Step 2: Add Postgres persistence for saved backtest runs
**Status:** ✅ Complete

- [x] Idempotent saved-run schema initialization added
- [x] Repository supports create/list/get/status/cancel/retry operations
- [x] Persistence excludes secrets, account identifiers, gateway URLs, tokens, cookies, and direct bars
- [x] Repository tests added

---

### Step 3: Expose first-class backtest REST APIs
**Status:** ✅ Complete

- [x] `AddBacktestingModule(...)` composed in API
- [x] `POST /api/backtests` implemented
- [x] `GET /api/backtests` and `GET /api/backtests/{id}` implemented
- [x] `POST /api/backtests/{id}/cancel` and `/retry` implemented
- [x] API/apphost contract tests added

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
| 2026-05-05 23:09 | Worker iter 1 | done in 599s, tools: 86 |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
