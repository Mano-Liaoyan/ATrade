---
status: draft
owner: maintainer
updated: 2026-05-14
summary: PRD for annotation-driven ATrade frontend workspace responsiveness, copy reduction, status consolidation, backtest usability, and scroll ownership improvements.
see_also:
  - ../INDEX.md
  - ../design/atrade-terminal-ui.md
  - ../architecture/paper-trading-workspace.md
  - ../architecture/provider-abstractions.md
  - ../architecture/backtesting.md
---

# PRD: Frontend Workspace Annotation Response

## Problem Statement

ATrade's current paper workspace is functionally broad, but several annotated browser surfaces feel slower, denser, and more explanatory than a commercial finance workstation should. The chart, analysis, status, help, backtest, nav rail, and scroll behavior expose too much tutorial copy, duplicate status information, cramped metadata, slow or misleading loading affordances, clipped collapsed rail icons, and wheel-scroll traps inside internal regions.

Users need the workspace to feel immediate, precise, and truthful. Chart and SignalR status should report state quickly without duplicate indicators or verbose explanations. Chart loading should favor instant cached render and clear stale/refresh/provider state, not fake bars. Backtesting should feel like a usable workflow instead of a compact form dump. Internal scrolling should be predictable across latest stable desktop Safari, Firefox, Chrome, and Edge.

## Solution

Build a focused frontend workspace polish and responsiveness pass that keeps all browser data behind `ATrade.Api`, preserves provider-neutral contracts, and removes excess explanatory copy from the main workspace. The user-facing result should be a quieter, faster-feeling ATrade terminal:

- one top-right SignalR/status indicator with instant initial state;
- chart footer and workspace copy reduced to necessary labels, with useful identity/source detail moved into hover affordances near the stock ID and chart legend identity area;
- provider-neutral, SignalR, status, help, and workspace explanations shortened to operational labels and compact unavailable states;
- summary metadata spacing fixed wherever label/value pairs run together;
- collapsed module rail icons centered exactly in their hit targets at every supported desktop viewport;
- backtest workspace reorganized into a clearer, more user-friendly flow;
- chart response path optimized for cache-first, instant cached render, skeleton/stale-while-refresh behavior, and truthful 429/503/provider/cache states;
- internal scroll regions consuming wheel input first, then chaining to workspace/global scroll only at their ends.

This PRD is planning-only. It creates no Taskplane artifacts and does not authorize implementation by itself.

## User Stories

