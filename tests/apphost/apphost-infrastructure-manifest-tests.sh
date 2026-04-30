#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$repo_root/scripts/local-env.sh"
atrade_load_local_port_contract "$repo_root"

manifest_path=''
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

assert_manifest_database_volume() {
  local resource_name="$1"
  local expected_volume="$2"

  python3 - <<'PY' "$manifest_path" "$resource_name" "$expected_volume"
import json
import sys

manifest_path, resource_name, expected_volume = sys.argv[1:]
with open(manifest_path, encoding="utf-8") as handle:
    manifest = json.load(handle)

resource = manifest.get("resources", {}).get(resource_name)
if not isinstance(resource, dict):
    raise SystemExit(f"manifest missing {resource_name!r} resource")

volumes = resource.get("volumes")
if not isinstance(volumes, list):
    raise SystemExit(f"manifest {resource_name!r} resource does not declare volumes")

matching = [
    volume for volume in volumes
    if volume.get("name") == expected_volume and volume.get("target") == "/var/lib/postgresql/data"
]
if not matching:
    raise SystemExit(
        f"manifest {resource_name!r} resource must mount {expected_volume!r} at /var/lib/postgresql/data; volumes={volumes!r}")

if matching[0].get("readOnly") is not False:
    raise SystemExit(
        f"manifest {resource_name!r} data volume {expected_volume!r} must be readOnly=false; volume={matching[0]!r}")
PY
}

cleanup() {
  if [[ -n "$manifest_path" && -f "$manifest_path" ]]; then
    rm -f "$manifest_path"
  fi
}

trap cleanup EXIT

assert_manifest_declares_infrastructure_graph() {
  manifest_path="$(mktemp --suffix=.json)"

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

main() {
  assert_manifest_declares_infrastructure_graph
}

main "$@"
