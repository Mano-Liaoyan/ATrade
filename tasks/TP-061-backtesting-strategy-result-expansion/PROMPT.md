# Task: TP-061 - Backtesting strategy and result expansion

**Created:** 2026-05-05
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This expands provider-neutral strategy validation and LEAN-generated analysis/backtest output across Analysis, Analysis.Lean, Backtesting, and tests. It is not auth-sensitive and remains paper-safe, but it changes result contracts and execution semantics.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 2, Security: 0, Reversibility: 1

## Canonical Task Folder

```
tasks/TP-061-backtesting-strategy-result-expansion/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Complete the backtesting MVP result model and built-in strategy support. Backtests must support three built-in strategies — SMA crossover, RSI mean-reversion, and breakout — with editable basic parameters, server-side validation, transaction-cost/slippage inputs, buy-and-hold benchmark comparison, summary metrics, equity curve, and simulated trade/signal list. Execution remains LEAN-only behind provider-neutral seams; no custom code, broker order routing, or fake fallback engine is introduced.

## Dependencies

- **Task:** TP-060 (async backtesting runner and SignalR status updates must exist)

## Context to Read First

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/INDEX.md` — documentation discovery layer
- `docs/architecture/backtesting.md` — backtesting contracts and runner behavior
- `docs/architecture/analysis-engines.md` — LEAN provider and provider-neutral analysis result rules
- `docs/architecture/provider-abstractions.md` — provider-neutral payload rules
- `docs/architecture/paper-trading-workspace.md` — no-order/no-live-trading guardrails
- `docs/architecture/modules.md` — module dependency direction
- `README.md` — verification entry points
- `PLAN.md` — active queue and dependency context

## Environment

- **Workspace:** `src/ATrade.Backtesting`, `src/ATrade.Analysis`, `src/ATrade.Analysis.Lean`, tests, docs
- **Services required:** None for unit/source tests. Real LEAN runtime is optional and must skip cleanly unless ignored local `.env` is configured.

## File Scope