1. As a paper-workspace user, I want SignalR status to appear immediately, so that I know whether live updates are connected without waiting on a slow status check.
2. As a paper-workspace user, I want exactly one SignalR/status indicator in the top-right workspace corner, so that connection state is not duplicated or contradictory.
3. As a chart user, I want chart status copy to be concise, so that the chart remains the primary focus.
4. As a chart user, I want source and identity details available on hover near the stock ID or chart legend identity area, so that I can inspect details only when needed.
5. As a chart user, I want cached candles to render instantly when they are fresh enough, so that opening a chart feels responsive.
6. As a chart user, I want stale cached data to remain visibly labeled while refresh is attempted, so that responsiveness does not hide provider truth.
7. As a chart user, I want 429, 503, provider-unavailable, provider-not-configured, authentication-required, and empty-candle states to be explicit, so that ATrade never implies fake market data.
8. As a chart user, I want skeleton or loading states that preserve chart dimensions, so that the chart workspace does not jump or collapse while data loads.
9. As a chart user, I want the selected Exact Instrument Identity to remain visible but compact, so that same-symbol instruments from different markets stay distinguishable.
10. As a search/watchlist user, I want provider, market, exchange, currency, and asset-class identity to remain available without long explanatory paragraphs, so that rows stay scannable.
11. As a workspace user, I want dense explanatory/tutorial text removed from analysis, status, help, chart, and provider-state surfaces, so that the product feels like a terminal rather than onboarding docs.
12. As a workspace user, I want disabled and unavailable modules to show short honest state labels, so that I understand availability without reading long guidance.
13. As a workspace user, I want summary label/value metadata to have consistent spacing, so that labels and values do not visually run together.
14. As a workspace user, I want metadata spacing fixed everywhere the pattern appears, so that chart, analysis, status, help, backtest, and monitor surfaces feel polished.
15. As a keyboard user, I want the collapsed rail icon buttons to retain clear focus and target geometry, so that icon-only navigation remains accessible.
16. As a collapsed-rail user, I want icons centered vertically and horizontally regardless of viewport height, so that the rail does not look clipped or broken.
17. As a desktop user, I want late-list rail entries such as NODE and ORDERS to remain reachable, so that disabled modules do not disappear below the viewport.
18. As a backtest user, I want the backtest page to guide me through capital, symbol, strategy, status, history, detail, and comparison in a humane order, so that I can create and inspect saved backtest runs confidently.
19. As a backtest user, I want fewer dense form clusters, so that the primary action and required inputs are obvious.
20. As a backtest user, I want strategy, range, cost, slippage, benchmark, and capital information grouped by task, so that I can understand what will be saved before creating a run.
21. As a backtest user, I want live status to stay visible without duplicating global SignalR state, so that I can track the selected run and understand streaming fallback.
22. As a backtest user, I want failed, cancelled, queued, running, and completed runs to remain truthful, so that comparison never includes fake or incomplete result envelopes.
23. As an analysis user, I want no-engine and runtime-unavailable states to be concise but explicit, so that I know whether LEAN or another provider is configured.
24. As a status user, I want operational status grouped around API, broker/iBeam, market-data cache, analysis runtime, and backtest streaming, so that status is useful without paragraphs of explanation.
25. As a help user, I want help content to behave like a compact reference, so that it does not read like product documentation embedded in the app.
26. As a provider-aware user, I want `timescale-cache:{originalSource}` and provider source metadata available in compact labels/tooltips, so that cache provenance remains inspectable.
27. As a user opening a chart after a full AppHost reboot, I want fresh Timescale cache rows to render quickly when available, so that restart does not force unnecessary provider waits.
28. As a user opening a chart during IBKR/iBeam outage, I want fresh cache hits to render with cache labels and missing fresh data to show unavailable state, so that the UI remains truthful.
29. As a user opening a chart during provider rate limiting, I want the UI to distinguish rate-limit/provider failure from no data, so that I know whether retry may help.
30. As a user scrolling inside a table, detail panel, chart workspace, help/status page, or backtest section, I want wheel input to scroll that internal region first, so that the pointer position controls the expected content.
31. As a user at the end of an internal scroll region, I want wheel input to chain to the next owning workspace/global scroll region, so that scrolling does not feel trapped.
32. As a Safari desktop user, I want visible app-owned or explicitly styled scroll affordances where reachability matters, so that hidden native scrollbars do not hide content.
33. As a Firefox desktop user, I want internal scrollbars to remain visible and styled consistently, so that scroll ownership is clear.
34. As a Chrome or Edge desktop user, I want horizontal and vertical overflow regions to expose usable tracks/thumbs, so that wide identity/action columns remain reachable.
35. As an ATrade maintainer, I want frontend regression coverage for status consolidation, copy reduction, metadata spacing, rail centering, chart states, backtest layout, and wheel chaining, so that annotations do not regress.
36. As an ATrade maintainer, I want any durable code/runtime implementation to update active docs in the same change, so that `docs/INDEX.md` remains the documentation discovery layer.
37. As an ATrade maintainer, I want browser-visible data to stay behind `ATrade.Api`, so that frontend polish does not bypass provider-neutral contracts.
38. As an ATrade maintainer, I want no fake/synthetic bars or demo backtest results introduced, so that provider unavailable states remain honest.
39. As an ATrade maintainer, I want no live trading or order placement behavior added, so that the paper-only safety contract remains intact.
40. As an ATrade maintainer, I want secrets, account identifiers, gateway URLs, tokens, cookies, and runtime internals redacted from UI, logs, tests, and docs, so that polish work does not leak sensitive data.

