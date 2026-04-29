# TP-025: Integrate LEAN as the first analysis engine provider — Status

**Current Step:** Step 1: Add LEAN provider project and runtime configuration
**Status:** 🟡 In Progress
**Last Updated:** 2026-04-30
**Review Level:** 3
**Review Counter:** 0
**Iteration:** 1
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ✅ Complete

- [x] Required files and paths exist
- [x] Dependencies satisfied
- [x] Analysis abstraction/no-engine behavior confirmed
- [x] Normalized market-data bars confirmed
- [x] LEAN integration approach selected and recorded

---

### Step 1: Add LEAN provider project and runtime configuration
**Status:** 🟨 In Progress

- [ ] LEAN provider project added to solution
- [ ] Official LEAN runtime/package/CLI/container integration added
- [ ] Safe LEAN config placeholders added to env templates
- [ ] LEAN provider registered behind analysis abstraction
- [ ] Targeted LEAN provider build passes

---

### Step 2: Implement analysis-only LEAN execution over ATrade market data
**Status:** ⬜ Not Started

- [ ] ATrade bars/symbols convert into LEAN input format
- [ ] Minimal LEAN analysis/backtest algorithm implemented
- [ ] Provider-neutral signals/metrics/results returned
- [ ] No brokerage/order-routing side effects enforced
- [ ] Targeted LEAN provider tests pass

---

### Step 3: Wire LEAN analysis through API and frontend
**Status:** ⬜ Not Started

- [ ] LEAN provider registered in API when configured
- [ ] Analysis endpoints run over market-data provider bars
- [ ] Frontend analysis client/types/panel added
- [ ] Loading/unavailable/timeout/error states handled
- [ ] Frontend build passes

---

### Step 4: Add LEAN verification
**Status:** ⬜ Not Started

- [ ] LEAN analysis shell test added
- [ ] Provider/configuration registration verified
- [ ] Provider-neutral API/frontend contracts verified
- [ ] Runtime execution or clean skip verified
- [ ] No order-routing/live-trading invocation verified
- [ ] Frontend analysis markers tested

---

### Step 5: Update docs for LEAN analysis
**Status:** ⬜ Not Started

- [ ] Analysis engines doc updated for LEAN implementation
- [ ] Paper-trading workspace doc updated
- [ ] Modules doc updated for Analysis/LEAN/API/frontend
- [ ] Provider abstractions doc updated
- [ ] Scripts README/README reviewed and updated if stale

---

### Step 6: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Docker/iBeam/LEAN-dependent tests pass or cleanly skip
- [ ] All failures fixed
- [ ] Frontend build passes
- [ ] Solution build passes

---

### Step 7: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
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
| Selected LEAN integration approach: invoke the official LEAN runtime through a configured LEAN CLI command or Docker-backed CLI/container workspace. The provider will generate a temporary analysis-only LEAN workspace from ATrade normalized bars, return provider-neutral results, and report unavailable/skip states when the runtime is absent instead of faking production output. Local check found Docker installed and `lean` CLI absent. | Implement in `ATrade.Analysis.Lean`; document runtime/config placeholders. | Step 0 preflight |

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-29 | Task staged | PROMPT.md and STATUS.md created |
| 2026-04-29 23:12 | Task started | Runtime V2 lane-runner execution |
| 2026-04-29 23:12 | Step 0 started | Preflight |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
