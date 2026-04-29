# Task: TP-015 - Define paper-trading workspace architecture and configuration contract

**Created:** 2026-04-29
**Size:** M

## Review Level: 2 (Plan and Code)

**Assessment:** This task establishes the implementation contract for a multi-surface trading feature before backend and frontend code lands. It touches architecture docs, environment configuration, safety guardrails for IBKR paper mode, and verification scripts, but does not connect to real broker services or place orders.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 2, Security: 1, Reversibility: 0

## Canonical Task Folder

```text
tasks/TP-015-paper-trading-workspace-architecture/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Create the architecture and configuration contract for the next ATrade feature slice: a paper-trading workspace that uses official IBKR Gateway APIs safely, exposes mocked market data and trending symbols now, supports real-time updates through SignalR, and prepares the Next.js frontend for TradingView-like charts, watchlists, and future LEAN signal integration. This task is intentionally design/config/test focused so follow-on implementation tasks have one authoritative source for paper-only safety, secrets handling, module boundaries, and UI/data contracts.

## Dependencies

- **None**

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `README.md` — current stack contract and repo status language
- `PLAN.md` — shared milestone state to extend with the paper-trading workspace increment
- `docs/INDEX.md` — documentation index to update for the new architecture document
- `docs/architecture/overview.md` — high-level runtime and infrastructure authority
- `docs/architecture/modules.md` — module map and current backend/frontend/worker boundaries
- `scripts/README.md` — startup and `.env` contract authority
- `.env.example` — committed local configuration template
- `.gitignore` — confirm repo-root `.env` remains ignored
- `frontend/package.json` — current frontend dependency baseline for chart-library decision context

## Environment

- **Workspace:** Project root
- **Services required:** None. This task must not require Docker, IBKR credentials, the IBKR Gateway, Postgres, TimescaleDB, Redis, NATS, or Next.js runtime startup.

## File Scope

> The orchestrator uses this to avoid merge conflicts. Follow-on paper-trading tasks intentionally overlap these docs so they serialize after this contract lands.

- `docs/architecture/paper-trading-workspace.md` (new)
- `docs/INDEX.md`
- `docs/architecture/overview.md`
- `docs/architecture/modules.md`
- `scripts/README.md`
- `.env.example`
- `README.md`
- `PLAN.md`
- `tests/apphost/paper-trading-config-contract-tests.sh` (new)

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Preflight

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Confirm `docs/INDEX.md` currently has no paper-trading workspace architecture document
- [ ] Confirm `.env.example` contains only the existing local port contract before adding new placeholders

### Step 1: Add the paper-trading workspace architecture document

- [ ] Create `docs/architecture/paper-trading-workspace.md` with required frontmatter (`status`, `owner`, `updated`, `summary`, `see_also`)
- [ ] Document backend architecture for IBKR Gateway authentication/session status, market data streaming, and order simulation while explicitly forbidding real trades
- [ ] Document frontend/backend/data separation: Next.js UI, C# API/modules/workers, TimescaleDB/Redis/NATS/SignalR data flow, and user preferences storage choices
- [ ] Record the charting-library decision: prefer `lightweight-charts` for the open-source MVP; do not use the proprietary TradingView Charting Library unless licensing approval is obtained
- [ ] Document mocked trending logic now (volume spikes, price momentum, volatility, news-sentiment placeholder) and future LEAN signal integration as a seam, not a first-slice dependency

**Artifacts:**
- `docs/architecture/paper-trading-workspace.md` (new)

### Step 2: Define the paper-only `.env` configuration contract

- [ ] Extend `.env.example` with safe placeholder variables for the IBKR Gateway URL/image/port, paper account mode, paper account identifier, broker feature enablement, and frontend API base URL
- [ ] Ensure the defaults are safe: broker integration disabled unless explicitly enabled, `Paper` mode only, no live-trading flag enabled, no real account IDs, no usernames, no passwords, and no tokens committed
- [ ] Update `scripts/README.md` so the local configuration contract explains which values belong in ignored `.env` and why secrets must never be committed
- [ ] Confirm `.gitignore` still ignores repo-root `.env`; update only if the ignore rule is missing

**Artifacts:**
- `.env.example` (modified)
- `scripts/README.md` (modified)
- `.gitignore` (modified only if required)

### Step 3: Wire the architecture into active repository docs and planning

- [ ] Add the new architecture document to `docs/INDEX.md` as `active`
- [ ] Update `docs/architecture/overview.md` with a concise paper-trading workspace note that preserves the existing Aspire/modular-monolith contract
- [ ] Update `docs/architecture/modules.md` with planned paper-trading responsibilities for IBKR, market data, frontend charts, and future LEAN signal seams without overstating implementation status
- [ ] Update `README.md` only if the user-facing stack/current-status description would otherwise miss the staged paper-trading feature direction
- [ ] Update `PLAN.md` so the staged paper-trading workspace increment is visible as the next shared milestone

**Artifacts:**
- `docs/INDEX.md` (modified)
- `docs/architecture/overview.md` (modified)
- `docs/architecture/modules.md` (modified)
- `README.md` (modified if affected)
- `PLAN.md` (modified)

### Step 4: Add configuration-contract verification

- [ ] Create `tests/apphost/paper-trading-config-contract-tests.sh`
- [ ] Verify the new architecture document exists, has required frontmatter, and is indexed as active
- [ ] Verify `.env.example` contains only safe placeholders for IBKR paper-mode configuration and does not contain real-looking credentials or live-trading defaults
- [ ] Verify the docs mention `lightweight-charts`, SignalR, mocked trending factors, future LEAN integration, and paper-only/no-real-trades guardrails
- [ ] Run targeted test: `bash tests/apphost/paper-trading-config-contract-tests.sh`

**Artifacts:**
- `tests/apphost/paper-trading-config-contract-tests.sh` (new)

### Step 5: Testing & Verification

> ZERO test failures allowed. This step runs the full available repository verification suite as the quality gate.

- [ ] Run FULL test suite: `dotnet build ATrade.sln --nologo --verbosity minimal && bash tests/start-contract/start-wrapper-tests.sh && bash tests/scaffolding/project-shells-tests.sh && bash tests/apphost/api-bootstrap-tests.sh && bash tests/apphost/accounts-feature-bootstrap-tests.sh && bash tests/apphost/frontend-nextjs-bootstrap-tests.sh && bash tests/apphost/apphost-infrastructure-manifest-tests.sh && bash tests/apphost/apphost-worker-resource-wiring-tests.sh && bash tests/apphost/local-port-contract-tests.sh && bash tests/apphost/paper-trading-config-contract-tests.sh && bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Confirm `apphost-infrastructure-runtime-tests.sh` passes or cleanly skips when no Docker-compatible engine is available
- [ ] Fix all failures
- [ ] Build passes: `dotnet build ATrade.sln --nologo --verbosity minimal`

