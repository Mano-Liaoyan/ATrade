---
status: active
owner: maintainer
updated: 2026-05-05
summary: Active ATrade paper workspace UI design authority for the direct module/workflow frontend.
see_also:
  - ../INDEX.md
  - ../architecture/paper-trading-workspace.md
  - ../architecture/modules.md
  - ../architecture/provider-abstractions.md
  - ../architecture/analysis-engines.md
  - ../../README.md
  - ../../PLAN.md
---

# ATrade Paper Workspace UI Design Spec

This document is the active design authority for the current Next.js paper
workspace. The historical filename is retained for continuity with the
`TP-045` through `TP-051` reconstruction queue, but the current product surface
is no longer a command-led shell. The UI is a direct
module/workflow workspace: users navigate through the module rail, explicit
market-monitor actions, chart/analysis route state, and HELP/STATUS surfaces.

## Related Active Authorities

- [`paper-trading-workspace.md`](../architecture/paper-trading-workspace.md) —
  paper-only workspace architecture, current frontend/backend contracts,
  watchlist/search/chart/analysis workflow boundaries, and safety rules.
- [`modules.md`](../architecture/modules.md) — modular-monolith ownership map
  for `src/`, `workers/`, and `frontend/` responsibilities.
- [`provider-abstractions.md`](../architecture/provider-abstractions.md) —
  provider-neutral broker, market-data, analysis, identity, and unavailable-state
  contracts the workspace must preserve.
- [`analysis-engines.md`](../architecture/analysis-engines.md) — provider-neutral
  analysis request/result contract and LEAN integration boundary.
- [`README.md`](../../README.md) and [`PLAN.md`](../../PLAN.md) — current runtime
  surface, verification entry points, and active Taskplane queue.

## 1. Authority And Scope

The UI spec governs the first-release visual direction, direct navigation model,
workspace layout, enabled modules, visible-disabled future surfaces, and
implementation constraints for the frontend. Backend API contracts, provider
identity semantics, paper-only guardrails, and unavailable-state behavior remain
governed by the active architecture documents linked above.

Current non-goals:

- Do not reintroduce a command input, command parser, command registry, command
  palette, natural-language router, fuzzy route parser, backend AI command route,
  or broker-command surface under another name.
- Do not restore retired terminal branding, shell headers, or command-first
  product copy.
- Do not remove the module rail or the API-backed HOME, SEARCH, WATCHLIST,
  CHART, ANALYSIS, STATUS, HELP, and visible-disabled module surfaces.

## 2. Clean-Room Visual And Source Guardrails

ATrade may use broad public finance-workstation patterns only as inspiration:
dense dark information hierarchy, keyboard-friendly module navigation,
resizable panels, source/status chips, and multi-panel market context. The
implementation must be an original ATrade design and codebase.

Non-negotiable clean-room rules:

- Do not copy FinceptTerminal source code, component structure, stylesheets,
  assets, screenshots, icons, names, trademarks, branding, or proprietary copy.
- Do not copy Bloomberg Terminal proprietary layouts, screenshots, trademarks,
  brand colors, fonts, iconography, command taxonomies, or any pixel-identical
  composition.
- Do not import, trace, crop, or recreate proprietary screenshots or product
  assets as implementation references.
- Do not make the UI look like an official FinceptTerminal, Bloomberg, IBKR, or
  third-party branded product. The shipped interface must read as ATrade.
- Use only original ATrade components, tokens, copy, icons, and layout
  compositions created inside this repository or from properly licensed open
  source primitives already accepted by the project.
- When in doubt, favor documented ATrade data contracts and product needs over
  visual imitation.

## 3. Product Target Decisions

The selected product target is a provider-backed paper workspace, not a light
reskin of the old paper-trading pages and not a command-first shell.

- **Replacement posture:** current user-facing routes render through
  `ATradeTerminalApp` as a module/workflow workspace. Existing rendering
  components and page CSS remain disposable unless a later task deliberately
  reuses logic behind the module architecture.
- **Runtime target:** ship as a Next.js web workspace first, served by the
  existing AppHost/Next.js frontend integration and browser-facing `ATrade.Api`
  contracts.
- **Future wrapper compatibility:** keep state and interactions friendly to a
  later desktop wrapper by avoiding browser-only assumptions in core workspace
  state, module registry behavior, layout persistence keys, and keyboard/focus
  handling.
- **Primary form factor:** optimize for desktop and laptop screens where dense
  multi-panel market context is valuable.
- **Mobile posture:** provide a simplified responsive fallback for narrow
  screens. Mobile may collapse rails and stack panels; it is not expected to
  deliver the full multi-panel workspace experience in the first release.

## 4. First-Release Module Model

