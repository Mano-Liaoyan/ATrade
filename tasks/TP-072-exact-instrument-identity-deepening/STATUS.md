# TP-072: Exact Instrument Identity provider-neutral key deepening - Status

**Current Step:** Step 5: Documentation and durable memory update
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-10
**Review Level:** 2
**Review Counter:** 10
**Iteration:** 1
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it - aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied
- [x] Current Exact Instrument Identity decisions in `tasks/CONTEXT.md` understood

---

### Step 1: Pin provider-neutral identity/key contract tests first
**Status:** ✅ Complete

- [x] Backend canonical key tests added/updated
- [x] Legacy `ibkrConid` key normalization tests added/updated
- [x] Frontend provisional provider-neutral key tests/source checks added/updated
- [x] Saved backtest full identity tuple tests added/updated

---

### Step 2: Deepen backend Exact Instrument Identity implementation
**Status:** ✅ Complete

- [x] Canonical backend key emission excludes `ibkrConid`
- [x] IBKR `conid` alias handling is provider-specific
- [x] Runtime key construction has one implementation path
- [x] Legacy `ibkrConid`-bearing inputs normalize forward
- [x] Workspace key expectation tests updated to provider-neutral shape
- [x] Workspace SQL backfill emits provider-neutral keys without `ibkrConid`
- [x] Workspace SQL/test guardrails reject `ibkrConid` in canonical keys

---

### Step 3: Update adapters and persistence consumers
**Status:** ✅ Complete

- [x] API route/query adapters translate into provider-neutral identity tuple
- [x] Watchlist runtime persistence uses Exact Instrument Identity key construction
- [x] Saved backtest request/history/retry carries full provider-neutral tuple
- [x] Legacy repair/backfill behavior documented in code/tests where unavoidable

---

### Step 4: Update frontend identity handoff
**Status:** ✅ Complete

- [x] Frontend provisional keys use provider-neutral tuple only
- [x] Chart/analysis/backtest/watchlist handoff uses canonical provider-neutral fields
- [x] `ibkrConid` removed or isolated from public frontend route/query/key behavior
- [x] Backend-returned keys remain authoritative over optimistic state

---

### Step 5: Documentation and durable memory update
**Status:** 🟨 In Progress

- [x] Active architecture docs updated
- [x] Saved backtest identity docs updated
- [x] Watchlist identity/key docs updated
- [x] `tasks/CONTEXT.md` updated with discoveries and next task state

---

### Step 6: Testing & Verification
**Status:** Not Started

- [ ] Exact Instrument Identity contract tests passing
- [ ] Workspaces watchlist tests passing
- [ ] Backtesting tests passing
- [ ] Affected frontend/apphost identity contract tests passing
- [ ] Frontend build passing if frontend identity code changes
- [ ] FULL test suite passing
- [ ] Build passes

---

### Step 7: Delivery
**Status:** Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|
| R004 | Code | 2 | REVISE | `.reviews/R004-code-step2.md` |

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-05-10 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-10 20:45 | Task started | Runtime V2 lane-runner execution |
| 2026-05-10 20:45 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

- R004 suggestions: document `IbkrConid` as provider-specific metadata in Step 3/5; optional extra workspace normalizer defense-in-depth can be considered while fixing required workspace failures.

| 2026-05-10 20:51 | Review R001 | plan Step 1: APPROVE |
| 2026-05-10 21:00 | Review R002 | code Step 1: APPROVE |
| 2026-05-10 21:07 | Review R003 | plan Step 2: APPROVE |
| 2026-05-10 21:14 | Review R004 | code Step 2: REVISE |
| 2026-05-10 21:22 | Review R005 | code Step 2: APPROVE |
| 2026-05-10 21:30 | Review R006 | plan Step 3: APPROVE |
| 2026-05-10 21:48 | Review R008 | plan Step 4: APPROVE |
| 2026-05-10 22:00 | Review R009 | code Step 4: APPROVE |
| 2026-05-10 22:05 | Review R010 | plan Step 5: APPROVE |
