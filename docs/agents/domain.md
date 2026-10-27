# Domain Docs

How the engineering skills use the domain documentation of this repository.

## Layout

ATrade has no central project context file and no document index.

- `GLOSSARY.md` holds the terms.
- `docs/architecture.md` is the architecture specification and the
  implementation authority. Sections split out by capability are in
  `docs/architecture/`.
- `docs/adr/` holds decisions that are hard to reverse, when they exist.
- The plan is in GitHub Issues.

## Before exploring, read these

- `GLOSSARY.md`
- The sections of `docs/architecture.md` that touch the area
- Any relevant ADRs under `docs/adr/`, if that directory exists

If an ADR directory or a topic does not exist, continue without a message. Do
not create domain or ADR files in advance. Create or update them only when a
skill workflow resolves a term or a decision.

## Use the project vocabulary

When output names a domain concept, use the terms in `GLOSSARY.md` and
`docs/architecture.md`, for example instrument, bar, watchlist, strategy
version, backtest, forward test, paper order, paper capital.

If a concept is missing or not clear, call it out as a domain-language gap to
resolve during the grilling loop.

## Flag ADR conflicts

If output contradicts an existing ADR, say so explicitly. Do not silently
override it:

> _Contradicts ADR-0007 — but worth reopening because..._