### Step 6: Documentation & Delivery

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged in STATUS.md

## Documentation Requirements

**Must Update:**
- `docs/architecture/paper-trading-workspace.md` — new authoritative architecture/configuration contract for this feature family
- `docs/INDEX.md` — index the new document as active
- `docs/architecture/overview.md` — add the paper-trading workspace direction without changing core topology
- `docs/architecture/modules.md` — align module responsibilities and future LEAN seam
- `scripts/README.md` — document new `.env` placeholders and secret-handling rules
- `.env.example` — add safe paper-mode placeholders only
- `PLAN.md` — add the staged paper-trading workspace milestone

**Check If Affected:**
- `README.md` — update only if current-status or stack-contract text becomes stale
- `.gitignore` — update only if repo-root `.env` is not ignored

## Completion Criteria

- [ ] A new indexed active architecture doc defines the paper-trading workspace, safety model, data flow, chart-library choice, trending logic, and future LEAN seam
- [ ] `.env.example` contains safe IBKR paper-mode and frontend API placeholders with no real secrets and no live-trading defaults
- [ ] Verification script proves the doc/config contract is present and safe
- [ ] Active docs and `PLAN.md` clearly stage follow-on implementation work without claiming the feature is already complete

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `feat(TP-015): complete Step N — description`
- **Bug fixes:** `fix(TP-015): description`
- **Tests:** `test(TP-015): description`
- **Hydration:** `hydrate: TP-015 expand Step N checkboxes`

## Do NOT

- Add live IBKR credentials, account numbers, tokens, usernames, or passwords to committed files
- Enable real trading or live-account behavior in defaults, examples, docs, or tests
- Use unofficial IBKR broker SDKs or undocumented Gateway behavior as the architectural baseline
- Add real market data providers, LEAN runtime dependencies, database migrations, or frontend chart implementation in this architecture task
- Use the proprietary TradingView Charting Library without explicit licensing approval
- Load docs not listed in "Context to Read First" unless a missing prerequisite is discovered and recorded

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
