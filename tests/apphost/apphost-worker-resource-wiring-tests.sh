#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
manifest_path=''

cleanup() {
  if [[ -n "$manifest_path" && -f "$manifest_path" ]]; then
    rm -f "$manifest_path"
  fi
}

trap cleanup EXIT

assert_manifest_wires_worker_and_application_resources() {
  manifest_path="$(mktemp --suffix=.json)"

  dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$manifest_path" >/dev/null

  python3 - <<'PY' "$manifest_path"
import json
import sys

manifest_path = sys.argv[1]
with open(manifest_path, encoding="utf-8") as handle:
    manifest = json.load(handle)

resources = manifest.get("resources", {})

required_resource_types = {
    "api": "project.v0",
    "ibkr-worker": "project.v0",
    "frontend": "container.v1",
    "postgres": "container.v0",
    "timescaledb": "container.v0",
    "redis": "container.v0",
    "nats": "container.v0",
}

for resource_name, expected_type in required_resource_types.items():
    resource = resources.get(resource_name)
    if resource is None:
        raise SystemExit(f"missing resource: {resource_name}")

    actual_type = resource.get("type")
    if actual_type != expected_type:
        raise SystemExit(
            f"resource {resource_name} expected type {expected_type}, found {actual_type}"
        )

api_env = resources["api"].get("env", {})
worker_env = resources["ibkr-worker"].get("env", {})

expected_api_env = {
    "ConnectionStrings__postgres": "{postgres.connectionString}",
    "ConnectionStrings__timescaledb": "{timescaledb.connectionString}",
    "ConnectionStrings__redis": "{redis.connectionString}",
    "ConnectionStrings__nats": "{nats.connectionString}",
    "POSTGRES_HOST": "{postgres.bindings.tcp.host}",
    "TIMESCALEDB_HOST": "{timescaledb.bindings.tcp.host}",
    "REDIS_HOST": "{redis.bindings.tcp.host}",
    "NATS_HOST": "{nats.bindings.tcp.host}",
}

expected_worker_env = {
    "ConnectionStrings__postgres": "{postgres.connectionString}",
    "ConnectionStrings__redis": "{redis.connectionString}",
    "ConnectionStrings__nats": "{nats.connectionString}",
    "POSTGRES_HOST": "{postgres.bindings.tcp.host}",
    "REDIS_HOST": "{redis.bindings.tcp.host}",
    "NATS_HOST": "{nats.bindings.tcp.host}",
}

for key, expected_value in expected_api_env.items():
    actual_value = api_env.get(key)
    if actual_value != expected_value:
        raise SystemExit(
            f"api env {key} expected {expected_value}, found {actual_value}"
        )

for key, expected_value in expected_worker_env.items():
    actual_value = worker_env.get(key)
    if actual_value != expected_value:
        raise SystemExit(
            f"ibkr-worker env {key} expected {expected_value}, found {actual_value}"
        )

if "ConnectionStrings__timescaledb" in worker_env or any(
    key.startswith("TIMESCALEDB_") for key in worker_env
):
    raise SystemExit("ibkr-worker should not receive TimescaleDB wiring in this slice")
PY
}

main() {
  assert_manifest_wires_worker_and_application_resources
}

main "$@"
