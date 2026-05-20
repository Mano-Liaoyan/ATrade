# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout

ATrade does not use a central project context file.

- `docs/INDEX.md` is the documentation discovery layer.
- Active docs listed in `docs/INDEX.md` are implementation authority.
- `docs/adr/` is the ADR location when architectural decisions are added later.

## Before exploring, read these

- `docs/INDEX.md`
- The active docs from `docs/INDEX.md` that touch the area being explored
- Any relevant ADRs under `docs/adr/`, if that directory exists

If an ADR directory or topic-specific doc does not exist, proceed silently. Do not create domain or ADR files upfront; create or update them only when a skill workflow resolves durable terminology or decisions.

## Use the project vocabulary

When output names a domain concept, use the terms already present in active architecture, design, process, and tooling docs. Prefer project language such as Exact Instrument Identity, paper-capital source, saved backtest run, Compose-managed infrastructure, AppHost, and provider-neutral contracts over new synonyms.

If the concept needed for a proposal is missing or fuzzy, call that out as a domain-language gap to resolve during the grilling loop.

## Flag ADR conflicts

If output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 — but worth reopening because..._
