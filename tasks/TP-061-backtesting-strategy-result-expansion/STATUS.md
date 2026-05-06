# TP-061: Backtesting strategy and result expansion — Status

**Current Step:** Step 4: Add validation scripts and compatibility checks
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

### Step 1: Add built-in strategy definitions and parameter validation
**Status:** ✅ Complete

- [x] SMA, RSI, and breakout definitions/defaults added
- [x] Parameter, cost, and slippage validation implemented
- [x] Unknown/custom/multi-symbol/direct-bar/order-field requests rejected
- [x] Strategy validation and snapshot tests added

---

### Step 2: Expand LEAN input/template/parser for parameterized built-ins
**Status:** ✅ Complete

- [x] LEAN input/template supports selected built-in strategy and parameters
- [x] Generated algorithms remain analysis-only and order-free
- [x] Commission/slippage included in internal simulated accounting
- [x] Guardrail tests cover generated templates

---

### Step 3: Persist and expose rich backtest results
**Status:** ✅ Complete

- [x] Rich result shapes added
- [x] LEAN output maps into saved backtest result envelopes
- [x] Buy-and-hold benchmark calculated from same candle window
- [x] Result, benchmark, unavailable-engine, and no-fake-result tests added

---

### Step 4: Add validation scripts and compatibility checks
**Status:** 🟨 In Progress

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
| 2026-05-06 00:17 | Task started | Runtime V2 lane-runner execution |
| 2026-05-06 00:17 | Step 0 started | Preflight |
| 2026-05-06 00:20 | Step 0 preflight | Verified TP-060 status is complete, required projects/tests/docs exist, and .NET SDK 10.0.102 is available. |
| 2026-05-06 00:21 | Step 0 completed | Preflight checks passed. |
| 2026-05-06 00:21 | Step 1 started | Built-in strategy definitions and validation. |
| 2026-05-06 00:31 | Step 1 strategy catalog | Added built-in SMA/RSI/breakout strategy definitions, stable parameter names, and default values. |
| 2026-05-06 00:32 | Step 1 validation | Added strategy-specific parameter defaulting/range/relationship validation and cost/slippage failure tests. |
| 2026-05-06 00:33 | Step 1 guardrails | Unknown parameters, custom code, multi-symbol, direct-bar, and order-routing payloads are rejected before LEAN invocation. |
| 2026-05-06 00:34 | Step 1 tests | Backtesting targeted tests passed: 44/44. |
| 2026-05-06 00:35 | Step 1 completed | Strategy definitions, validation, guardrails, and snapshots are in place. |
| 2026-05-06 00:35 | Step 2 started | LEAN input/template/parser expansion for parameterized strategies. |
| 2026-05-06 00:45 | Step 2 LEAN input/template | Analysis requests now carry strategy parameters/accounting settings into LEAN input and generated built-in strategy code. |
| 2026-05-06 00:46 | Step 2 analysis-only guardrail | Generated LEAN source remains free of broker/order/live-trading tokens across all built-ins. |
| 2026-05-06 00:47 | Step 2 simulated accounting | Commission, bps costs, slippage, equity, signals, and trades are simulated internally without LEAN order APIs. |
| 2026-05-06 00:48 | Step 2 tests | LEAN targeted tests passed: 15/15; backtesting targeted tests passed: 44/44. |
| 2026-05-06 00:49 | Step 2 completed | LEAN parameterized built-ins, internal simulated accounting, parser support, and guardrails are in place. |
| 2026-05-06 00:49 | Step 3 started | Rich result persistence/envelopes and benchmark expansion. |
| 2026-05-06 01:00 | Step 3 result shapes | Added provider-neutral summary, equity curve, simulated trade, benchmark, accounting, source, and engine result records. |
| 2026-05-06 01:01 | Step 3 result mapping | LEAN parser details now map into saved TP-061 result envelopes with safe source/engine metadata. |
| 2026-05-06 01:02 | Step 3 benchmark | Buy-and-hold benchmark equity/return is computed from the same server-side candle window and labeled separately. |
| 2026-05-06 01:03 | Step 3 tests | Backtesting targeted tests passed: 47/47; LEAN targeted tests passed: 15/15; analysis targeted tests passed: 10/10. |
| 2026-05-06 01:04 | Step 3 completed | Rich saved-run result envelopes, benchmark calculation, safe errors, and no-fake-result tests are in place. |
| 2026-05-06 01:04 | Step 4 started | Validation scripts and compatibility checks. |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
