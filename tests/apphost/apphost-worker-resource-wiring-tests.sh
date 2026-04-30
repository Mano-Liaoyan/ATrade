#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
manifest_path=''
enabled_manifest_path=''
missing_credentials_manifest_path=''

cleanup() {
  if [[ -n "$manifest_path" && -f "$manifest_path" ]]; then
    rm -f "$manifest_path"
  fi

  if [[ -n "$enabled_manifest_path" && -f "$enabled_manifest_path" ]]; then
    rm -f "$enabled_manifest_path"
  fi

  if [[ -n "$missing_credentials_manifest_path" && -f "$missing_credentials_manifest_path" ]]; then
    rm -f "$missing_credentials_manifest_path"
  fi
}

trap cleanup EXIT

publish_apphost_manifest() {
  local output_path="$1"
  local integration_enabled="$2"
  local username="$3"
  local password="$4"

  ATRADE_BROKER_INTEGRATION_ENABLED="$integration_enabled" \
  ATRADE_BROKER_ACCOUNT_MODE=Paper \
  ATRADE_IBKR_GATEWAY_URL=https://127.0.0.1:5000 \
  ATRADE_IBKR_GATEWAY_PORT=5000 \
  ATRADE_IBKR_GATEWAY_IMAGE=voyz/ibeam:latest \
  ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS=15 \
  ATRADE_IBKR_USERNAME="$username" \
  ATRADE_IBKR_PASSWORD="$password" \
  ATRADE_IBKR_PAPER_ACCOUNT_ID=IBKR_ACCOUNT_ID \
  dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$output_path" >/dev/null
}

assert_secret_parameters_are_redacted() {
  python3 - <<'PY' "$1"
import json
import sys

manifest_path = sys.argv[1]
with open(manifest_path, encoding="utf-8") as handle:
    manifest = json.load(handle)

resources = manifest.get("resources", {})
for resource_name in ("ibkr-username", "ibkr-password", "ibkr-paper-account-id"):
    resource = resources.get(resource_name)
    if resource is None:
        raise SystemExit(f"missing secret parameter resource: {resource_name}")
    if resource.get("type") != "parameter.v0":
        raise SystemExit(f"{resource_name} should be a parameter resource")
    value_input = resource.get("inputs", {}).get("value", {})
    if value_input.get("secret") is not True:
        raise SystemExit(f"{resource_name} parameter must be marked secret")
PY
}

assert_manifest_wires_worker_and_application_resources() {
  manifest_path="$(mktemp --suffix=.json)"
  publish_apphost_manifest "$manifest_path" false IBKR_USERNAME IBKR_PASSWORD
  assert_secret_parameters_are_redacted "$manifest_path"

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

if "ibkr-gateway" in resources:
    raise SystemExit("ibkr-gateway should stay optional and must not appear while broker integration is disabled")

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
    "ATRADE_BROKER_INTEGRATION_ENABLED": "false",
    "ATRADE_BROKER_ACCOUNT_MODE": "Paper",
    "ATRADE_IBKR_GATEWAY_URL": "https://127.0.0.1:5000",
    "ATRADE_IBKR_GATEWAY_PORT": "5000",
    "ATRADE_IBKR_GATEWAY_IMAGE": "voyz/ibeam:latest",
    "ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS": "15",
    "ATRADE_IBKR_PAPER_ACCOUNT_ID": "{ibkr-paper-account-id.value}",
    "ATRADE_IBKR_USERNAME": "{ibkr-username.value}",
    "ATRADE_IBKR_PASSWORD": "{ibkr-password.value}",
}

