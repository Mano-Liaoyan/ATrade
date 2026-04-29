# Task: TP-006 — Replace the placeholder frontend with the first Next.js slice

**Created:** 2026-04-23
**Size:** M

## Review Level: 2 (Moderate)

**Assessment:** Replaces the placeholder frontend runtime with the first real
Next.js application slice, updates the AppHost-facing bootstrap surface, adds
smoke coverage, and updates active docs. No auth, broker, or market-data logic
is introduced.
**Score:** 4/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-006-nextjs-frontend-bootstrap/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Replace the current placeholder Node HTTP server in `frontend/` with the first
real Next.js application slice while preserving the single-command local startup
contract through Aspire AppHost.

This task should deliver a minimal but genuine Next.js app — enough to prove the
frontend runtime contract, file layout, and AppHost orchestration path —
without pulling in auth, trading features, or broad UI scope.

## Scope

Deliver the smallest real frontend slice:

1. Replace the placeholder `frontend/server.js` bootstrap with a minimal Next.js app.
2. Keep `npm run dev` as the AppHost entrypoint for the frontend resource.
3. Provide a visible home page that shell smoke tests can verify.
4. Add repo-local smoke coverage for direct frontend startup and the AppHost path.
5. Update active docs so they no longer describe the frontend as a plain Node placeholder.

## Dependencies

- **None**

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `docs/INDEX.md`
- `docs/architecture/overview.md`
- `docs/architecture/modules.md`
- `scripts/README.md`
- `frontend/package.json`
- `frontend/server.js`
- `src/ATrade.AppHost/Program.cs`
- `tests/start-contract/start-wrapper-tests.sh`
- `tests/apphost/api-bootstrap-tests.sh`

## Environment

- **Workspace:** Project root
- **Services required:** None before implementation; frontend startup is part of verification

## File Scope

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/server.js` (remove/replace)
- `frontend/app/` (new)
- `frontend/next-env.d.ts` (new)
- `frontend/tsconfig.json` (new)
- `frontend/next.config.*` (new if needed)
- `src/ATrade.AppHost/Program.cs` (if needed)
- `tests/apphost/frontend-nextjs-bootstrap-tests.sh` (new)
- `tests/start-contract/start-wrapper-tests.sh`
- `scripts/README.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `README.md`
- `plans/senior-engineer/CURRENT.md` (if affected)

## Steps

### Step 0: Preflight

- [ ] Read the current frontend, AppHost, test, and architecture files listed above
- [ ] Confirm `frontend/` is still the placeholder Node server and not yet a Next.js app
- [ ] Confirm the current AppHost frontend resource still targets `npm run dev`

### Step 1: Scaffold the Next.js app

- [ ] Convert `frontend/` into a minimal Next.js application
- [ ] Keep `npm run dev` as the frontend entrypoint
- [ ] Add the smallest necessary Next.js config and app files
- [ ] Replace the placeholder server with a real page at `/`
- [ ] Make the home page expose stable visible text markers that a shell smoke test can assert

### Step 2: Keep AppHost orchestration working

- [ ] Update `src/ATrade.AppHost/Program.cs` only as needed to keep the frontend resource launching correctly through Aspire
- [ ] Preserve the existing API + frontend local bootstrap graph
- [ ] Do not add unrelated infra resources or backend feature modules in this task

### Step 3: Add smoke coverage

- [ ] Create `tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- [ ] Verify the frontend can be started directly and serves the expected home-page markers
- [ ] Update `tests/start-contract/start-wrapper-tests.sh` so it reflects the Next.js-based frontend instead of the old `server.js` placeholder contract

### Step 4: Update docs

- [ ] Update `scripts/README.md` so the bootstrap slice describes a real Next.js frontend
- [ ] Update `docs/architecture/modules.md`
- [ ] Update `docs/architecture/overview.md` if its current-slice note changes
- [ ] Update `README.md` if the current-status wording changes

### Step 5: Verification

- [ ] `bash tests/apphost/frontend-nextjs-bootstrap-tests.sh`
- [ ] `bash tests/start-contract/start-wrapper-tests.sh`
- [ ] `dotnet build ATrade.sln`
- [ ] `timeout 20s dotnet run --project src/ATrade.AppHost/ATrade.AppHost.csproj`
- [ ] `timeout 20s ./start run`

### Step 6: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `scripts/README.md`, `docs/architecture/modules.md`
**Check If Affected:** `docs/architecture/overview.md`, `README.md`, `plans/senior-engineer/CURRENT.md`

## Completion Criteria

- [ ] `frontend/` is a real Next.js app rather than the placeholder Node server
- [ ] `npm run dev` still works as the AppHost entrypoint
- [ ] The home page serves stable text markers verified by the new smoke test
- [ ] AppHost still launches the API and frontend together
- [ ] Active docs reflect the new current bootstrap slice

## Git Commit Convention

- **Implementation:** `feat(TP-006): description`
- **Checkpoints:** `checkpoint: TP-006 description`

## Do NOT

- Add auth flows, trading features, market-data views, or dashboard complexity in this slice
- Introduce a component library or design system unless it is required for a minimal Next.js bootstrap
- Add infrastructure resources (`Postgres`, `TimescaleDB`, `Redis`, `NATS`) here
- Change the repo-local startup contract away from `start run`

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