- `src/ATrade.Backtesting/*`
- `src/ATrade.Analysis/AnalysisContracts.cs`
- `src/ATrade.Analysis/AnalysisRequestIntake.cs` (check if affected)
- `src/ATrade.Analysis.Lean/*`
- `tests/ATrade.Backtesting.Tests/*`
- `tests/ATrade.Analysis.Tests/*`
- `tests/ATrade.Analysis.Lean.Tests/*`
- `tests/apphost/backtesting-strategy-result-tests.sh` (new)
- `frontend/types/analysis.ts` (check if shared generated contracts require type updates; do not build UI here)
- `docs/architecture/backtesting.md`
- `docs/architecture/analysis-engines.md`
- `docs/architecture/modules.md` (check if affected)
- `docs/architecture/paper-trading-workspace.md`
- `README.md`
- `PLAN.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers
> expand steps when runtime discoveries warrant it. See task-worker agent for rules.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied

### Step 1: Add built-in strategy definitions and parameter validation

- [ ] Add provider-neutral strategy definitions for `sma-crossover`, `rsi-mean-reversion`, and `breakout` with display labels, descriptions, default parameters, min/max validation, and stable JSON parameter names
- [ ] Validate basic editable parameters server-side: SMA short/long windows, RSI period/oversold/overbought thresholds, breakout lookback/window, commission per trade, slippage bps, and initial capital already snapshotted by TP-059
- [ ] Reject unknown strategy IDs, custom code/script fields, invalid parameters, multi-symbol requests, direct bars, and order-routing fields before invoking LEAN
- [ ] Add tests for defaulting, validation failures, and persisted request snapshots for all three strategies

**Artifacts:**
- `src/ATrade.Backtesting/*` (modified/new)
- `tests/ATrade.Backtesting.Tests/*` (modified/new)

### Step 2: Expand LEAN input/template/parser for parameterized built-ins

- [ ] Extend the LEAN input model and generated analysis-only algorithm template to execute the selected built-in strategy over ATrade OHLCV bars using parameter values from the provider-neutral request
- [ ] Keep generated LEAN code analysis-only: no `MarketOrder`, brokerage model, live mode, ATrade order endpoints, or broker execution calls
- [ ] Apply commission/slippage inputs to internal simulated trade/equity accounting without using broker/order APIs
- [ ] Add/extend guardrail tests proving all generated strategy templates remain free of order-routing/live-trading tokens

**Artifacts:**
- `src/ATrade.Analysis.Lean/*` (modified)
- `tests/ATrade.Analysis.Lean.Tests/*` (modified/new)

### Step 3: Persist and expose rich backtest results

- [ ] Add provider-neutral result shapes for summary metrics, equity curve points, simulated trades/signals, benchmark buy-and-hold return/equity, source metadata, and safe engine/error metadata
- [ ] Map LEAN output into the `ATrade.Backtesting` saved-run result envelope and preserve compatibility with existing `AnalysisResult` consumers where applicable
- [ ] Ensure buy-and-hold benchmark is calculated from the same server-side candle window and labelled separately from strategy returns
- [ ] Add tests for completed SMA/RSI/breakout runs, benchmark calculation, equity curve/trade list shape, failed unavailable engine responses, and no fake results

**Artifacts:**
- `src/ATrade.Backtesting/*` (modified)
- `src/ATrade.Analysis/*` (modified if needed)
- `src/ATrade.Analysis.Lean/*` (modified)
- `tests/ATrade.Backtesting.Tests/*` (modified)
- `tests/ATrade.Analysis.Tests/*` (modified if needed)
- `tests/ATrade.Analysis.Lean.Tests/*` (modified)

### Step 4: Add validation scripts and compatibility checks

- [ ] Create `tests/apphost/backtesting-strategy-result-tests.sh` covering source/API contract strings for strategy IDs, parameter validation, rich results, benchmark fields, no custom-code fields, and no order-routing behavior
- [ ] Update existing analysis/LEAN apphost tests only if result contract changes require it; do not weaken no-engine/unavailable/no-order assertions
- [ ] Update frontend shared types only if the backend result contract is already represented there, but do not create UI components in this task

**Artifacts:**
- `tests/apphost/backtesting-strategy-result-tests.sh` (new)
- `frontend/types/analysis.ts` (modified if needed)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the FULL test suite as a quality gate.

- [ ] Run targeted backtesting tests: `dotnet test tests/ATrade.Backtesting.Tests/ATrade.Backtesting.Tests.csproj --nologo --verbosity minimal`
- [ ] Run targeted LEAN tests: `dotnet test tests/ATrade.Analysis.Lean.Tests/ATrade.Analysis.Lean.Tests.csproj --nologo --verbosity minimal`
- [ ] Run targeted analysis tests: `dotnet test tests/ATrade.Analysis.Tests/ATrade.Analysis.Tests.csproj --nologo --verbosity minimal`
- [ ] Run strategy/result validation: `bash tests/apphost/backtesting-strategy-result-tests.sh`
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.slnx --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] Update active docs with built-in strategy catalog, parameters/defaults, costs/slippage model, benchmark behavior, result payload fields, and LEAN-only/no-custom-code rules
- [ ] Update README/PLAN verification inventory/runtime text if affected
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/backtesting.md` — built-in strategies, parameters, rich result fields, benchmark/cost model
- `docs/architecture/analysis-engines.md` — update LEAN provider behavior if analysis contracts/result parsing change
- `docs/architecture/paper-trading-workspace.md` — update backtesting strategy/result UX contract if needed
- `README.md` — verification entry points/runtime surface if adding tests or result surface
- `PLAN.md` — current direction if affected

**Check If Affected:**
- `docs/architecture/modules.md` — update only if module responsibilities change
- `docs/architecture/provider-abstractions.md` — update only if provider-neutral analysis payload rules change

## Completion Criteria

- [ ] All steps complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] SMA crossover, RSI mean-reversion, and breakout built-ins have editable validated parameters and defaults
- [ ] Backtest results include summary, equity curve, simulated trades/signals, buy-and-hold benchmark, costs/slippage impact, source metadata, and safe errors
- [ ] LEAN remains the only execution path and unavailable/no-engine states fail explicitly
- [ ] No custom code, generated orders, broker routing, live trading, fake engine, synthetic data, or direct browser bars are introduced

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits
for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-061): complete Step N — description`
- **Bug fixes:** `fix(TP-061): description`
- **Tests:** `test(TP-061): description`
- **Hydration:** `hydrate: TP-061 expand Step N checkboxes`

## Do NOT

- Expand task scope — add tech debt to `tasks/CONTEXT.md` instead
- Skip tests
- Modify framework/standards docs without explicit user approval
- Load docs not listed in "Context to Read First"
- Commit without the task ID prefix in the commit message
- Add frontend backtesting UI, comparison screens, export, optimization, multi-symbol portfolios, or custom user code
- Use LEAN brokerage/order APIs, `MarketOrder`, live mode, broker execution, or ATrade order endpoints
- Add a C# fallback engine or fake successful results when LEAN is unavailable
- Expose secrets, account identifiers, gateway URLs, LEAN workspace paths, process command lines, tokens, or cookies

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
