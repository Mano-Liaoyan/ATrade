## Plan Review: Step 5 — Documentation and durable memory update

### Verdict: APPROVE

### Summary

The four outcome-level checkboxes are properly scoped: they cover the "Must Update" docs and the CONTEXT.md durable-memory update required by PROMPT.md, and they leverage the worker's intimate knowledge from implementing Steps 1-4. No missing outcomes; the plan is sufficient to complete the step.

### Issues Found

*None blocking.*

### Missing Items

*None.* The checkboxes cover all four "Must Update" artifacts from PROMPT.md plus the "Check If Affected" review.

### Suggestions

1. **`docs/design/atrade-terminal-ui.md` has two references to `ibkrConid`/`IBKR conid`** (lines 197, 415) that describe the exact identity handoff as including `ibkrConid`. This design doc is not in the PROMPT "Must Update" or "Check If Affected" lists, but it is the active UI design authority. Consider updating these two references so the frontend design authority matches the new provider-neutral semantics. At minimum, review and decide whether a clarifying note is needed.

2. **Specific doc sections to focus on —** Based on grep analysis of the current doc state, the following specific paragraphs still describe `ibkrConid` as a canonical identity dimension and need updating:

   - **`provider-abstractions.md` §3** (Market-Data Provider Contract): The `ExactInstrumentIdentity` description currently says "optional IBKR `conid`" and states frontend routes "may carry `ibkrConid` alongside `providerSymbolId`." These need to shift to describing `ibkrConid` as IBKR-specific provider metadata only.
   - **`provider-abstractions.md` §3** (Compatibility layer): The `MarketDataService` description lists "optional `ibkrConid`" as forwarded identity metadata — should be clarified as backward-compat / IBKR-adapter-only.
   - **`provider-abstractions.md` §6** (Current IBKR Provider Implementations): References "provider symbol id/IBKR `conid` as the exact identity" — needs the `ibkrConid` part recast as provider-specific metadata.
   - **`modules.md` §2** (current slice summary): "provider id / IBKR `conid`" in the workspace watchlist description.
   - **`modules.md` §2.7** (ATrade.MarketData): "optional IBKR `conid`" in ExactInstrumentIdentity description.
   - **`modules.md` §2.10** (ATrade.Workspaces): "optional provider symbol id / IBKR `conid`" in schema description.
   - **`paper-trading-workspace.md` §3.1** (API query metadata): Lists `ibkrConid` alongside `providerSymbolId` as accepted query metadata — should note it's backward-compat only.
   - **`paper-trading-workspace.md` §7.3** (Preference storage): "optional `ibkrConid`" in search-result pin metadata description.
   - **`backtesting.md`**: Currently has no explicit mention of `ibkrConid` (good), but should add an explicit statement that saved runs persist and display the full provider-neutral tuple (`provider`, `providerSymbolId`, `symbol`, `exchange`, `currency`, `assetClass`), without `ibkrConid`.

3. **Discoveries table is empty —** The STATUS.md Discoveries table has zero entries despite four completed implementation steps. During doc updates, the worker should capture at least:
   - The decision that `IbkrConid` remains stored on `ExactInstrumentIdentity` records as non-key provider-specific metadata (noted in R004 suggestion)
   - Any normalization edge cases encountered (e.g., legacy keys where `ibkrConid` differs from `providerSymbolId`)
   - The SQL backfill update that removed `ibkrConid` from `concat_ws` (R004 issue #4)

4. **Cross-reference R004 notes —** The R004 review explicitly requested that Step 3/5 docs make clear that `IbkrConid` is provider-specific metadata, not an identity dimension. The "Active architecture docs updated" checkbox should ensure this is addressed.

5. **`tasks/CONTEXT.md` Domain Vocabulary update —** The current "Exact Instrument Identity" entry describes the tuple as including "optional IBKR `conid`" and should be updated to reflect the post-TP-072 provider-neutral semantics. The `Next Task ID` should also advance from `TP-072` to `TP-073`.

6. **No quality checks to run** — This is a plan review for a documentation step; there is no code to type-check or lint yet.
