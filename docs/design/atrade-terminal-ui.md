---
status: active
owner: maintainer
updated: 2026-05-04
summary: Active ATrade Terminal UI design authority for the frontend reconstruction queue.
see_also:
  - ../INDEX.md
  - ../architecture/paper-trading-workspace.md
  - ../architecture/modules.md
  - ../architecture/provider-abstractions.md
  - ../architecture/analysis-engines.md
  - ../../README.md
  - ../../PLAN.md
---

# ATrade Terminal UI Design Spec

This document is the active design authority for the ATrade Terminal frontend
reconstruction queue (`TP-045` through `TP-050`). It translates the current
paper-trading workspace, module map, and provider-neutral API boundaries into an
implementation-ready terminal UI direction for the Next.js frontend.

## Related Active Authorities

- [`paper-trading-workspace.md`](../architecture/paper-trading-workspace.md) —
  paper-only workspace architecture, current frontend/backend contracts,
  watchlist/search/chart/analysis workflow boundaries, and safety rules.
- [`modules.md`](../architecture/modules.md) — modular-monolith ownership map
  for `src/`, `workers/`, and `frontend/` responsibilities.
- [`provider-abstractions.md`](../architecture/provider-abstractions.md) —
  provider-neutral broker, market-data, analysis, identity, and unavailable-state
  contracts the terminal must preserve.
- [`analysis-engines.md`](../architecture/analysis-engines.md) — provider-neutral
  analysis request/result contract and LEAN integration boundary.
- [`README.md`](../../README.md) and [`PLAN.md`](../../PLAN.md) — current runtime
  surface, verification entry points, and active Taskplane queue.

## 1. Authority And Scope

The terminal UI spec governs the first-release visual direction, navigation,
command grammar, workspace layout, enabled modules, visible-disabled future
surfaces, and implementation constraints for the frontend reconstruction. Backend
API contracts, provider identity semantics, paper-only guardrails, and unavailable
state behavior remain governed by the active architecture documents linked above.

## 2. Clean-Room Visual And Source Guardrails

ATrade Terminal may use FinceptTerminal-style public product imagery and
Bloomberg-like command workflows only as broad visual and interaction
inspiration: dense dark finance-terminal information hierarchy, keyboard-first
navigation, command-driven workspace switching, and multi-panel market context.
The implementation must be an original ATrade design and codebase.

Non-negotiable clean-room rules:

- Do not copy FinceptTerminal source code, component structure, stylesheets,
  assets, screenshots, icons, names, trademarks, branding, or proprietary copy.
- Do not copy Bloomberg Terminal proprietary layouts, screenshots, trademarks,
  brand colors, fonts, iconography, command taxonomies beyond generic finance
  workflow concepts, or any pixel-identical composition.
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

The selected product target for this queue is a full frontend reconstruction,
not a light reskin of the existing paper-trading pages.

- **Replacement posture:** rebuild the user-facing frontend around ATrade
  Terminal. Existing rendering components and page CSS are disposable unless a
  later task deliberately reuses logic behind the new terminal architecture.
- **Runtime target:** ship as a Next.js web terminal first, served by the
  existing AppHost/Next.js frontend integration and browser-facing `ATrade.Api`
  contracts.
- **Future wrapper compatibility:** keep the interaction model friendly to a
  later desktop wrapper by avoiding browser-only assumptions in core terminal
  state, command registration, layout persistence keys, and keyboard handling.
- **Primary form factor:** optimize for desktop and laptop screens where dense
  multi-panel market context is valuable.
- **Mobile posture:** provide a simplified responsive fallback for narrow
  screens. Mobile may collapse rails and stack panels; it is not expected to
  deliver the full multi-panel terminal experience in the first release.

## 4. First-Release Module Model

First-release modules must be backed by current ATrade API and frontend workflow
contracts. They may reorganize and restyle those workflows, but they must not
invent backend data, bypass `ATrade.Api`, or imply functionality that the current
backend cannot supply.

### 4.1 Enabled Modules

