#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
manifest_path=''
api_pid=''
api_log=''
api_url=''
health_file=''
response_file=''
request_file=''
env_file=''
lean_smoke_container=''
lean_smoke_workspace=''

pick_free_port() {
  python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

cleanup_api() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  api_pid=''
}

cleanup() {
  cleanup_api

  if [[ -n "$lean_smoke_container" ]] && command -v docker >/dev/null 2>&1; then
    docker rm -f "$lean_smoke_container" >/dev/null 2>&1 || true
  fi

  for temp_file in "$manifest_path" "$api_log" "$health_file" "$response_file" "$request_file" "$env_file"; do
    if [[ -n "$temp_file" && -f "$temp_file" ]]; then
      rm -f "$temp_file"
    fi
  done

  if [[ -n "$lean_smoke_workspace" && -d "$lean_smoke_workspace" ]]; then
    rm -rf "$lean_smoke_workspace"
  fi
}

trap cleanup EXIT

reset_manifest_path() {
  if [[ -n "$manifest_path" && -f "$manifest_path" ]]; then
    rm -f "$manifest_path"
  fi
  manifest_path="$(mktemp --suffix=.json)"
}

publish_manifest_with_lean_defaults() {
  reset_manifest_path

  ATRADE_ANALYSIS_ENGINE=none \
  ATRADE_LEAN_RUNTIME_MODE=cli \
  ATRADE_LEAN_CLI_COMMAND=lean \
  ATRADE_LEAN_DOCKER_COMMAND=docker \
  ATRADE_LEAN_DOCKER_IMAGE=quantconnect/lean:latest \
  ATRADE_LEAN_WORKSPACE_ROOT=artifacts/lean-workspaces \
  ATRADE_LEAN_TIMEOUT_SECONDS=45 \
  ATRADE_LEAN_KEEP_WORKSPACE=false \
  ATRADE_LEAN_MANAGED_CONTAINER_NAME=atrade-lean-engine \
  ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT=/workspace \
    dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$manifest_path" >/dev/null
}

publish_manifest_with_lean_docker_enabled() {
  local managed_container_name="${1:-atrade-lean-engine}"
  local workspace_root="${2:-artifacts/lean-workspaces}"
  local docker_command="${3:-docker}"
  local timeout_seconds="${4:-45}"
  reset_manifest_path

  ATRADE_ANALYSIS_ENGINE=Lean \
  ATRADE_LEAN_RUNTIME_MODE=docker \
  ATRADE_LEAN_CLI_COMMAND=lean \
  ATRADE_LEAN_DOCKER_COMMAND="$docker_command" \
  ATRADE_LEAN_DOCKER_IMAGE=quantconnect/lean:latest \
  ATRADE_LEAN_WORKSPACE_ROOT="$workspace_root" \
  ATRADE_LEAN_TIMEOUT_SECONDS="$timeout_seconds" \
  ATRADE_LEAN_KEEP_WORKSPACE=false \
  ATRADE_LEAN_MANAGED_CONTAINER_NAME="$managed_container_name" \
  ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT=/workspace \
    dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$manifest_path" >/dev/null
}

write_api_env_exports_from_manifest() {
  env_file="$(mktemp)"
  python3 - "$manifest_path" >"$env_file" <<'PY'
import json
import shlex
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text())
api = manifest.get("resources", {}).get("api")
if not api:
    raise SystemExit("expected api resource in manifest")
env = api.get("env", {})
keys = [
    "ATRADE_ANALYSIS_ENGINE",
    "ATRADE_LEAN_RUNTIME_MODE",
    "ATRADE_LEAN_CLI_COMMAND",
    "ATRADE_LEAN_DOCKER_COMMAND",
    "ATRADE_LEAN_DOCKER_IMAGE",
    "ATRADE_LEAN_WORKSPACE_ROOT",
    "ATRADE_LEAN_TIMEOUT_SECONDS",
    "ATRADE_LEAN_KEEP_WORKSPACE",
    "ATRADE_LEAN_MANAGED_CONTAINER_NAME",
    "ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT",
]
missing = [key for key in keys if key not in env]
if missing:
    raise SystemExit(f"api resource is missing expected LEAN environment keys: {missing!r}")
for key in keys:
    print(f"export {key}={shlex.quote(str(env[key]))}")
PY
}