## Implementation Decisions

- Modify the frontend terminal shell, top-right status area, module rail, workspace layout, and scroll primitives as the primary UI ownership boundary.
- Consolidate SignalR/connection display into one top-right indicator. Remove duplicate SignalR indicators from module bodies unless they describe a specific run or stream in compact local terms.
- Make the SignalR status model initialize synchronously from known client state, then refine after hub connection attempts and HTTP fallback checks. The initial render must not block on a slow status check.
- Preserve `SignalR-to-HTTP fallback` as a canonical behavior. UI may show fallback state, but must not inflate it into explanatory paragraphs.
- Reduce chart footer notes to required operational labels only. Move detailed source, range, Exact Instrument Identity, cache freshness, and provider metadata into hover details attached to the stock ID or chart legend identity area.
- Keep `Exact Instrument Identity` canonical: provider, provider symbol id, symbol, exchange, currency, and asset class. IBKR `conid` remains provider metadata / provider symbol id alias, not a separate identity dimension.
- Remove or sharply shorten tutorial/explanatory copy across chart, analysis, status, help, provider-neutral endpoint, SignalR, workspace-description, and disabled-module surfaces.
- Preserve honest unavailable-state copy. Copy reduction must not hide `provider-not-configured`, `provider-unavailable`, `authentication-required`, `analysis-engine-not-configured`, `analysis-engine-unavailable`, empty candles, rate limits, or storage failures.
- Fix summary metadata label/value spacing through a reusable display pattern where possible, instead of one-off spacing patches across modules.
- Center collapsed rail icons through stable button geometry, not fragile text/layout offsets. Icons must remain centered with visible focus states and accessible labels/tooltips.
- Keep rail overflow reachable through rail-owned scrolling and visible/custom scroll affordances for late-list modules.
- Rework the backtest workspace into task-oriented sections: effective capital, selected instrument, strategy setup, advanced cost/benchmark settings, create action, live selected-run status, saved history, detail, and completed-run comparison.
- Keep backtest browser interactions limited to `ATrade.Api` contracts for paper capital, saved runs, retry/cancel, detail/list, and `/hubs/backtests`.
- Preserve `saved backtest run`, `paper-capital source`, and provider-neutral saved-run identity language in backtest UI and docs.
- Do not add custom code, export controls, optimization controls, order controls, order routing, live trading, or synthetic demo runs.
- Improve chart responsiveness through a cache-first/stale-while-refresh product path: render fresh cached Timescale candles immediately when available, preserve labeled stale content while refreshing when safe, and show skeletons/placeholders that keep chart layout stable when no usable candles exist yet.
- Preserve `Timescale cache-aside` semantics. Fresh persisted rows may serve as successful cache-backed data; stale, mismatched, or missing rows must not be promoted to fresh success when provider refresh fails.
- Treat 429 and 503 as first-class user-facing states in chart loading and market-data source UI. They should remain truthful and retry-friendly without dumping raw provider/runtime details.
- Preserve `lightweight-charts` as the open-source charting baseline. Do not introduce proprietary TradingView Charting Library dependency.
- Implement wheel ownership through shared scroll primitives or hooks where practical: internal scroll areas consume wheel deltas while scrollable; wheel events chain only when the region is at the relevant edge.
- Preserve full-viewport desktop app behavior. Page-level scrolling may remain disabled only if every overflowing rail/workspace/panel/table/module region owns visible reachable scroll.
- Active documentation updates are required in any later durable implementation change, especially terminal UI, paper workspace, provider abstractions, and backtesting docs.
- No production code, tests, schema, or UI edits are part of this PRD creation step.

## Testing Decisions