| Module | First-release responsibility | Current contract backing it |
| ------ | ---------------------------- | --------------------------- |
| `HOME` | Landing workspace with market status, paper-only safety summary, provider state, trending entry points, recent watchlist context, and shortcuts into chart/search/analysis workflows. | `GET /health`, `GET /api/accounts/overview`, `GET /api/broker/ibkr/status`, `GET /api/market-data/trending`, existing frontend home/workflow modules. |
| `SEARCH` | Keyboard-first symbol search for stocks with bounded/ranked results, exact provider/market identity badges, provider unavailable/authentication-required copy, and actions to chart or pin an exact instrument. | `GET /api/market-data/search?query=...&assetClass=stock&limit=...` plus existing `symbolSearchWorkflow` behavior. |
| `WATCHLIST` | Backend-owned watchlist view for exact provider/market pins with pin/unpin/remove, stable `instrumentKey` / `pinKey`, read-only cached fallback copy, and no browser-owned authority. | `GET` / `PUT` / `POST /api/workspace/watchlist`, exact `DELETE /api/workspace/watchlist/pins/{instrumentKey}`, legacy unambiguous `DELETE /api/workspace/watchlist/{symbol}`, and `watchlistWorkflow`. |
| `CHART` | Dense chart workspace for an exact symbol/identity with candlesticks, volume, range controls, source labels, latest updates, and chart-to-analysis handoff. | `GET /api/market-data/{symbol}/candles?range=...`, `GET /api/market-data/{symbol}/indicators?range=...`, optional exact identity query metadata, `/hubs/market-data`, and `symbolChartWorkflow`. |
| `ANALYSIS` | Provider-neutral analysis panel/workspace that lists available engines, runs analysis over market-data bars, and surfaces explicit no-engine or runtime-unavailable states without fake signals. | `GET /api/analysis/engines`, `POST /api/analysis/run`, `ATrade.Analysis` result payloads, optional LEAN provider. |
| `STATUS` | Operational status module for paper-mode broker readiness, provider/cache/source metadata, frontend/API health, and explicit unavailable states. | `GET /health`, `GET /api/broker/ibkr/status`, source metadata on market-data responses, analysis engine metadata. |
| `HELP` | In-product command/module reference, safety reminders, provider-state explanations, and keyboard shortcut guidance. | Static frontend content derived from this spec and active architecture docs; no backend data required. |

Enabled modules should share a single registry in later implementation tasks so
module rail entries, command routing, empty states, and help copy stay
consistent.

### 4.2 Visible-Disabled Future Modules

The terminal may show future modules in the rail, command help, or module switcher
as disabled surfaces to communicate the intended product shape. A disabled module
must be visually distinct from enabled modules, must not be keyboard-selectable as
an active workspace, and must show honest unavailable copy instead of mock data.

| Future module | Disabled-state meaning |
| ------------- | ---------------------- |
| `NEWS` | Coming soon; no committed news provider or news API exists in the current backend. Do not show scraped headlines, stale fixture stories, or invented market narratives. |
| `PORTFOLIO` | Coming soon; no durable positions/P&L portfolio workspace is available beyond current paper account overview/status contracts. Do not synthesize holdings. |
| `RESEARCH` | Coming soon; no research-document ingestion, fundamentals provider, or analyst-rating API is available. Do not ship placeholder analyst opinions. |
| `SCREENER` | Coming soon; current backend supports scanner/trending and bounded symbol search only, not arbitrary multi-factor screen building. |
| `ECON` | Coming soon; no economic calendar, macro series, or central-bank feed is integrated. |
| `AI` | Coming soon; no committed AI assistant, model runtime, tool-use backend, or retrieval contract exists for browser use. |
| `NODE` | Coming soon; no node-graph workflow or visual strategy graph runtime exists in the current frontend scope. |
| `ORDERS` | Explicitly disabled in this reconstruction batch. The current backend has deterministic paper simulation, but this UI spec forbids order-entry tickets, simulated-submit workflows, and live-trading affordances in the terminal queue. |