First-release modules must be backed by current ATrade API and frontend workflow
contracts. They may reorganize and restyle those workflows, but they must not
invent backend data, bypass `ATrade.Api`, or imply functionality that the current
backend cannot supply.

### 4.1 Enabled Modules

| Module | First-release responsibility | Current contract backing it |
| ------ | ---------------------------- | --------------------------- |
| `HOME` | Landing workspace with market status, paper-only safety summary, provider state, trending entry points, recent watchlist context, and shortcuts into chart/search/analysis workflows. | `GET /health`, `GET /api/accounts/overview`, `GET /api/broker/ibkr/status`, `GET /api/market-data/trending`, current frontend workflow modules. |
| `SEARCH` | Bounded/ranked stock search with exact provider/market identity badges, provider unavailable/authentication-required copy, and actions to chart or pin an exact instrument. | `GET /api/market-data/search?query=...&assetClass=stock&limit=...` plus `symbolSearchWorkflow`. |
| `WATCHLIST` | Backend-owned watchlist view for exact provider/market pins with pin/unpin/remove, stable `instrumentKey` / `pinKey`, read-only cached fallback copy, and no browser-owned authority. | `GET` / `PUT` / `POST /api/workspace/watchlist`, exact `DELETE /api/workspace/watchlist/pins/{instrumentKey}`, legacy unambiguous `DELETE /api/workspace/watchlist/{symbol}`, and `watchlistWorkflow`. |
| `CHART` | Dense chart workspace for an exact symbol/identity with candlesticks, volume, range controls, source labels, latest updates, and chart-to-analysis handoff. | `GET /api/market-data/{symbol}/candles?range=...`, `GET /api/market-data/{symbol}/indicators?range=...`, optional exact identity query metadata, `/hubs/market-data`, and `symbolChartWorkflow`. |
| `ANALYSIS` | Provider-neutral analysis workspace that lists available engines, runs analysis over market-data bars, and surfaces explicit no-engine or runtime-unavailable states without fake signals. | `GET /api/analysis/engines`, `POST /api/analysis/run`, `ATrade.Analysis` result payloads, optional LEAN provider. |
| `STATUS` | Operational status module for paper-mode broker readiness, provider/cache/source metadata, frontend/API health, and explicit unavailable states. | `GET /health`, `GET /api/broker/ibkr/status`, source metadata on market-data responses, analysis engine metadata. |
| `HELP` | In-product module/workflow reference, safety reminders, provider-state explanations, and direct-navigation guidance. | Static frontend content derived from this spec and active architecture docs; no backend data required. |

Enabled modules share `frontend/lib/terminalModuleRegistry.ts` so rail entries,
module labels, disabled states, and help copy stay consistent.

### 4.2 Visible-Disabled Future Modules

Future modules may appear in the rail and HELP surfaces as disabled entries to
communicate intended product breadth. A disabled module must be visually distinct
from enabled modules, must not be keyboard-selectable as an active workspace,
and must show honest unavailable copy instead of mock data.

| Future module | Disabled-state meaning |
| ------------- | ---------------------- |
| `NEWS` | Coming soon; no committed news provider or news API exists in the current backend. Do not show scraped headlines, stale fixture stories, or invented market narratives. |
| `PORTFOLIO` | Coming soon; no durable positions/P&L portfolio workspace is available beyond current paper account overview/status contracts. Do not synthesize holdings. |
| `RESEARCH` | Coming soon; no research-document ingestion, fundamentals provider, or analyst-rating API is available. Do not ship placeholder analyst opinions. |
| `SCREENER` | Coming soon; current backend supports scanner/trending and bounded symbol search only, not arbitrary multi-factor screen building. |
| `ECON` | Coming soon; no economic calendar, macro series, or central-bank feed is integrated. |
| `AI` | Coming soon; no committed AI assistant, model runtime, tool-use backend, or retrieval contract exists for browser use. |
| `NODE` | Coming soon; no node-graph workflow or visual strategy graph runtime exists in the current frontend scope. |
| `ORDERS` | Explicitly disabled. The current backend has deterministic paper simulation, but this UI forbids order-entry tickets, simulated-submit workflows, and live-trading affordances. |

Disabled modules should use direct unavailable states such as "Not available in
this release", "No provider configured in ATrade yet", or "Orders are disabled
by the paper-only safety contract". They must not display fake tables, sample
positions, placeholder news, example orders, or demo AI output that could be
mistaken for live data.

## 5. Direct Navigation And Workflow Actions

The first-release navigation model is intentionally explicit and deterministic
without a command system.

- The module rail opens `HOME`, `SEARCH`, `WATCHLIST`, `CHART`, `ANALYSIS`,
  `STATUS`, and `HELP` and exposes visible-disabled future modules with honest
  unavailable states.
