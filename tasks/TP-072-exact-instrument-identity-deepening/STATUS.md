# TP-072: Exact Instrument Identity provider-neutral key deepening - Status

**Current Step:** Step 7: Delivery
**Status:** ✅ Complete
**Last Updated:** 2026-05-10
**Review Level:** 2
**Review Counter:** 14
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
**Status:** ✅ Complete

- [x] Active architecture docs updated
- [x] Saved backtest identity docs updated
- [x] Watchlist identity/key docs updated
- [x] `tasks/CONTEXT.md` updated with discoveries and next task state

---

### Step 6: Testing & Verification
**Status:** ✅ Complete

- [x] Exact Instrument Identity contract tests passing
- [x] Workspaces watchlist tests passing
- [x] Backtesting tests passing
- [x] Affected frontend/apphost identity contract tests passing
- [x] Frontend build passing if frontend identity code changes
- [x] FULL test suite passing
- [x] Build passes
- [x] R013 stale Category A apphost `ibkrConid` assertions migrated
- [x] R013 affected apphost identity scripts rerun and passing

---

### Step 7: Delivery
**Status:** ✅ Complete

- [x] "Must Update" docs modified
- [x] "Check If Affected" docs reviewed
- [x] Discoveries logged

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|
| R004 | Code | 2 | REVISE | `.reviews/R004-code-step2.md` |
| R013 | Code | 6 | REVISE | `.reviews/R013-code-step6.md` |

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|
| Canonical Exact Instrument Identity keys now exclude `ibkrConid`; legacy `ibkrConid` key segments normalize forward through the backend helper. | Implemented and documented. | `src/ATrade.MarketData/ExactInstrumentIdentity.cs`, `docs/architecture/provider-abstractions.md` |
| Frontend routes/query strings and provisional keys use provider-neutral identity fields only; `ibkrConid` remains only provider metadata in DTO/display paths. | Implemented and apphost source checks updated. | `frontend/lib/instrumentIdentity.ts`, `frontend/lib/terminalRoutes.ts`, `tests/apphost/*` |
| Plain `npm run build` fails under orchestrator `NODE_ENV=development`, but `NODE_ENV=production npm run build` passes; reviewer confirmed the plain-build failure exists at baseline. | Logged as pre-existing environment/build issue, not TP-072 regression. | `STATUS.md` Notes |

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
- R013 notes: frontend build only passed with `NODE_ENV=production npm run build`; plain `npm run build` fails at baseline too because orchestrator environment sets `NODE_ENV=development`. Category B Docker/Postgres apphost scripts still need stale canonical-key values reviewed if infrastructure validation is expanded.

| 2026-05-10 20:51 | Review R001 | plan Step 1: APPROVE |
| 2026-05-10 21:00 | Review R002 | code Step 1: APPROVE |
| 2026-05-10 21:07 | Review R003 | plan Step 2: APPROVE |
| 2026-05-10 21:14 | Review R004 | code Step 2: REVISE |
| 2026-05-10 21:22 | Review R005 | code Step 2: APPROVE |
| 2026-05-10 21:30 | Review R006 | plan Step 3: APPROVE |
| 2026-05-10 21:48 | Review R008 | plan Step 4: APPROVE |
| 2026-05-10 22:00 | Review R009 | code Step 4: APPROVE |
| 2026-05-10 22:05 | Review R010 | plan Step 5: APPROVE |
| 2026-05-10 22:13 | Review R011 | code Step 5: APPROVE |
| 2026-05-10 22:21 | Review R012 | plan Step 6: APPROVE |
| 2026-05-10 22:33 | Review R013 | code Step 6: REVISE |
| 2026-05-10 22:44 | Review R014 | code Step 6: APPROVE |
