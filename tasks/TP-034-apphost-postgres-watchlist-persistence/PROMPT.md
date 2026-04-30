# Task: TP-034 - Persist AppHost Postgres watchlists across application reboot

**Created:** 2026-04-30
**Size:** M

## Review Level: 1 (Plan Only)

**Assessment:** This fixes local runtime durability for the AppHost-managed Postgres resource and adds focused restart coverage. It follows the existing Aspire/Postgres pattern and does not change auth, broker behavior, or watchlist API semantics.
**Score:** 3/8 — Blast radius: 1, Pattern novelty: 1, Security: 0, Reversibility: 1

## Canonical Task Folder

```text
tasks/TP-034-apphost-postgres-watchlist-persistence/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (created by the orchestrator runtime)
└── .DONE       ← Created when complete
```

## Mission

Fix the watchlist disappearing after an application reboot by making the AppHost-managed Postgres data directory durable across full `start run` stop/start cycles. Existing watchlist repository/API code already persists pins when the same Postgres database stays alive; this task must close the local Aspire runtime gap where the `postgres` container can be recreated without a persistent data volume. The frontend must continue to use backend watchlist APIs, and browser `localStorage` must remain non-authoritative.

## Dependencies

- **None**

## Context to Read First

> Only load these files unless implementation reveals a directly related missing prerequisite. Do **not** read, print, or commit the ignored repo-root `.env` file.

**Tier 2 (area context):**
- `tasks/CONTEXT.md`

**Tier 3 (load only if needed):**
- `docs/architecture/paper-trading-workspace.md` — backend-owned watchlist persistence contract
- `docs/architecture/modules.md` — AppHost/Workspaces/API/frontend ownership
- `docs/architecture/overview.md` — AppHost infrastructure graph summary
- `scripts/README.md` — local `.env` and `start run` contract
- `.env.template` — committed non-secret defaults only; never read ignored `.env`
- `src/ATrade.AppHost/Program.cs` — current `postgres` resource declaration
- `src/ATrade.AppHost/PaperTradingEnvironmentContract.cs` — pattern for merged local contract parsing if volume-name settings are added
- `src/ATrade.Workspaces/*` — current watchlist schema/repository behavior
- `src/ATrade.Api/Program.cs` — watchlist endpoints and schema initialization
- `tests/apphost/postgres-watchlist-persistence-tests.sh` — current API-restart-only persistence test
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` — manifest assertion style
- `tests/apphost/apphost-infrastructure-runtime-tests.sh` — Docker runtime AppHost verification pattern
- `tests/apphost/frontend-trading-workspace-tests.sh` — frontend localStorage/backend-source guardrails if frontend behavior is touched

## Environment

- **Workspace:** Repository root
- **Services required:** Manifest tests should run without a container engine. Full AppHost reboot persistence tests may require Docker/Podman and must cleanly skip when unavailable. Tests must not remove or truncate a developer's real/default Postgres data volume.

## File Scope

> The orchestrator uses this to avoid merge conflicts. Keep changes inside this scope unless `STATUS.md` records a discovered prerequisite.

- `.env.template` (only if a non-secret Postgres volume-name override is introduced)
- `src/ATrade.AppHost/Program.cs`
- `src/ATrade.AppHost/PaperTradingEnvironmentContract.cs` (only if shared parsing is reused)
- `src/ATrade.AppHost/AppHostStorageContract.cs` (new, or equivalent)
- `tests/apphost/apphost-postgres-watchlist-volume-tests.sh` (new)
- `tests/apphost/postgres-watchlist-persistence-tests.sh` (only if shared helpers are extracted)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh`
- `tests/apphost/apphost-infrastructure-runtime-tests.sh` (only if shared runtime helpers are updated)
- `tests/apphost/paper-trading-config-contract-tests.sh` (only if `.env.template` contract assertions change)
- `docs/architecture/paper-trading-workspace.md`
- `docs/architecture/modules.md`
- `docs/architecture/overview.md`
- `scripts/README.md`
- `README.md` (only if current runtime-surface wording changes)
- `tasks/TP-034-apphost-postgres-watchlist-persistence/STATUS.md`

## Steps

> **Hydration:** STATUS.md tracks outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it.

### Step 0: Confirm root cause and scope boundary

- [ ] Inspect the AppHost `postgres` resource and confirm whether it currently has a persistent data volume or bind mount
- [ ] Review existing watchlist persistence coverage and record that it verifies API restart against the same database, not full AppHost/container recreation
- [ ] Record the selected Postgres volume approach in `STATUS.md`; prefer Aspire `WithDataVolume(...)` with a stable named volume and an isolated test override if needed
- [ ] Confirm frontend/localStorage behavior is not the persistence source of truth and should not be changed unless a regression is discovered

**Artifacts:**
- `tasks/TP-034-apphost-postgres-watchlist-persistence/STATUS.md` (modified)

### Step 1: Add durable Postgres storage to AppHost

- [ ] Add a persistent AppHost data volume for the `postgres` resource while preserving existing `--pids-limit` runtime safeguards
- [ ] If a configurable volume name is introduced, add a non-secret `.env.template` default such as `ATRADE_POSTGRES_DATA_VOLUME=atrade-postgres-data` and parse it through an AppHost storage contract
- [ ] Ensure tests can use an isolated temporary Postgres volume name without deleting or modifying a developer's default volume
- [ ] Keep AppHost project references and connection-string naming unchanged for `ATrade.Api` and `ATrade.Ibkr.Worker`
- [ ] Run targeted AppHost build/manifest checks