- Good tests should verify external behavior and browser-visible outcomes, not implementation details or CSS class names unless the class name is itself a documented contract.
- Frontend regression tests should cover one top-right SignalR/status indicator and absence of duplicate SignalR status text elsewhere.
- Frontend tests should assert status appears immediately or from deterministic initial state without waiting on slow remote checks.
- Chart tests should cover fresh cache render, stale-while-refresh labeling, provider 429/503/unavailable states, empty candles, and no synthetic bars.
- Chart tests should cover compact footer copy plus hover-accessible source/Exact Instrument Identity details near stock ID or legend identity area.
- Copy tests should cover removal of dense explanatory/tutorial paragraphs from chart, analysis, status, help, provider-neutral endpoint, and workspace description surfaces while preserving concise unavailable-state labels.
- Metadata tests should cover repeated label/value summary patterns across chart, analysis, status, help, backtest, and monitor surfaces.
- Rail tests should cover collapsed icon centering, focus states, accessible labels/tooltips, viewport-height variation, and reachability of late-list modules.
- Backtest workspace tests should cover task-oriented layout, required inputs, advanced settings disclosure or grouping, live selected-run status, history/detail, comparison eligibility, cancel/retry, and no order/export/optimization controls.
- Scroll tests should cover wheel consumption within internal scroll regions and chaining at scroll boundaries for workspace, rail, market table, detail panel, chart, analysis, backtest, status, help, and disabled module content.
- Cross-browser validation should remain focused on latest stable desktop Safari, Firefox, Chrome, and Edge. Mobile work is limited to preserving existing fallbacks.
- Existing prior art includes frontend terminal regression, chart visibility, chart watchlist default, market monitor scrollbar, module rail icon/collapse, backtest workspace, backtest comparison, route architecture, and layout visibility tests.
- Backend/API tests may be needed only if chart responsiveness requires contract changes for cache freshness, source metadata, rate-limit classification, or response timing. Those tests should assert provider-neutral payloads and no secret/account/gateway leakage.
- Timescale/cache tests should assert cache-first behavior only through `ATrade.Api` contracts and `Timescale cache-aside` semantics, not by letting the browser read TimescaleDB directly.
- SignalR tests should assert `SignalR-to-HTTP fallback` behavior and safe status projection without raw provider/runtime details.
- Documentation verification should ensure any later implementation updates active docs referenced through `docs/INDEX.md`.

## Out of Scope

- No implementation in this PRD step.
- No Taskplane packets, `tasks/TP-*` folders, or Taskplane state edits.
- No production code, test, schema, API, or UI edits in this PRD step.
- No fake market bars, synthetic candles, demo chart data, fake analysis signals, fake backtest results, or mock production fallback data.
- No browser direct access to Postgres, TimescaleDB, Redis, NATS, IBKR/iBeam, LEAN, or provider runtimes.
- No live trading, order placement, order tickets, buy/sell controls, staged order submission, broker routing, or real order behavior.
- No secrets, IBKR credentials, account identifiers, gateway URLs with sensitive values, tokens, cookies, session identifiers, LEAN workspace paths, raw provider commands, or direct bars in UI, docs, tests, logs, or persisted browser state.
- No proprietary TradingView Charting Library adoption.
- No mobile optimization beyond preserving existing responsive fallbacks.
- No change to canonical routes, retired `/symbols/{symbol}` behavior, or provider-neutral Exact Instrument Identity semantics except where a later implementation explicitly preserves compatibility while improving UI.
- No PRD-created implementation issues. A later issue-slicing agent may break this PRD into implementation work.

## Further Notes

- UX target is commercial-feeling responsiveness through truthful cache-first rendering, stable skeletons, and compact source labels, not fake or hidden data.
- Canonical project terms to preserve in implementation issues: `Exact Instrument Identity`, `provider-neutral contracts`, `Timescale cache-aside`, `SignalR-to-HTTP fallback`, `saved backtest run`, and `paper-capital source`.
- Likely touched modules in later implementation: frontend terminal shell, module rail, workspace layout/scroll primitives, chart workspace/legend/status copy, SignalR status model, market-data cache/performance contracts, `ATrade.Api` market-data response handling if needed, Timescale cache-aside behavior if needed, analysis/status/help copy surfaces, backtest workspace layout/forms, frontend browser/regression tests, and active documentation.
