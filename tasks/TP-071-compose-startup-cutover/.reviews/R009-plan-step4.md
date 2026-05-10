## Plan Review: Step 4 — Migrate runtime persistence and infrastructure tests

### Verdict: APPROVE

### Summary
The four outcomes correctly target the test files that need migration and align with PROMPT.md requirements. Each checkbox identifies a meaningful behavioral change: container discovery shifts from Aspire-managed to Compose-managed, persistence validation uses Compose volumes, and cleanup/skip behavior is explicit. The worker has enough direction to proceed. Several important implementation risks are worth flagging below — none are blockers at the plan level, but they represent failure modes the worker should address during implementation.

### Issues Found
_None blocking._

### Missing Items
_None. The four checkboxes cover the required outcomes from PROMPT.md Step 4._

### Suggestions

1. **Container discovery label scheme** — All three test files (`apphost-infrastructure-runtime-tests.sh`, `apphost-postgres-watchlist-volume-tests.sh`, `apphost-timescale-cache-volume-tests.sh`) currently use the Aspire-specific label filter `label=com.microsoft.developer.usvc-dev.group-version=usvc-dev.developer.microsoft.com/v1` to find containers. Under Compose mode, containers are labeled with `com.docker.compose.project` and `com.docker.compose.service` instead. The tests should use Compose project-name filtering (e.g., `--filter label=com.docker.compose.project=atrade`) or `docker compose ps -q` to discover containers. Consider adding a shared helper under `tests/compose/` for this, since all three tests need the same discovery mechanism.

2. **Image version matching** — The runtime tests do exact image name matching via `docker inspect --format '{{.Config.Image}}'`. The compose.yaml uses `postgres:17`, `redis:7`, `nats:2`, while the current tests look for `docker.io/library/postgres:17.6`, `docker.io/library/redis:8.6`, `docker.io/library/nats:2.12`. These will mismatch at runtime. The tests should either match the compose.yaml image tags exactly, or use a looser pattern match (substring) rather than exact equality.

3. **Container lifecycle timing** — The tests currently wait for containers to appear *after* AppHost starts (`wait_for_new_infra_containers`). Under Compose mode, `start run` invokes `compose-infra.sh up` before AppHost, so infra containers are already running when AppHost begins. The "wait for new containers" pattern should flip: verify Compose containers are running *before* AppHost starts, or wait for Compose containers to appear *after* Compose `up` but *before* AppHost launch. The postgres/timescale tests that start/stop AppHost twice will run Compose `up` on each `start run` call (idempotent, but worth testing).

4. **Compose project name isolation** — The watchlist and timescale persistence tests each start AppHost twice in sequence with the same volume name. If a developer already has `atrade` Compose project running, these tests could collide. Consider setting `ATRADE_COMPOSE_PROJECT_NAME` to a unique value per test run (e.g., `atrade-test-$$-$RANDOM`) so the test Compose project is fully isolated.

5. **Compose lifecycle for cleanup** — The tests currently use raw `docker rm -f` and `docker volume rm`. Under Compose mode, cleanup should use `compose-infra.sh down` (or the equivalent `docker compose down`) to tear down the Compose project cleanly, followed by `docker volume rm` for the isolated test volumes. Using `docker rm -f` alone could leave stale Compose project metadata.

6. **`ATRADE_INFRASTRUCTURE_MODE` explicitness** — Consider whether the runtime tests should explicitly set `ATRADE_INFRASTRUCTURE_MODE=compose` to assert the default path, or rely on the implicit default. Being explicit makes the test intent clearer and guards against future default changes. The manifest test in Step 3 already uses `ATRADE_INFRASTRUCTURE_MODE=apphost` for the legacy path — the runtime tests should mirror this clarity.

7. **Podman CLI compatibility** — The tests use `docker` CLI commands (`docker ps`, `docker inspect`, `docker logs`, `docker exec`). If Podman is the default, the `docker` command may be a Podman alias or may not exist. The tests should use whichever CLI is available (checking `podman` first, then `docker`) or delegate inspection through Compose (`docker compose exec` / `podman compose exec`) where possible. The compose-infra-contract-tests.sh already demonstrates the Podman-first pattern.