expected_worker_env = {
    "ConnectionStrings__postgres": "{postgres.connectionString}",
    "ConnectionStrings__redis": "{redis.connectionString}",
    "ConnectionStrings__nats": "{nats.connectionString}",
    "POSTGRES_HOST": "{postgres.bindings.tcp.host}",
    "REDIS_HOST": "{redis.bindings.tcp.host}",
    "NATS_HOST": "{nats.bindings.tcp.host}",
    "ATRADE_BROKER_INTEGRATION_ENABLED": "false",
    "ATRADE_BROKER_ACCOUNT_MODE": "Paper",
    "ATRADE_IBKR_GATEWAY_URL": "https://127.0.0.1:5000",
    "ATRADE_IBKR_GATEWAY_PORT": "5000",
    "ATRADE_IBKR_GATEWAY_IMAGE": "voyz/ibeam:latest",
    "ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS": "15",
    "ATRADE_IBKR_PAPER_ACCOUNT_ID": "{ibkr-paper-account-id.value}",
    "ATRADE_IBKR_USERNAME": "{ibkr-username.value}",
    "ATRADE_IBKR_PASSWORD": "{ibkr-password.value}",
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

assert_manifest_does_not_start_ibeam_with_placeholder_credentials() {
  missing_credentials_manifest_path="$(mktemp --suffix=.json)"
  publish_apphost_manifest "$missing_credentials_manifest_path" true IBKR_USERNAME IBKR_PASSWORD
  assert_secret_parameters_are_redacted "$missing_credentials_manifest_path"

  python3 - <<'PY' "$missing_credentials_manifest_path"
import json
import sys

manifest_path = sys.argv[1]
with open(manifest_path, encoding="utf-8") as handle:
    manifest = json.load(handle)

resources = manifest.get("resources", {})
if "ibkr-gateway" in resources:
    raise SystemExit("ibkr-gateway must not start when enabled config still contains fake IBKR credential placeholders")

for resource_name in ("api", "ibkr-worker"):
    env = resources[resource_name].get("env", {})
    if env.get("ATRADE_BROKER_INTEGRATION_ENABLED") != "true":
        raise SystemExit(f"{resource_name} should still receive the enabled integration flag")
    if env.get("ATRADE_IBKR_PAPER_ACCOUNT_ID") != "{ibkr-paper-account-id.value}":
        raise SystemExit(f"{resource_name} paper account id env must stay a secret parameter reference")
    if env.get("ATRADE_IBKR_USERNAME") != "{ibkr-username.value}":
        raise SystemExit(f"{resource_name} username env must stay a secret parameter reference")
    if env.get("ATRADE_IBKR_PASSWORD") != "{ibkr-password.value}":
        raise SystemExit(f"{resource_name} password env must stay a secret parameter reference")
PY
}

assert_manifest_wires_ibeam_container_when_enabled() {
  enabled_manifest_path="$(mktemp --suffix=.json)"
  publish_apphost_manifest \
    "$enabled_manifest_path" \
    true \
    REAL_IBKR_USERNAME_SHOULD_NOT_SURFACE \
    REAL_IBKR_PASSWORD_SHOULD_NOT_SURFACE
  assert_secret_parameters_are_redacted "$enabled_manifest_path"

  python3 - <<'PY' "$enabled_manifest_path"
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
manifest_text = manifest_path.read_text(encoding="utf-8")
for forbidden in (
    "REAL_IBKR_USERNAME_SHOULD_NOT_SURFACE",
    "REAL_IBKR_PASSWORD_SHOULD_NOT_SURFACE",
    "IBKR_ACCOUNT_ID",
):
    if forbidden in manifest_text:
        raise SystemExit(f"manifest exposed raw IBKR credential value: {forbidden}")

manifest = json.loads(manifest_text)
resources = manifest.get("resources", {})
container = resources.get("ibkr-gateway")
if container is None:
    raise SystemExit("ibkr-gateway container must be present when integration and credentials are configured")
if container.get("type") != "container.v0":
    raise SystemExit(f"ibkr-gateway should be a container resource, found {container.get('type')}")
if container.get("image") != "voyz/ibeam:latest":
    raise SystemExit(f"ibkr-gateway must use voyz/ibeam:latest, found {container.get('image')}")

container_env = container.get("env", {})
expected_container_env = {
    "IBEAM_ACCOUNT": "{ibkr-username.value}",
    "IBEAM_PASSWORD": "{ibkr-password.value}",
}
if container_env != expected_container_env:
    raise SystemExit(f"ibkr-gateway should receive only required iBeam env vars: {container_env!r}")

https_binding = container.get("bindings", {}).get("https", {})
if https_binding.get("scheme") != "https" or https_binding.get("targetPort") != 5000:
    raise SystemExit(f"ibkr-gateway HTTPS target port should be 5000, found {https_binding!r}")

for resource_name in ("api", "ibkr-worker"):
    env = resources[resource_name].get("env", {})
    if env.get("ATRADE_IBKR_PAPER_ACCOUNT_ID") != "{ibkr-paper-account-id.value}":
        raise SystemExit(f"{resource_name} paper account id env must be a secret parameter reference")
    if env.get("ATRADE_IBKR_USERNAME") != "{ibkr-username.value}":
        raise SystemExit(f"{resource_name} username env must be a secret parameter reference")
    if env.get("ATRADE_IBKR_PASSWORD") != "{ibkr-password.value}":
        raise SystemExit(f"{resource_name} password env must be a secret parameter reference")
PY
}

main() {
  assert_manifest_wires_worker_and_application_resources
  assert_manifest_does_not_start_ibeam_with_placeholder_credentials
  assert_manifest_wires_ibeam_container_when_enabled
}

main "$@"
