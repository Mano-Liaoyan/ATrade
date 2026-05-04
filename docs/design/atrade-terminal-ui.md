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
