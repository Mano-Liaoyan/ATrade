# Task: TP-011 — Fix AppHost-managed container startup under a Podman-backed Docker API

**Created:** 2026-04-24
**Size:** M

## Review Level: 3 (Elevated)

**Assessment:** This task changes the local infrastructure runtime contract for
AppHost-managed containers. It touches container startup behavior, resource
limits, and runtime verification for the bootstrap stack. The blast radius is
local orchestration rather than domain logic, but the change is operationally
important.
**Score:** 5/8 — Blast radius: 2, Pattern novelty: 1, Security: 0, Reversibility: 2

## Canonical Task Folder

```text
tasks/TP-011-fix-apphost-container-runtime-startup/
├── PROMPT.md   ← This file (immutable above --- divider)
├── STATUS.md   ← Execution state (worker updates this)
├── .reviews/   ← Reviewer output (task-runner creates this)
└── .DONE       ← Created when complete
```

## Mission

Fix the local infrastructure startup failures seen in the Aspire console when
AppHost launches managed containers through a Docker-compatible socket backed by
rootless Podman.

The operator reported hard failures such as:

- `/bin/sh: 1: Cannot fork`
- `/usr/local/bin/docker-entrypoint.sh: fork: retry: Resource temporarily unavailable`
- `runtime: failed to create new OS thread ... errno=11`

Repository-local investigation reproduced the root causes:

1. AppHost-created `postgres` / `timescaledb` containers currently come up with
   `HostConfig.PidsLimit=0`, but under the Podman Docker API this becomes an
   effective container cgroup limit of `pids.max=1`, which prevents entrypoint
   scripts and Go runtimes from forking.
2. After explicitly setting a safe pids limit, the `timescale/timescaledb:latest-pg17`
   image still fails in rootless Podman because its tuning script tries to read
   `/sys/fs/cgroup/memory.max` and `/sys/fs/cgroup/cpu.max`, which are not
   available in this environment unless tuning inputs are provided explicitly.

This task must implement a real startup fix, not just document the problem or
silence the error.

## Scope

Deliver a durable AppHost container runtime fix:

1. Ensure all AppHost-managed infra containers that need process creation run
   with an explicit, non-broken pids limit instead of relying on the Docker API
   default.
2. Make `timescaledb` start successfully under the same environment by giving it
   deterministic tuning inputs (or another equivalently real fix), rather than
   leaving it to fail inside its init script.
3. Keep the AppHost graph names and resource roles intact: `postgres`,
   `timescaledb`, `redis`, `nats`, `api`, `frontend`.
4. Add runtime verification that exercises the real AppHost path when a local
   container engine is available.
5. Update docs so the local runtime contract is truthful about the fix.

## Dependencies

- **TP-010** — Land the frontend/AppHost runtime-contract fix first so the
  follow-up AppHost orchestration edits in this task apply on top of a stable
  startup baseline and avoid overlapping changes in `src/ATrade.AppHost/Program.cs`.

## Context to Read First

- `README.md`
- `PLAN.md`
- `AGENTS.md`
- `tasks/CONTEXT.md`
- `src/ATrade.AppHost/Program.cs`
- `tests/apphost/apphost-infrastructure-manifest-tests.sh`
- `scripts/README.md`

## Observed Evidence

Concrete reproduction gathered in this repo:

- Running `./start run` under the current environment created AppHost-managed
  containers whose inspect data showed `HostConfig.PidsLimit=0`
- The actual cgroup for those containers showed `pids.max=1`
- That limit explains the reported `Cannot fork` / `newosproc` failures
- Manually running `postgres` with `--pids-limit 2048` starts successfully
- Manually running `timescale/timescaledb:latest-pg17` with `--pids-limit 2048`
  plus explicit `TS_TUNE_MEMORY=512MB` and `TS_TUNE_NUM_CPUS=2` starts successfully,
  whereas the same image without explicit tuning crashes in
  `001_timescaledb_tune.sh`

## Environment

- **Workspace:** Project root
- **Services required:** A local Docker-compatible engine for runtime verification
- **Graceful fallback:** If no engine is available, keep manifest/build checks,
  but when the engine exists the task must verify the real runtime path

## File Scope

- `src/ATrade.AppHost/Program.cs`
- `tests/apphost/` runtime-focused verification script(s)
- `scripts/README.md`
- `README.md` / `PLAN.md` only if current-state wording needs correction

## Steps

### Step 0: Preflight

- [ ] Reproduce/confirm the AppHost-created container runtime state in this repo
- [ ] Confirm the effective `pids.max` problem on AppHost-created infra containers
- [ ] Confirm the TimescaleDB tuning-script failure mode after pids are fixed

### Step 1: Fix process limits for AppHost-managed containers

- [ ] Update the AppHost resource configuration so infra containers do not inherit the broken default pids behavior
- [ ] Use an explicit, readable container runtime configuration rather than a hidden machine tweak
- [ ] Apply the fix consistently to the AppHost-managed infra resources that need it

### Step 2: Fix TimescaleDB startup for rootless Podman compatibility

- [ ] Make `timescaledb` start cleanly under the same runtime path after the pids fix
- [ ] Prefer deterministic tuning inputs or another real configuration fix over merely disabling error output
- [ ] Keep the resource as `timescaledb` and keep it in the AppHost graph

### Step 3: Preserve the bootstrap graph

- [ ] Keep `postgres`, `timescaledb`, `redis`, `nats`, `api`, and `frontend` in the graph
- [ ] Do not replace Aspire with `docker compose` or ad-hoc scripts
- [ ] Do not add unrelated consumer wiring in this task

### Step 4: Add verification

- [ ] Add a runtime verification script that starts the AppHost long enough to inspect the actual container state when an engine is available
- [ ] Verify the affected infra containers get a real pids limit (`pids.max > 1`)
- [ ] Verify `postgres` and `timescaledb` become running/healthy enough to prove startup no longer dies in entrypoint scripts
- [ ] Keep the existing manifest-based verification intact as a container-engine-independent guardrail

### Step 5: Update docs

- [ ] Update `scripts/README.md` to describe the runtime contract truthfully
- [ ] Update `README.md` / `PLAN.md` only if their current wording would otherwise remain misleading
- [ ] Call out any important local runtime assumptions without overstating support

### Step 6: Verification

- [ ] `bash tests/apphost/apphost-infrastructure-manifest-tests.sh`
- [ ] Run the new runtime-focused AppHost infrastructure verification
- [ ] Confirm the original `Cannot fork` / `newosproc` startup class is resolved for the managed infra containers

### Step 7: Delivery

- [ ] Commit with the conventions below

## Documentation Requirements

**Must Update:** `scripts/README.md`
**Check If Affected:** `README.md`, `PLAN.md`

## Completion Criteria

- [ ] AppHost-managed infra containers no longer come up with the broken effective `pids.max=1` behavior in this environment
- [ ] `timescaledb` starts successfully through the AppHost-managed path
- [ ] Verification covers real runtime behavior when a container engine is available
- [ ] Docs reflect the corrected runtime contract

## Git Commit Convention

- **Implementation:** `fix(TP-011): description`
- **Checkpoints:** `checkpoint: TP-011 description`

## Do NOT

- Close the task by saying Podman is unsupported without implementing any repo-level improvement
- Solve the problem by hiding the container failures or suppressing logs only
- Replace AppHost-managed infra with a parallel manual startup path
- Remove `timescaledb` from the graph just to make startup look green
- Add domain logic or application resource consumers in this task

---

## Amendments (Added During Execution)

<!-- Workers add amendments here if issues discovered during execution. -->