start_api_from_manifest_handoff() {
  cleanup_api
  write_api_env_exports_from_manifest

  local api_port
  api_port="$(pick_free_port)"
  api_url="http://127.0.0.1:${api_port}"
  api_log="$(mktemp)"
  health_file="$(mktemp)"
  response_file="$(mktemp)"
  request_file="$(mktemp)"

  (
    # shellcheck disable=SC1090
    . "$env_file"
    ASPNETCORE_URLS="$api_url" dotnet run --project "$api_project"
  ) >"$api_log" 2>&1 &
  api_pid=$!

  local attempt
  local health_code=''
  for attempt in {1..80}; do
    health_code="$(curl --silent --output "$health_file" --write-out '%{http_code}' "$api_url/health" || true)"
    if [[ "$health_code" == '200' ]]; then
      return 0
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
      printf 'ATrade.Api exited before becoming healthy.\n' >&2
      cat "$api_log" >&2
      return 1
    fi

    sleep 0.5
  done

  printf 'expected GET /health to return HTTP 200, got %s\n' "$health_code" >&2
  cat "$api_log" >&2
  return 1
}

write_direct_bars_analysis_request() {
  python3 >"$request_file" <<'PY'
import json
from datetime import datetime, timedelta, timezone

start = datetime(2026, 4, 1, tzinfo=timezone.utc)
bars = []
for index in range(30):
    close = 100 + index * 0.5
    bars.append({
        "time": (start + timedelta(days=index)).isoformat(),
        "open": close - 0.25,
        "high": close + 0.75,
        "low": close - 0.75,
        "close": close,
        "volume": 1_000_000 + index,
    })

payload = {
    "symbol": {
        "symbol": "AAPL",
        "provider": "ibkr",
        "providerSymbolId": "265598",
        "assetClass": "STK",
        "exchange": "NASDAQ",
        "currency": "USD",
    },
    "timeframe": "1D",
    "requestedAtUtc": "2026-04-30T00:00:00+00:00",
    "bars": bars,
    "engineId": "lean",
    "strategyName": "apphost-managed-runtime-smoke",
}
print(json.dumps(payload))
PY
}

assert_disabled_default_manifest_omits_lean_resource_and_hands_off_no_engine_config() {
  publish_manifest_with_lean_defaults

  python3 - "$repo_root" "$manifest_path" <<'PY'
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[1]).resolve()
manifest_path = Path(sys.argv[2])
manifest = json.loads(manifest_path.read_text())
resources = manifest.get("resources", {})
lean_resources = sorted(name for name in resources if "lean" in name.lower())
if lean_resources:
    raise SystemExit(f"disabled defaults must not create LEAN resources, got {lean_resources!r}")

api = resources.get("api")
if not api:
    raise SystemExit("expected AppHost manifest to include api project resource")

env = api.get("env", {})
expected_workspace = str(repo_root / "artifacts" / "lean-workspaces")
expected = {
    "ATRADE_ANALYSIS_ENGINE": "none",
    "ATRADE_LEAN_RUNTIME_MODE": "cli",
    "ATRADE_LEAN_CLI_COMMAND": "lean",
    "ATRADE_LEAN_DOCKER_COMMAND": "docker",
    "ATRADE_LEAN_DOCKER_IMAGE": "quantconnect/lean:latest",
    "ATRADE_LEAN_WORKSPACE_ROOT": expected_workspace,
    "ATRADE_LEAN_TIMEOUT_SECONDS": "45",
    "ATRADE_LEAN_KEEP_WORKSPACE": "false",
    "ATRADE_LEAN_MANAGED_CONTAINER_NAME": "atrade-lean-engine",
    "ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT": "/workspace",
}
missing_or_wrong = {key: env.get(key) for key, value in expected.items() if env.get(key) != value}
if missing_or_wrong:
    raise SystemExit(f"api project did not receive expected safe LEAN no-engine configuration: {missing_or_wrong!r}")

credential_like = [key for key in env if (key == "ATRADE_ANALYSIS_ENGINE" or key.startswith("ATRADE_LEAN_")) and any(token in key for token in ("PASSWORD", "USERNAME", "ACCOUNT", "TOKEN", "COOKIE", "SECRET"))]
if credential_like:
    raise SystemExit(f"LEAN API environment must not include credential-like variables: {credential_like!r}")
PY
}

