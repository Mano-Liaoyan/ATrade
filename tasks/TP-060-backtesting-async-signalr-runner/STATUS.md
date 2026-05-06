# TP-060: Backtesting async runner and SignalR updates — Status

**Current Step:** Step 3: Add best-effort cancellation and SignalR job updates
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-05
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

### Step 1: Add durable async job runner and restart recovery
**Status:** ✅ Complete

- [x] Hosted runner claims queued runs and records status/timestamps durably
- [x] Startup recovery fails interrupted running jobs and preserves queued jobs
- [x] Duplicate-claim safeguards implemented
- [x] Runner/recovery tests added

---

### Step 2: Execute runs through market data and analysis/LEAN seams
**Status:** ✅ Complete

- [x] Runner fetches candles server-side via `IMarketDataService`
- [x] Runner invokes `IAnalysisEngineRegistry` with saved strategy metadata and cancellation
- [x] Market-data and analysis unavailable states map to failed runs safely
- [x] Completed result envelopes persist for TP-061 enrichment

---

### Step 3: Add best-effort cancellation and SignalR job updates
**Status:** ✅ Complete

- [x] Queued and running cancel behavior implemented
- [x] `/hubs/backtests` or equivalent SignalR hub added
- [x] Update payloads redacted and safe
- [x] Hub/cancellation validation added

---

### Step 4: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Targeted backtesting tests passing
- [ ] SignalR/runner apphost validation passing
- [ ] Existing analysis tests passing
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 5: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] README/PLAN verification/current-surface text updated if affected
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
| 2026-05-05 | Task staged | PROMPT.md and STATUS.md created |
| 2026-05-05 23:46 | Task started | Runtime V2 lane-runner execution |
| 2026-05-05 23:46 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
