# TP-062: Terminal backtest run, history, retry, and status streaming — Status

**Current Step:** Step 1: Add BACKTEST module registration and typed client/workflow contracts
**Status:** 🟡 In Progress
**Last Updated:** 2026-05-06
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

### Step 1: Add BACKTEST module registration and typed client/workflow contracts
**Status:** ⬜ Not Started

- [ ] BACKTEST enabled module registered
- [ ] Backtesting frontend types added
- [ ] Backtest/capital HTTP and SignalR client added
- [ ] Terminal backtest workflow coordinates capital, create/cancel/retry, history/detail, and SignalR updates

---

### Step 2: Build the Backtest workspace form, capital panel, and live status UI
**Status:** ⬜ Not Started

- [ ] Single-symbol strategy run form created
- [ ] Paper-capital panel shows source and supports local capital update
- [ ] Status, cancel, retry, unavailable/error states rendered truthfully
- [ ] ATradeTerminalApp/rail/handoff routing wired without breaking existing modules

---

### Step 3: Add run history, detail, cancel, and retry views
**Status:** ⬜ Not Started

- [ ] Saved run history rendered
- [ ] Run detail includes summary, benchmark, trades/signals, and source metadata
- [ ] Cancel and retry controls call backend endpoints correctly
- [ ] Empty/unavailable states avoid fake runs/results

---

### Step 4: Add frontend validation coverage
**Status:** ⬜ Not Started

- [ ] `tests/apphost/frontend-terminal-backtest-workspace-tests.sh` created
- [ ] Existing terminal validations updated only if required
- [ ] Validation remains provider/runtime independent

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Backtest workspace validation passing
- [ ] Terminal cutover validation passing
- [ ] Chart/analysis validation passing
- [ ] Frontend build passes
- [ ] FULL test suite passing
- [ ] All failures fixed
- [ ] Build passes

---

### Step 6: Documentation & Delivery
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
| 2026-05-06 00:48 | Task started | Runtime V2 lane-runner execution |
| 2026-05-06 00:48 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