assert_lean_docker_manifest_declares_dashboard_resource_mount_and_api_handoff() {
  publish_manifest_with_lean_docker_enabled

  python3 - "$repo_root" "$manifest_path" <<'PY'
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[1]).resolve()
manifest_path = Path(sys.argv[2])
manifest = json.loads(manifest_path.read_text())
resources = manifest.get("resources", {})

lean = resources.get("lean-engine")
if not lean:
    raise SystemExit(f"expected Docker-mode manifest to include stable lean-engine resource; got {sorted(resources)!r}")
if lean.get("type") != "container.v0":
    raise SystemExit(f"lean-engine must be a container resource, got {lean!r}")
if lean.get("image") != "quantconnect/lean:latest":
    raise SystemExit(f"lean-engine must use configured LEAN image, got {lean.get('image')!r}")

bind_mounts = lean.get("bindMounts", [])
workspace_mount = next((mount for mount in bind_mounts if mount.get("target") == "/workspace"), None)
if workspace_mount is None:
    raise SystemExit(f"lean-engine must mount the shared workspace at /workspace, got {bind_mounts!r}")
source = str(workspace_mount.get("source", "")).replace("\\", "/")
if not source.endswith("artifacts/lean-workspaces"):
    raise SystemExit(f"lean-engine workspace mount must use the configured safe workspace root, got {workspace_mount!r}")
if workspace_mount.get("readOnly") is not False:
    raise SystemExit(f"lean-engine workspace mount must be read-write for generated analysis output, got {workspace_mount!r}")

api = resources.get("api")
if not api:
    raise SystemExit("expected AppHost manifest to include api project resource")

env = api.get("env", {})
expected_workspace = str(repo_root / "artifacts" / "lean-workspaces")
expected = {
    "ATRADE_ANALYSIS_ENGINE": "Lean",
    "ATRADE_LEAN_RUNTIME_MODE": "docker",
    "ATRADE_LEAN_CLI_COMMAND": "lean",
    "ATRADE_LEAN_DOCKER_COMMAND": "docker",
    "ATRADE_LEAN_DOCKER_IMAGE": "quantconnect/lean:latest",
    "ATRADE_LEAN_WORKSPACE_ROOT": expected_workspace,
    "ATRADE_LEAN_TIMEOUT_SECONDS": "45",
    "ATRADE_LEAN_KEEP_WORKSPACE": "false",
    "ATRADE_LEAN_MANAGED_CONTAINER_NAME": "atrade-lean-engine",
    "ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT": "/workspace",
}
missing_or_wrong = {key: env.get(key) for key, value in expected.items() if env.get(key) != value}
if missing_or_wrong:
    raise SystemExit(f"api project did not receive expected Docker-mode LEAN configuration: {missing_or_wrong!r}")
PY
}

assert_api_discovers_lean_engine_from_apphost_env_handoff() {
  publish_manifest_with_lean_docker_enabled "atrade-lean-engine-discovery-$$" "$(mktemp -d)" "docker" "5"
  start_api_from_manifest_handoff

  local status_code
  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/analysis/engines")"
  if [[ "$status_code" != '200' ]]; then
    printf 'expected GET /api/analysis/engines to return HTTP 200, got %s\n' "$status_code" >&2
    cat "$response_file" >&2
    cat "$api_log" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
if len(payload) != 1:
    raise SystemExit(f"expected one configured LEAN engine descriptor, got {payload!r}")
descriptor = payload[0]
metadata = descriptor.get("metadata", {})
capabilities = descriptor.get("capabilities", {})
if metadata.get("engineId") != "lean" or metadata.get("state") != "available":
    raise SystemExit(f"expected LEAN available metadata from AppHost env handoff, got {metadata!r}")
if capabilities.get("requiresExternalRuntime") is not True or capabilities.get("supportsBacktests") is not True:
    raise SystemExit(f"expected LEAN capabilities requiring external runtime, got {capabilities!r}")
PY

  cleanup_api
}

