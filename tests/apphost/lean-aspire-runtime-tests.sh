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

pick_free_port() {
  node - <<'NODE'
const net = require('node:net');
const server = net.createServer();
server.listen(0, '127.0.0.1', () => { console.log(server.address().port); server.close(); });
NODE
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
  for temp_file in "$manifest_path" "$api_log" "$health_file" "$response_file" "$request_file" "$env_file"; do
    if [[ -n "$temp_file" && -f "$temp_file" ]]; then rm -f "$temp_file"; fi
  done
}
trap cleanup EXIT

publish_manifest_with_lean() {
  local engine="$1"
  local mode="$2"
  local managed_container_name="${3:-atrade-lean-engine}"
  local workspace_root="${4:-artifacts/lean-workspaces}"
  local docker_command="${5:-docker}"
  local timeout_seconds="${6:-45}"
  manifest_path="$(mktemp --suffix=.json)"

  ATRADE_INFRASTRUCTURE_MODE=compose \
  ATRADE_ANALYSIS_ENGINE="$engine" \
  ATRADE_LEAN_RUNTIME_MODE="$mode" \
  ATRADE_LEAN_CLI_COMMAND=lean \
  ATRADE_LEAN_DOCKER_COMMAND="$docker_command" \
  ATRADE_LEAN_DOCKER_IMAGE=quantconnect/lean:latest \
  ATRADE_LEAN_WORKSPACE_ROOT="$workspace_root" \
  ATRADE_LEAN_TIMEOUT_SECONDS="$timeout_seconds" \
  ATRADE_LEAN_KEEP_WORKSPACE=false \
  ATRADE_LEAN_MANAGED_CONTAINER_NAME="$managed_container_name" \
  ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT=//workspace \
    dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$manifest_path" >/dev/null
}

assert_manifest_env() {
  local expected_engine="$1"
  local expected_mode="$2"
  node - "$repo_root" "$manifest_path" "$expected_engine" "$expected_mode" <<'NODE'
const fs = require('node:fs');
const repoRoot = process.argv[2];
const manifest = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const expectedEngine = process.argv[4];
const expectedMode = process.argv[5];
const resources = manifest.resources || {};
if (resources['lean-engine']) throw new Error('Compose-owned lean-engine must not appear in the default AppHost manifest');
for (const name of ['api', 'ibkr-worker', 'frontend']) if (!resources[name]) throw new Error(`missing ${name}`);
const composeText = fs.readFileSync(`${repoRoot}/compose.yaml`, 'utf8');
if (!composeText.includes('lean-engine:') || !composeText.includes('- lean')) throw new Error('Compose file must own lean-engine behind the lean profile');
const env = resources.api.env || {};
const expected = {
  ATRADE_ANALYSIS_ENGINE: expectedEngine,
  ATRADE_LEAN_RUNTIME_MODE: expectedMode,
  ATRADE_LEAN_CLI_COMMAND: 'lean',
  ATRADE_LEAN_DOCKER_COMMAND: 'docker',
  ATRADE_LEAN_DOCKER_IMAGE: 'quantconnect/lean:latest',
  ATRADE_LEAN_TIMEOUT_SECONDS: '45',
  ATRADE_LEAN_KEEP_WORKSPACE: 'false',
  ATRADE_LEAN_MANAGED_CONTAINER_NAME: 'atrade-lean-engine',
  ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT: '/workspace',
};
for (const [key, value] of Object.entries(expected)) if (env[key] !== value) throw new Error(`${key} expected ${value}, found ${env[key]}`);
if (!String(env.ATRADE_LEAN_WORKSPACE_ROOT || '').replace(/\\/g, '/').endsWith('artifacts/lean-workspaces')) throw new Error('workspace root handoff missing');
NODE
}

write_api_env_exports_from_manifest() {
  env_file="$(mktemp)"
  node - "$manifest_path" >"$env_file" <<'NODE'
const fs = require('node:fs');
const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const env = manifest.resources?.api?.env || {};
const keys = ['ATRADE_ANALYSIS_ENGINE','ATRADE_LEAN_RUNTIME_MODE','ATRADE_LEAN_CLI_COMMAND','ATRADE_LEAN_DOCKER_COMMAND','ATRADE_LEAN_DOCKER_IMAGE','ATRADE_LEAN_WORKSPACE_ROOT','ATRADE_LEAN_TIMEOUT_SECONDS','ATRADE_LEAN_KEEP_WORKSPACE','ATRADE_LEAN_MANAGED_CONTAINER_NAME','ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT'];
for (const key of keys) {
  if (!(key in env)) throw new Error(`missing ${key}`);
  console.log(`export ${key}=${JSON.stringify(String(env[key]))}`);
}
NODE
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
  ( . "$env_file"; ASPNETCORE_URLS="$api_url" dotnet run --project "$api_project" ) >"$api_log" 2>&1 &
  api_pid=$!
  for _ in {1..80}; do
    if [[ "$(curl --silent --output "$health_file" --write-out '%{http_code}' "$api_url/health" || true)" == '200' ]]; then return 0; fi
    if ! kill -0 "$api_pid" 2>/dev/null; then cat "$api_log" >&2; return 1; fi
    sleep 0.5
  done
  cat "$api_log" >&2
  return 1
}

