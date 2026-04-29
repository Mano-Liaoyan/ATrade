# Task: TP-002 — Architecture and Module Docs

**Created:** 2026-04-23
**Size:** M

## Review Level: 1 (Light)

**Assessment:** Durable documentation change affecting agent read order and `docs/INDEX.md`. Pure docs, no code, fully reversible — but authoritative for future implementation work.
**Score:** 2/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 0

## Canonical Task Folder

```
tasks/TP-002-architecture-module-docs/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Author the first implementation-facing architecture and module docs for the new
ATrade codebase, as required by the open milestone in `PLAN.md`:

> Author the first implementation-facing architecture and module docs for the new codebase

The repo is currently in governance-first bootstrap mode with no implementation
docs beyond the top-level contract files. This task adds the minimum set of
`active` docs an engineer or agent needs to understand the target architecture
before `src/`, `workers/`, and `frontend/` are scaffolded.

## Scope

Produce two new documents under `docs/`:

1. `docs/architecture/overview.md` — high-level architecture for the target
   modular monolith: .NET 10 backend, Next.js frontend, Aspire 13.2
   orchestrator, and the `Postgres`, `TimescaleDB`, `Redis`, `NATS`
   infrastructure stack called out in `README.md`. Must describe the role of
   each component and how `start run` ties them together through Aspire
   AppHost.
2. `docs/architecture/modules.md` — module map aligned with the repository
   structure in `README.md` (`src/`, `workers/`, `frontend/`). For each
   planned module, record: purpose, primary responsibilities, expected
   dependencies, and the broker/data focus for the first phase (`IBKR`,
   `Polygon`).

Both documents must:

- Carry the required frontmatter (`status: active`, `owner: architect`,
  `updated: 2026-04-23`, `summary`, `see_also`).
- Cross-link each other and link back to `README.md`, `PLAN.md`, and
  `scripts/README.md`.
- Be explicit that they describe the **target** architecture, not a finished
  implementation, mirroring the tone of `README.md`.

## Dependencies

- **None** — purely additive documentation. Does not block on code scaffolding.

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `docs/INDEX.md`
- `scripts/README.md`

## Environment

- **Workspace:** Project root
- **Services required:** None

## File Scope

- `docs/architecture/overview.md` (new)
- `docs/architecture/modules.md` (new)
- `docs/INDEX.md` (update to index the two new docs)

## Steps

### Step 0: Preflight

- [ ] Read `README.md`, `PLAN.md`, `AGENTS.md`, and `docs/INDEX.md`
- [ ] Confirm `docs/architecture/overview.md` and `docs/architecture/modules.md` do not yet exist
- [ ] Confirm no existing `active` doc already owns this scope

### Step 1: Author `overview.md`

- [ ] Create `docs/architecture/overview.md` with required frontmatter
- [ ] Describe the modular monolith, Aspire 13.2 orchestration, and the `start run` contract
- [ ] Describe each infrastructure component (`Postgres`, `TimescaleDB`, `Redis`, `NATS`) and its role
- [ ] Mark the doc as describing the **target** architecture

### Step 2: Author `modules.md`

- [ ] Create `docs/architecture/modules.md` with required frontmatter
- [ ] Map planned modules under `src/`, `workers/`, and `frontend/`
- [ ] For each module, record purpose, responsibilities, and expected dependencies
- [ ] Call out the `IBKR` and `Polygon` broker/data focus for the first phase

### Step 3: Update `docs/INDEX.md`

- [ ] Add entries for both new documents with `status: active`
- [ ] Ensure `see_also` links resolve

### Step 4: Verification

- [ ] Both new docs have valid frontmatter with all required fields
- [ ] All cross-links resolve to existing files
- [ ] `docs/INDEX.md` lists both new docs
- [ ] No existing `active` docs were silently invalidated

### Step 5: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `docs/INDEX.md`
**Check If Affected:** `README.md` read order, `plans/architect/CURRENT.md`

## Completion Criteria

- [ ] `docs/architecture/overview.md` exists and is `status: active`
- [ ] `docs/architecture/modules.md` exists and is `status: active`
- [ ] Both docs carry complete required frontmatter
- [ ] `docs/INDEX.md` indexes both new docs
- [ ] All cross-links resolve

## Git Commit Convention

- **Implementation:** `docs(TP-002): description`
- **Checkpoints:** `checkpoint: TP-002 description`

## Do NOT

- Scaffold any `src/`, `workers/`, or `frontend/` code — that is a separate milestone
- Reintroduce or promote legacy docs to `active` without architect review
- Mark the new docs anything other than `active`
- Invent infrastructure components not listed in `README.md`

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
