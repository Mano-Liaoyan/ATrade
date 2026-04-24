#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
manifest_path=''

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

cleanup() {
  if [[ -n "$manifest_path" && -f "$manifest_path" ]]; then
    rm -f "$manifest_path"
  fi
}

trap cleanup EXIT

assert_manifest_declares_infrastructure_graph() {
  manifest_path="$(mktemp --suffix=.json)"

  dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$manifest_path" >/dev/null

  assert_file_contains "$manifest_path" '"postgres"'
  assert_file_contains "$manifest_path" '"timescaledb"'
  assert_file_contains "$manifest_path" '"redis"'
  assert_file_contains "$manifest_path" '"nats"'
  assert_file_contains "$manifest_path" '"api"'
  assert_file_contains "$manifest_path" '"frontend"'

  assert_file_contains "$manifest_path" '"image": "docker.io/library/postgres:'
  assert_file_contains "$manifest_path" '"image": "docker.io/timescale/timescaledb:latest-pg17"'
  assert_file_contains "$manifest_path" '"image": "docker.io/library/redis:'
  assert_file_contains "$manifest_path" '"image": "docker.io/library/nats:'
  assert_file_contains "$manifest_path" '"TS_TUNE_MEMORY": "512MB"'
  assert_file_contains "$manifest_path" '"TS_TUNE_NUM_CPUS": "2"'

  assert_file_contains "$manifest_path" '"targetPort": 5432'
  assert_file_contains "$manifest_path" '"targetPort": 6379'
  assert_file_contains "$manifest_path" '"targetPort": 4222'
  assert_file_contains "$manifest_path" '"targetPort": 3000'
  assert_file_contains "$manifest_path" '"type": "project.v0"'
  assert_file_contains "$manifest_path" '"type": "container.v1"'
  assert_file_contains "$manifest_path" '"type": "container.v0"'
  assert_file_contains "$manifest_path" '"external": true'
}

main() {
  assert_manifest_declares_infrastructure_graph
}

main "$@"