- The market monitor is the primary workflow handoff surface for search,
  watchlist, and trending rows. Row actions open chart and analysis workspaces
  while preserving exact provider identity when available.
- Symbol routes may initialize `CHART` or `ANALYSIS` directly from route/query
  state, including chart range and exact identity metadata.
- HELP lists enabled modules, visible-disabled modules, workflow actions,
  provider-state meanings, and paper-only safety constraints.
- STATUS surfaces `ATrade.Api`, broker/iBeam/provider, cache/source, and analysis
  runtime states without hiding unavailable conditions.
- Navigation updates focus and status text for accessibility, but it does not
  parse free-form text and it does not send navigation text to a backend AI,
  broker, or order route.

## 6. Workspace Layout And Navigation Behavior

ATrade should present a dense but legible multi-panel paper workspace on
laptop/desktop screens. The layout model should be simple enough for the first
implementation while leaving room for a desktop wrapper later.

### 6.1 Resizable Multi-Panel Workspace

- Use a rectangular workspace frame with a top header region, left module rail,
  central workspace grid, optional context/status rail, and compact status strip.
- The central workspace should support resizable split panels for first-release
  market workflows: for example market monitor + watchlist, chart + indicators,
  chart + analysis, or status/help + context.
- Resizing should use accessible handles, preserve minimum usable panel sizes,
  and avoid overlapping or free-floating windows in the first release.
- Panel content must remain honest about backend state: loading, provider
  not-configured, provider unavailable, authentication required, no analysis
  engine configured, no watchlist pins, and disabled module states each get
  explicit copy.

### 6.2 Layout Persistence

- Persist only non-sensitive UI preferences in browser-local storage, such as
  active enabled module, panel split sizes, collapsed/expanded rail preference,
  and last selected chart range.
- Use an ATrade-owned versioned key namespace such as
  `atrade.terminal.layout.v1` so future migrations can reset safely.
- Treat local layout state as convenience state only. Backend-owned watchlists,
  exact instrument identity, analysis inputs/results intended to roam, account
  state, and any broker/provider data remain API-owned.
- Invalid or stale persisted layout should reset to a documented default instead
  of breaking module navigation.

### 6.3 Module Rail

- The rail lists enabled modules (`HOME`, `SEARCH`, `WATCHLIST`, `CHART`,
  `ANALYSIS`, `STATUS`, `HELP`) first with clear active/focus/keyboard states.
- Visible-disabled future modules may appear below a separator with disabled
  styling, explanatory tooltips/popovers, and no active workspace route.
- Rail labels should use ATrade module names, not third-party product branding.
- The rail may collapse to icons/short codes on laptop screens if tooltips and
  keyboard labels remain available.

### 6.4 Top Header Region

- The top region contains ATrade workspace branding, current product copy,
  paper-only/provider-boundary status, and concise provider-truthful messaging.
- Header copy should reinforce that the browser talks only to `ATrade.Api`,
  provider/runtime unavailable states are expected safe outcomes, and orders are
  disabled.
- The header must not include a command input, command prompt, command grammar,
  or command-first product tagline.

### 6.5 Status Strip

- The strip may show provider/source labels, cache freshness/source metadata,
  selected symbol identity, backend health, and compact navigation status.
- It must not show fabricated price ticks. If SignalR or HTTP market data is
  unavailable, show explicit stale/unavailable labels and retry affordances.
- It must repeat paper-only/no-live-orders safety in compact form when order or
  broker terms appear elsewhere on the screen.

### 6.6 Responsive And Laptop Fallback Rules

- Desktop and laptop layouts are primary; optimize first for approximately
  1280px-wide and larger screens.
- At narrower laptop widths, allow the context rail to collapse under the active
  workspace and allow the module rail to shrink.
- At tablet/mobile widths, collapse to a single-column flow with header, module
  rail/picker, active panel, and status sections stacked vertically.
- Mobile fallback may omit simultaneous multi-panel context; it must still expose
  enabled modules, safety copy, provider unavailable states, and HELP/STATUS
  guidance.

## 7. Visual System Direction

The visual goal is an original ATrade interpretation of a modern institutional
finance workstation: dense, precise, dark, data-forward, and module-friendly. It
should feel closer to contemporary finance workspaces than to a generic SaaS
dashboard, while staying clearly separate from proprietary product identities.

### 7.1 Institutional Characteristics

- **Dark dense panels:** default to a near-black application shell with layered
  graphite/slate panels, subtle dividers, and restrained elevation rather than
  large white cards or marketing-style gradients.
- **High-contrast data hierarchy:** prices, symbols, status labels, timestamps,
  source metadata, and unavailable states should have obvious priority through
  weight, color, spacing, and alignment.