write_direct_bars_analysis_request() {
  node >"$request_file" <<'NODE'
const start = Date.UTC(2026, 3, 1);
const bars = Array.from({ length: 30 }, (_, index) => {
  const close = 100 + index * 0.5;
  return { time: new Date(start + index * 86400000).toISOString(), open: close - 0.25, high: close + 0.75, low: close - 0.75, close, volume: 1000000 + index };
});
console.log(JSON.stringify({ symbol: { symbol: 'AAPL', provider: 'ibkr', providerSymbolId: '265598', assetClass: 'STK', exchange: 'NASDAQ', currency: 'USD' }, timeframe: '1D', requestedAtUtc: '2026-04-30T00:00:00+00:00', bars, engineId: 'lean', strategyName: 'compose-managed-runtime-smoke' }));
NODE
}

assert_disabled_default_manifest_omits_lean_resource_and_hands_off_no_engine_config() {
  publish_manifest_with_lean none cli
  assert_manifest_env none cli
}

assert_lean_docker_manifest_omits_dashboard_resource_and_hands_off_api_config() {
  publish_manifest_with_lean Lean docker
  assert_manifest_env Lean docker
}

assert_api_discovers_lean_engine_from_apphost_env_handoff() {
  publish_manifest_with_lean Lean docker "atrade-lean-engine-discovery-$$" "$(mktemp -d)" docker 5
  start_api_from_manifest_handoff
  local status_code
  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/analysis/engines")"
  [[ "$status_code" == '200' ]] || { cat "$response_file" >&2; cat "$api_log" >&2; return 1; }
  node - "$response_file" <<'NODE'
const fs = require('node:fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
if (payload.length !== 1) throw new Error('expected one LEAN engine');
const descriptor = payload[0];
if (descriptor.metadata?.engineId !== 'lean' || descriptor.metadata?.state !== 'available') throw new Error(`bad metadata ${JSON.stringify(descriptor.metadata)}`);
if (descriptor.capabilities?.requiresExternalRuntime !== true || descriptor.capabilities?.supportsBacktests !== true) throw new Error('bad capabilities');
NODE
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
  publish_manifest_with_lean Lean docker "atrade-lean-engine-unavailable-$$" "$(mktemp -d)" "$fake_docker" 5
  start_api_from_manifest_handoff
  write_direct_bars_analysis_request
  local status_code
  status_code="$(curl --silent --show-error --request POST --header 'Content-Type: application/json' --data @"$request_file" --output "$response_file" --write-out '%{http_code}' "$api_url/api/analysis/run")"
  [[ "$status_code" == '503' ]] || { cat "$response_file" >&2; cat "$api_log" >&2; return 1; }
  node - "$response_file" <<'NODE'
const fs = require('node:fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
if (payload.status !== 'failed') throw new Error('expected failed status');
if (payload.engine?.engineId !== 'lean' || payload.engine?.state !== 'unavailable') throw new Error('expected unavailable engine');
if (payload.error?.code !== 'analysis-engine-unavailable') throw new Error('expected analysis-engine-unavailable');
if (payload.signals?.length || payload.metrics?.length || payload.backtest != null) throw new Error('unavailable runtime returned fake output');
NODE
  rm -f "$fake_docker"
  cleanup_api
}

optional_smoke_analysis_run_if_runtime_available() {
  if ! command -v docker >/dev/null 2>&1 || ! docker version >/dev/null 2>&1; then
    printf 'SKIP: no healthy Docker-compatible engine is available; skipping optional LEAN managed-runtime smoke.\n'
    return 0
  fi
  printf 'SKIP: optional real LEAN smoke is left to local developer runs with the image available.\n'
}

main() {
  command -v curl >/dev/null 2>&1 || { printf 'curl is required for lean-aspire-runtime-tests.sh\n' >&2; return 1; }
  assert_disabled_default_manifest_omits_lean_resource_and_hands_off_no_engine_config
  assert_lean_docker_manifest_omits_dashboard_resource_and_hands_off_api_config
  assert_api_discovers_lean_engine_from_apphost_env_handoff
  assert_unavailable_runtime_response_is_explicit_failure
  optional_smoke_analysis_run_if_runtime_available
}

main "$@"