**Artifacts:**
- `src/ATrade.AppHost/Program.cs` (modified)
- `src/ATrade.AppHost/AppHostStorageContract.cs` (new, or equivalent if volume names are configurable)
- `.env.template` (modified only if non-secret volume setting is added)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (modified)
- `tests/apphost/paper-trading-config-contract-tests.sh` (modified only if `.env.template` changes)

### Step 2: Add full AppHost watchlist reboot regression coverage

- [ ] Create `tests/apphost/apphost-postgres-watchlist-volume-tests.sh` that starts AppHost with isolated temporary ports and an isolated Postgres data volume, then waits for the API health endpoint
- [ ] Pin provider/market-specific watchlist entries through `/api/workspace/watchlist`, stop the full AppHost session, restart AppHost with the same isolated Postgres volume, and verify the same pins are still returned
- [ ] Verify the test path uses backend API persistence only; do not depend on browser `localStorage` or frontend cache files
- [ ] Ensure the test skips cleanly when no Docker/Podman-compatible runtime is available and cleans up only its own temporary volume/container resources
- [ ] Add/update manifest assertions so `postgres` has a non-read-only volume mount in the published AppHost graph

**Artifacts:**
- `tests/apphost/apphost-postgres-watchlist-volume-tests.sh` (new)
- `tests/apphost/apphost-infrastructure-manifest-tests.sh` (modified)
- `tests/apphost/apphost-infrastructure-runtime-tests.sh` (modified only if shared helpers are reused)

### Step 3: Guard against regressions in existing watchlist behavior

- [ ] Keep exact `instrumentKey` / `pinKey` persistence semantics unchanged for duplicate-market symbols
- [ ] Keep database-unavailable responses explicit; do not mask failed Postgres writes with frontend/localStorage state
- [ ] Run existing Workspaces and apphost watchlist tests after the AppHost volume change
- [ ] Update frontend tests only if source markers or backend-watchlist copy changed

**Artifacts:**
- `tests/apphost/postgres-watchlist-persistence-tests.sh` (modified only if needed)
- `tests/ATrade.Workspaces.Tests/*` (modified only if a regression requires source changes)
- `tests/apphost/frontend-trading-workspace-tests.sh` (modified only if frontend-visible behavior changes)

### Step 4: Testing & Verification

> ZERO unexpected test failures allowed. Runtime-dependent checks must pass or cleanly skip according to existing contracts.

- [ ] Run `dotnet test tests/ATrade.Workspaces.Tests/ATrade.Workspaces.Tests.csproj --nologo --verbosity minimal`
- [ ] Run `bash tests/apphost/postgres-watchlist-persistence-tests.sh`
- [ ] Run `bash tests/apphost/apphost-postgres-watchlist-volume-tests.sh`
- [ ] Run `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Run `bash tests/apphost/apphost-infrastructure-runtime-tests.sh`
- [ ] Run `bash tests/apphost/paper-trading-config-contract-tests.sh` if `.env.template` changes
- [ ] Run FULL test suite: `dotnet test ATrade.slnx --nologo --verbosity minimal`
- [ ] Run solution build: `dotnet build ATrade.slnx --nologo --verbosity minimal`
- [ ] Fix all failures or record pre-existing unrelated failures with evidence in `STATUS.md`

### Step 5: Documentation & Delivery

- [ ] "Must Update" docs describe AppHost Postgres volume persistence and watchlist survival across full application reboot
- [ ] "Check If Affected" docs reviewed and updated only where relevant
- [ ] `STATUS.md` Discoveries record the root cause, chosen volume name/override behavior, and test cleanup caveats

## Documentation Requirements

**Must Update:**
- `scripts/README.md` — document AppHost Postgres data persistence, any non-secret volume-name setting, and test/dev cleanup caveats
- `docs/architecture/paper-trading-workspace.md` — clarify watchlist pins survive full AppHost restart because Postgres data is volume-backed
- `docs/architecture/modules.md` — update AppHost/Workspaces responsibilities if storage runtime wording changes

**Check If Affected:**
- `.env.template` — update if a non-secret volume-name setting is added
- `docs/architecture/overview.md` — update if infrastructure graph persistence wording changes
- `README.md` — update if current runtime surface wording changes
- `docs/INDEX.md` — update only if new active docs are introduced

## Completion Criteria

- [ ] AppHost-managed `postgres` uses durable data storage across `start run` stop/start cycles
- [ ] Existing watchlist API/repository semantics remain exact and provider/market-specific
- [ ] A full AppHost reboot regression test pins stocks, restarts AppHost with the same Postgres data volume, and verifies pins survive
- [ ] Tests do not delete or corrupt a developer's default local Postgres volume
- [ ] Browser `localStorage` remains non-authoritative and cannot mask failed backend persistence
- [ ] Docs explain persistence behavior and any local cleanup/volume-name caveats

## Git Commit Convention

Commits happen at **step boundaries** (not after every checkbox). All commits for this task MUST include the task ID for traceability:

- **Step completion:** `fix(TP-034): complete Step N — description`
- **Bug fixes:** `fix(TP-034): description`
- **Tests:** `test(TP-034): description`
- **Hydration:** `hydrate: TP-034 expand Step N checkboxes`

## Do NOT

- Treat browser `localStorage` as authoritative watchlist persistence
- Delete, truncate, or `docker volume rm` a developer's default Postgres data volume from tests
- Change watchlist identity back to bare symbol/name
- Add broker credentials, account identifiers, tokens, cookies, or live-trading behavior
- Break `start run` on Unix or Windows
- Skip tests or commit without the task ID prefix

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution.
     Format:
     ### Amendment N — YYYY-MM-DD HH:MM
     **Issue:** [what was wrong]
     **Resolution:** [what was changed] -->
