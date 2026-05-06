# TP-061: Backtesting strategy and result expansion — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-05-05
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** M

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code
> changes. Workers expand steps when runtime discoveries warrant it — aim for
> 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

---

### Step 1: Add built-in strategy definitions and parameter validation
**Status:** ⬜ Not Started

- [ ] SMA, RSI, and breakout definitions/defaults added
- [ ] Parameter, cost, and slippage validation implemented
- [ ] Unknown/custom/multi-symbol/direct-bar/order-field requests rejected
- [ ] Strategy validation and snapshot tests added

---

### Step 2: Expand LEAN input/template/parser for parameterized built-ins
**Status:** ⬜ Not Started

- [ ] LEAN input/template supports selected built-in strategy and parameters
- [ ] Generated algorithms remain analysis-only and order-free
- [ ] Commission/slippage included in internal simulated accounting
- [ ] Guardrail tests cover generated templates

---

### Step 3: Persist and expose rich backtest results
**Status:** ⬜ Not Started

- [ ] Rich result shapes added
- [ ] LEAN output maps into saved backtest result envelopes
- [ ] Buy-and-hold benchmark calculated from same candle window
- [ ] Result, benchmark, unavailable-engine, and no-fake-result tests added

---

### Step 4: Add validation scripts and compatibility checks
**Status:** ⬜ Not Started

- [ ] `tests/apphost/backtesting-strategy-result-tests.sh` created
- [ ] Existing analysis/LEAN apphost tests updated only if required
- [ ] Shared frontend types updated only if contract compatibility requires it

---

### Step 5: Testing & Verification
**Status:** ⬜ Not Started

- [ ] Targeted backtesting tests passing
- [ ] Targeted LEAN tests passing
- [ ] Targeted analysis tests passing
- [ ] Strategy/result validation passing
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

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