assert_unavailable_runtime_response_is_explicit_failure() {
  local fake_docker
  fake_docker="$(mktemp)"
  cat >"$fake_docker" <<'SH'
#!/usr/bin/env bash
printf 'No such container: %s\n' "${4:-atrade-lean-engine}" >&2
exit 1
SH
  chmod +x "$fake_docker"

  publish_manifest_with_lean_docker_enabled "atrade-lean-engine-unavailable-$$" "$(mktemp -d)" "$fake_docker" "5"
  start_api_from_manifest_handoff
  write_direct_bars_analysis_request

  local status_code
  status_code="$(curl --silent --show-error --request POST --header 'Content-Type: application/json' --data @"$request_file" --output "$response_file" --write-out '%{http_code}' "$api_url/api/analysis/run")"
  if [[ "$status_code" != '503' ]]; then
    printf 'expected POST /api/analysis/run to return HTTP 503 when the managed LEAN runtime is unavailable, got %s\n' "$status_code" >&2
    cat "$response_file" >&2
    cat "$api_log" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
if payload.get("status") != "failed":
    raise SystemExit(f"expected failed analysis status, got {payload!r}")
engine = payload.get("engine", {})
if engine.get("engineId") != "lean" or engine.get("state") != "unavailable":
    raise SystemExit(f"expected unavailable LEAN engine metadata, got {engine!r}")
error = payload.get("error", {})
if error.get("code") != "analysis-engine-unavailable":
    raise SystemExit(f"expected analysis-engine-unavailable error, got {payload!r}")
if payload.get("signals") != [] or payload.get("metrics") != [] or payload.get("backtest") is not None:
    raise SystemExit(f"unavailable runtime must not return fake signals, metrics, or backtest output: {payload!r}")
PY

  rm -f "$fake_docker"
  cleanup_api
}

optional_smoke_analysis_run_if_runtime_available() {
  if ! command -v docker >/dev/null 2>&1; then
    printf 'SKIP: docker CLI is not available; skipping optional LEAN managed-runtime smoke.\n'
    return 0
  fi

  if ! docker version >/dev/null 2>&1; then
    printf 'SKIP: no healthy Docker-compatible engine is available; skipping optional LEAN managed-runtime smoke.\n'
    return 0
  fi

  local image='quantconnect/lean:latest'
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    printf 'SKIP: configured LEAN image %s is not present locally; skipping optional managed-runtime smoke.\n' "$image"
    return 0
  fi

  if ! docker run --rm --entrypoint test "$image" -f /Lean/Launcher/bin/Debug/QuantConnect.Lean.Launcher.dll >/dev/null 2>&1; then
    printf 'SKIP: configured LEAN image %s is present but does not expose the LEAN engine launcher; skipping optional managed-runtime smoke.\n' "$image"
    return 0
  fi

  lean_smoke_container="atrade-lean-engine-smoke-$$"
  lean_smoke_workspace="$(mktemp -d)"
  docker run --detach --rm \
    --name "$lean_smoke_container" \
    --pids-limit 2048 \
    --volume "$lean_smoke_workspace:/workspace" \
    --entrypoint tail \
    "$image" -f /dev/null >/dev/null

  publish_manifest_with_lean_docker_enabled "$lean_smoke_container" "$lean_smoke_workspace" "docker" "45"
  start_api_from_manifest_handoff
  write_direct_bars_analysis_request

  local status_code
  status_code="$(curl --silent --show-error --request POST --header 'Content-Type: application/json' --data @"$request_file" --output "$response_file" --write-out '%{http_code}' "$api_url/api/analysis/run")"
  if [[ "$status_code" != '200' ]]; then
    printf 'expected optional LEAN managed-runtime smoke to return HTTP 200, got %s\n' "$status_code" >&2
    cat "$response_file" >&2
    cat "$api_log" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
if payload.get("status") != "completed":
    raise SystemExit(f"expected completed optional LEAN analysis smoke result, got {payload!r}")
if payload.get("engine", {}).get("engineId") != "lean":
    raise SystemExit(f"expected LEAN engine metadata, got {payload!r}")
if payload.get("error") is not None:
    raise SystemExit(f"completed smoke must not include an error: {payload!r}")
PY

  cleanup_api
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for lean-aspire-runtime-tests.sh\n' >&2
    return 1
  fi

  assert_disabled_default_manifest_omits_lean_resource_and_hands_off_no_engine_config
  assert_lean_docker_manifest_declares_dashboard_resource_mount_and_api_handoff
  assert_api_discovers_lean_engine_from_apphost_env_handoff
  assert_unavailable_runtime_response_is_explicit_failure
  optional_smoke_analysis_run_if_runtime_available
}

main "$@"