Disabled modules should use direct unavailable states such as "Not available in
this release", "No provider configured in ATrade yet", or "Orders are disabled
by the paper-only safety contract". They must not display fake tables, sample
positions, placeholder news, example orders, or demo AI output that could be
mistaken for live data. The `ORDERS` disabled-state copy should include the
plain-language sentence: "Orders are disabled by the paper-only safety contract."

## 5. Deterministic First-Release Commands

The command bar is a deterministic router, not a natural-language assistant.
Commands must parse locally, normalize case, trim extra whitespace, and either
route to an enabled module/action or show a stable help/error state. First-release
commands are intentionally small:

| Command | Behavior |
| ------- | -------- |
| `HOME` | Open/focus the `HOME` module. |
| `SEARCH <query>` | Open `SEARCH`, seed the search box with `<query>`, and run the bounded stock search once the query satisfies the current minimum-length rules. Empty `SEARCH` focuses the search module/help state. |
| `CHART <symbol>` | Open `CHART` for the supplied symbol. When exact identity metadata is already available from search/watchlist/trending context, preserve it in route/query state; otherwise use the legacy symbol path and let current backend/provider unavailable states surface honestly. |
| `WATCH` | Open/focus the `WATCHLIST` module. |
| `WATCHLIST` | Alias for `WATCH`; open/focus the `WATCHLIST` module. |
| `ANALYSIS <symbol>` | Open `ANALYSIS` for the supplied symbol and prepare an analysis request using supported chart-range defaults and exact identity metadata when available. Empty `ANALYSIS` opens the module with engine/status help. |
| `STATUS` | Open/focus the `STATUS` module. |
| `HELP` | Open/focus the `HELP` module and list enabled commands, disabled modules, safety constraints, and provider-state meanings. |

Unknown commands must not try fuzzy execution or AI completion in the first
release. They should render deterministic copy such as "Unknown command" plus a
`HELP` shortcut. Disabled module names typed as commands should route to the same
honest unavailable state shown in the rail, not to mock content.

## 6. Workspace Layout And Navigation Behavior

ATrade Terminal should present a dense but legible multi-panel workspace on
laptop/desktop screens. The layout model should be simple enough for the first
implementation while leaving room for a desktop wrapper later.

### 6.1 Resizable Multi-Panel Workspace

- Use a rectangular terminal frame with a top command/header region, left module
  rail, central workspace grid, optional right context/status rail, and bottom or
  low-height status/ticker strip.
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
- Rail labels should use ATrade module names, not third-party terminal product
  branding.
- The rail may collapse to icons/short codes on laptop screens if tooltips and
  keyboard labels remain available.

### 6.4 Top Command/Header Region

- The top region contains the ATrade Terminal mark/name, deterministic command
  input, current module/breadcrumb, paper-only badge, and concise provider status.
- Command input should be keyboard-first, use local deterministic parsing from
  Section 5, and never send raw command text to a backend AI or broker system.
- Header copy should reinforce that the browser talks only to `ATrade.Api` and
  that market/provider unavailable states are expected safe outcomes.

### 6.5 Status/Ticker Strip

- The strip may show provider/source labels, cache freshness/source metadata,
  selected symbol identity, backend health, and a compact watchlist/trending
  ticker derived from current API data.
- It must not show fabricated price ticks. If SignalR or HTTP market data is
  unavailable, show explicit stale/unavailable labels and retry affordances.
- It must repeat paper-only/no-live-orders safety in compact form when order or
  broker terms appear elsewhere on the screen.

### 6.6 Responsive And Laptop Fallback Rules

- Desktop and laptop layouts are primary; optimize first for approximately
  1280px-wide and larger screens.
- At narrower laptop widths, allow the right context rail to collapse under the
  active workspace and allow the module rail to shrink.
- At tablet/mobile widths, collapse to a single-column flow with command/header,
  module picker, active panel, and status sections stacked vertically.
- Mobile fallback may omit simultaneous multi-panel context; it must still expose
  enabled modules, safety copy, provider unavailable states, and deterministic
  command/help guidance.