- **Compact typography:** prefer compact sans-serif UI typography with tabular
  numerals, tight line heights for tables, and clear monospace/code treatments
  for symbols, instrument keys, provider/source labels, and route/state chips.
- **Grid/table density:** market lists, watchlists, search results, indicators,
  and status diagnostics should use dense rows, sticky headings where useful,
  right-aligned numeric columns, and scan-friendly separators.
- **Workspace accents:** use amber, cyan, green, and red accents for attention,
  selected/focused states, positive/negative movement, warning/unavailable
  states, and paper-only safety. Accent use must be an original palette, not a
  copied third-party brand palette.
- **Rectangular/resizable paneling:** prefer crisp rectangular regions,
  splitters, rails, source/status chips, and instrument identity chips over
  rounded consumer-card layouts.
- **Non-generic shadcn styling:** avoid unmodified shadcn examples. Components
  should be restyled into ATrade primitives with custom density, focus, color,
  and data-state treatments.

### 7.2 UI Stack Direction

The selected UI stack direction is a shadcn/ui-style component approach using
Tailwind CSS and Radix primitives where they fit the workspace interaction model.

Implementation guidance:

- Use Tailwind tokens/utilities as the styling substrate, but define ATrade
  workspace tokens for shell backgrounds, panel layers, borders, focus rings,
  data-state colors, typography scale, spacing density, and chart/workspace
  surfaces.
- Use Radix primitives for accessible dialogs, popovers, tabs, tooltips, menus,
  separators, scroll areas, and similar behaviors when they reduce custom
  accessibility risk.
- Treat shadcn/ui as a composition pattern and starting implementation style, not
  as a visual identity. Generated/default examples must be heavily restyled.
- Build reusable original ATrade primitives such as workspace frame, module rail,
  resizable panel group, status strip, data table, metric tile, provider-state
  callout, symbol identity chip, and disabled-module callout.
- Preserve keyboard focus visibility and screen-reader labels even when the UI is
  visually dense.

## 8. Frontend Replacement And Reuse Constraints

This queue is authorized to aggressively replace frontend rendering and styling
while preserving the backend/API and workflow contracts that make the current
paper-trading slice honest and safe.

### 8.1 Disposable Frontend Surfaces

- Existing page layouts, visual components, old shell components, and CSS may be
  deleted or rewritten when they conflict with this spec.
- Existing component names do not define the target architecture; the module
  registry, direct workflow actions, layout primitives, and dense data
  components should be designed around this document.
- Existing generic dashboard/card styling is not a compatibility requirement.
- Do not keep old UI solely to avoid churn if it blocks the dense workspace,
  resizable layout model, direct workflow navigation, or original visual system.

### 8.2 Reusable Logic To Preserve When It Fits

- Preserve browser-facing `ATrade.Api` endpoint contracts and provider-neutral
  payload expectations from the active architecture docs.
- Preserve workflow logic that already centralizes backend-aware behavior when it
  fits the workspace architecture: watchlist load/migration/pin/unpin logic,
  symbol search validation/ranking/error copy, chart range normalization/source
  labels, SignalR-to-HTTP fallback, and analysis engine no-configured/unavailable
  handling.
- Preserve exact instrument identity handoff (`provider`, provider symbol id /
  IBKR `conid`, symbol, exchange, currency, asset class, `instrumentKey`, and
  `pinKey`) across search, watchlist, chart, analysis, and status surfaces.
- Reuse types, API clients, data mappers, and tests when they keep provider
  behavior honest; rewrite rendering components and CSS around the workspace
  model.

## 9. Safety And Data-Access Constraints

The workspace reconstruction must preserve the paper-only safety contract and the
browser/backend separation defined by the active architecture docs.

Non-negotiable constraints:

- Do not add order-entry UI in this batch.
- Do not add a simulated-submit workflow, order ticket, staged ticket drawer,
  buy/sell button, order preview, or order confirmation path to the UI.
- Do not add real or live order placement behavior.
- Do not weaken the existing backend live-mode rejection or paper-only defaults.
- Do not let the browser connect directly to Postgres, TimescaleDB, Redis, NATS,
  IBKR/iBeam, LEAN, or any provider runtime.
- All browser-visible data must flow through `ATrade.Api` and its existing
  HTTP/SignalR/provider-neutral contracts.
- Do not commit or display secrets, IBKR credentials, account identifiers,
  tokens, session cookies, gateway URLs that include sensitive values, or hidden
  provider runtime details.
- If provider, analysis, database, SignalR, or runtime dependencies are missing,
  unauthenticated, unavailable, or timed out, render explicit safe unavailable
  states rather than fallback mocks.
- Disabled `ORDERS` surfaces may explain that orders are out of scope and that
  the current architecture remains paper-only; they must not provide controls
  that look executable.
