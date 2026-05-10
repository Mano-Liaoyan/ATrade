## Code Review: Step 5 — Documentation and durable memory update

### Verdict: APPROVE

### Summary

The four outcome-level checkboxes are correctly marked complete. All four "Must Update" documents (`provider-abstractions.md`, `modules.md`, `backtesting.md`, `tasks/CONTEXT.md`) have been revised to describe Exact Instrument Identity as provider-neutral, with `ibkrConid` recast as IBKR-specific provider metadata/alias only. The "Check If Affected" docs (`paper-trading-workspace.md`, `README.md`, `PLAN.md`) were also updated. Two minor documentation inconsistencies remain — one unaddressed R010 suggestion and an empty discoveries table — but these do not block the step's stated outcomes.

### Issues Found

*None blocking.*

### Pattern Violations

*None.*

### Test Gaps

*No code changes in this step — documentation-only step, no tests relevant.*

### Suggestions

1. **[Minor]** **`docs/design/atrade-terminal-ui.md` line 416** still describes the exact instrument identity handoff tuple as including `IBKR conid`:
   > `Preserve exact instrument identity handoff (\`provider\`, provider symbol id / IBKR \`conid\`, symbol, exchange, currency, asset class, \`instrumentKey\`, and \`pinKey\`)`

   The R010 plan review flagged both lines 197 and ~415. Line 197 was correctly updated (now says "IBKR `conid` is adapter metadata only, not route/query identity"), but line 416 was missed. This is a "Check If Affected" doc (not Must Update), so it doesn't block this step, but updating it would keep the design authority consistent with the new provider-neutral semantics.

2. **[Minor]** **STATUS.md Discoveries table is still empty.** The R010 plan review suggested capturing at least three discoveries from the four completed implementation steps:
   - The decision that `IbkrConid` remains stored on `ExactInstrumentIdentity` records as non-key provider-specific metadata
   - Any normalization edge cases encountered (e.g., legacy keys where `ibkrConid` differs from `providerSymbolId`)
   - The SQL backfill update that removed `ibkrConid` from `concat_ws`

   Filling these in would improve audit trail, but is not a completion criterion for Step 5.

3. **[Minor]** **`STATUS.md` updated date unchanged.** The frontmatter `updated` field of several docs (e.g., `modules.md` says `2026-05-07`, `paper-trading-workspace.md` says `2026-05-06`) was not bumped to 2026-05-10 even though content was changed. This is a minor frontmatter hygiene item; the PROMPT does not require it.

4. **[Note]** **No quality checks were run.** The `.pi/taskplane-config.json` has no `testing.commands` section, and neither the root nor `frontend/package.json` defines `typecheck`, `lint`, or `format:check` scripts. This is a documentation-only step with zero code changes, so quality checks are not applicable.

### Verification Summary

- **`provider-abstractions.md`** ✅ — §3 now defines `ExactInstrumentIdentity` as the "provider-neutral tuple" with `ibkrConid` as "provider-specific metadata." Compatibility layer now states legacy `ibkrConid` accepted only as "adapter-local alias." §6 (IBKR provider-specific) retains some `ibkrConid` phrasing in context of describing IBKR adapter behavior — acceptable since it's the IBKR implementation section.
- **`modules.md`** ✅ — §2.7, §2.10, and §2.3 all updated to use "provider-neutral" language and state `ibkrConid` is "provider metadata" or "alias data only."
- **`backtesting.md`** ✅ — Saved run contract now explicitly lists the full provider-neutral tuple; adds explicit statement that "IBKR `conid` is not a saved backtest identity dimension."
- **`tasks/CONTEXT.md`** ✅ — Next Task ID advanced to `TP-073`. Domain vocabulary updated to reflect post-TP-072 provider-neutral semantics.
- **`paper-trading-workspace.md`** ✅ — §§3.1, 7.3 updated with provider-neutral key construction language.
- **`README.md` / `PLAN.md`** ✅ — Updated to remove optional-`ibkrConid` wording, advance next Task ID to `TP-073`.
- **`atrade-terminal-ui.md`** ✅/⚠️ — Line ~197 updated correctly; line ~416 still references `IBKR conid` in identity handoff tuple (see Suggestion #1).
