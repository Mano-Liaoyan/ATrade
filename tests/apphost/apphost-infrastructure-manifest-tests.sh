#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$repo_root/scripts/local-env.sh"
atrade_load_local_port_contract "$repo_root"

manifest_path=''
compose_manifest_path=''
manifest_postgres_data_volume="atrade-postgres-manifest-test-$$-$RANDOM"
manifest_timescale_data_volume="atrade-timescaledb-manifest-test-$$-$RANDOM"

assert_file_contains() {
  local file_path="$1"
  local needle="$2"

  if [[ ! -f "$file_path" ]]; then
    printf 'expected file to exist: %s\n' "$file_path" >&2
    return 1
  fi

  if ! grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_file_not_contains() {
  local file_path="$1"
  local needle="$2"

  if grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_manifest_database_volume() {
  local resource_name="$1"
  local expected_volume="$2"

  node - <<'NODE' "$manifest_path" "$resource_name" "$expected_volume"
const fs = require('fs');
const [manifestPath, resourceName, expectedVolume] = process.argv.slice(2);
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const resource = manifest.resources?.[resourceName];
if (!resource) throw new Error(`manifest missing ${resourceName} resource`);
const volumes = resource.volumes;
if (!Array.isArray(volumes)) throw new Error(`manifest ${resourceName} resource does not declare volumes`);
const matching = volumes.filter((volume) => volume.name === expectedVolume && volume.target === '/var/lib/postgresql/data');
if (matching.length === 0) {
  throw new Error(`manifest ${resourceName} resource must mount ${expectedVolume} at /var/lib/postgresql/data; volumes=${JSON.stringify(volumes)}`);
}
if (matching[0].readOnly !== false) {
  throw new Error(`manifest ${resourceName} data volume ${expectedVolume} must be readOnly=false; volume=${JSON.stringify(matching[0])}`);
}
NODE
}

cleanup() {
  if [[ -n "$manifest_path" && -f "$manifest_path" ]]; then
    rm -f "$manifest_path"
  fi
  if [[ -n "$compose_manifest_path" && -f "$compose_manifest_path" ]]; then
    rm -f "$compose_manifest_path"
  fi
}

trap cleanup EXIT

assert_manifest_declares_infrastructure_graph() {
  manifest_path="$(mktemp --suffix=.json)"

  ATRADE_INFRASTRUCTURE_MODE=apphost \
    ATRADE_POSTGRES_DATA_VOLUME="$manifest_postgres_data_volume" \
    ATRADE_TIMESCALEDB_DATA_VOLUME="$manifest_timescale_data_volume" \
    dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$manifest_path" >/dev/null

  assert_file_contains "$manifest_path" '"postgres"'
  assert_file_contains "$manifest_path" '"timescaledb"'
  assert_file_contains "$manifest_path" '"redis"'
  assert_file_contains "$manifest_path" '"nats"'
  assert_file_contains "$manifest_path" '"api"'
  assert_file_contains "$manifest_path" '"frontend"'

  assert_file_contains "$manifest_path" '"image": "docker.io/library/postgres:'
  assert_file_contains "$manifest_path" "\"name\": \"$manifest_postgres_data_volume\""
  assert_file_contains "$manifest_path" '"target": "/var/lib/postgresql/data"'
  assert_file_contains "$manifest_path" '"readOnly": false'
  assert_file_contains "$manifest_path" '"image": "docker.io/timescale/timescaledb:latest-pg17"'
  assert_file_contains "$manifest_path" "\"name\": \"$manifest_timescale_data_volume\""
  assert_manifest_database_volume postgres "$manifest_postgres_data_volume"
  assert_manifest_database_volume timescaledb "$manifest_timescale_data_volume"
  assert_file_contains "$manifest_path" '"image": "docker.io/library/redis:'
  assert_file_contains "$manifest_path" '"image": "docker.io/library/nats:'
  assert_file_contains "$manifest_path" '"TS_TUNE_MEMORY": "512MB"'
  assert_file_contains "$manifest_path" '"TS_TUNE_NUM_CPUS": "2"'

  assert_file_contains "$manifest_path" '"ConnectionStrings__postgres": "{postgres.connectionString}"'
  assert_file_contains "$manifest_path" '"ConnectionStrings__timescaledb": "{timescaledb.connectionString}"'
  assert_file_contains "$manifest_path" '"targetPort": 5432'
  assert_file_contains "$manifest_path" '"targetPort": 6379'
  assert_file_contains "$manifest_path" '"targetPort": 4222'
  assert_file_contains "$manifest_path" "\"targetPort\": $ATRADE_APPHOST_FRONTEND_HTTP_PORT"
  assert_file_contains "$manifest_path" '"type": "project.v0"'
  assert_file_contains "$manifest_path" '"type": "container.v1"'
  assert_file_contains "$manifest_path" '"type": "container.v0"'
  assert_file_contains "$manifest_path" '"external": true'
}

assert_default_compose_mode_omits_infrastructure_graph() {
  compose_manifest_path="$(mktemp --suffix=.json)"

  ATRADE_POSTGRES_PORT=15432 \
    ATRADE_TIMESCALEDB_PORT=15433 \
    ATRADE_REDIS_PORT=16379 \
    ATRADE_NATS_PORT=14222 \
    dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$compose_manifest_path" >/dev/null

  node - <<'NODE' "$compose_manifest_path"
const fs = require('fs');
const manifestPath = process.argv[2];
const text = fs.readFileSync(manifestPath, 'utf8');
const manifest = JSON.parse(text);
const resources = manifest.resources ?? {};
for (const resourceName of ['postgres', 'timescaledb', 'redis', 'nats', 'ibkr-gateway', 'lean-engine']) {
  if (Object.prototype.hasOwnProperty.call(resources, resourceName)) {
    throw new Error(`Default Compose infrastructure mode must not declare ${resourceName}`);
  }
}
for (const resourceName of ['api', 'ibkr-worker', 'frontend']) {
  if (!resources[resourceName]) {
    throw new Error(`Default Compose infrastructure mode must keep ${resourceName}`);
  }
}
if (resources.api.type !== 'project.v0') throw new Error(`api should stay project.v0, found ${resources.api.type}`);
if (resources['ibkr-worker'].type !== 'project.v0') throw new Error(`ibkr-worker should stay project.v0, found ${resources['ibkr-worker'].type}`);
if (resources.frontend.type !== 'container.v1') throw new Error(`frontend should stay container.v1, found ${resources.frontend.type}`);
const apiEnv = resources.api.env ?? {};
const workerEnv = resources['ibkr-worker'].env ?? {};
const expectedApi = {
  ConnectionStrings__postgres: 'Host=127.0.0.1;Port=15432;Username=postgres;Password={postgres-password.value};Database=postgres',
  ConnectionStrings__timescaledb: 'Host=127.0.0.1;Port=15433;Username=postgres;Password={timescaledb-password.value};Database=postgres',
  ConnectionStrings__redis: '127.0.0.1:16379',
  ConnectionStrings__nats: 'nats://127.0.0.1:14222',
};
const expectedWorker = {
  ConnectionStrings__postgres: expectedApi.ConnectionStrings__postgres,
  ConnectionStrings__redis: expectedApi.ConnectionStrings__redis,
  ConnectionStrings__nats: expectedApi.ConnectionStrings__nats,
};
for (const [key, expected] of Object.entries(expectedApi)) {
  if (apiEnv[key] !== expected) throw new Error(`api env ${key} expected ${expected}, found ${apiEnv[key]}`);
}
for (const [key, expected] of Object.entries(expectedWorker)) {
  if (workerEnv[key] !== expected) throw new Error(`ibkr-worker env ${key} expected ${expected}, found ${workerEnv[key]}`);
}
for (const forbidden of ['ATRADE_POSTGRES_PASSWORD', 'ATRADE_TIMESCALEDB_PASSWORD']) {
  if (text.includes(forbidden)) throw new Error(`manifest exposed raw database password placeholder ${forbidden}`);
}
NODE

  assert_file_not_contains "$compose_manifest_path" '"image": "docker.io/library/postgres:'
  assert_file_not_contains "$compose_manifest_path" '"image": "docker.io/timescale/timescaledb:'
  assert_file_not_contains "$compose_manifest_path" '"image": "docker.io/library/redis:'
  assert_file_not_contains "$compose_manifest_path" '"image": "docker.io/library/nats:'
}

main() {
  assert_manifest_declares_infrastructure_graph
  assert_default_compose_mode_omits_infrastructure_graph
}

main "$@"
