#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$repo_root/scripts/local-env.sh"

api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
api_pid=''
api_log=''
health_file=''
overview_file=''
status_file=''
simulation_file=''
second_simulation_file=''
live_status_file=''
live_simulation_file=''

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

cleanup_files() {
  rm -f "$health_file" "$overview_file" "$status_file" "$simulation_file" \
    "$second_simulation_file" "$live_status_file" "$live_simulation_file"
}

stop_api() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  api_pid=''

  if [[ -n "$api_log" && -f "$api_log" ]]; then
    rm -f "$api_log"
  fi

  api_log=''
}

cleanup() {
  stop_api
  cleanup_files
}

trap cleanup EXIT

allocate_api_port() {
  python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

start_api() {
  local integration_enabled="$1"
  local account_mode="$2"
  local api_port="$3"
  local api_url="http://127.0.0.1:${api_port}"

  stop_api
  api_log="$(mktemp)"

  ATRADE_BROKER_INTEGRATION_ENABLED="$integration_enabled" \
  ATRADE_BROKER_ACCOUNT_MODE="$account_mode" \
  ATRADE_IBKR_GATEWAY_URL="http://127.0.0.1:5000" \
  ATRADE_IBKR_GATEWAY_PORT="5000" \
  ATRADE_IBKR_GATEWAY_IMAGE="example.invalid/ibkr-gateway-paper:local" \
  ATRADE_IBKR_PAPER_ACCOUNT_ID="PAPER_ACCOUNT_ID" \
  ASPNETCORE_URLS="$api_url" \
  dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  wait_for_api "$api_url"
}

wait_for_api() {
  local api_url="$1"
  local health_code=''

  for _ in {1..40}; do
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

  printf 'ATrade.Api did not become healthy at %s.\n' "$api_url" >&2
  cat "$api_log" >&2
  return 1
}

assert_default_contract_and_references() {
  assert_file_contains "$repo_root/.env.example" 'ATRADE_BROKER_INTEGRATION_ENABLED=false'
  assert_file_contains "$repo_root/.env.example" 'ATRADE_BROKER_ACCOUNT_MODE=Paper'
  assert_file_contains "$repo_root/.env.example" 'ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS=15'
  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.Brokers.Ibkr'
  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.Orders.Tests'
  assert_file_contains "$repo_root/src/ATrade.Api/ATrade.Api.csproj" 'ATrade.Brokers.Ibkr.csproj'
  assert_file_contains "$repo_root/src/ATrade.Api/ATrade.Api.csproj" 'ATrade.Orders.csproj'
  assert_file_contains "$repo_root/workers/ATrade.Ibkr.Worker/ATrade.Ibkr.Worker.csproj" 'ATrade.Brokers.Ibkr.csproj'
}

run_build_and_unit_checks() {
  dotnet build "$repo_root/ATrade.sln" --nologo --verbosity minimal >/dev/null
  dotnet test "$repo_root/tests/ATrade.Brokers.Ibkr.Tests/ATrade.Brokers.Ibkr.Tests.csproj" --nologo --verbosity minimal >/dev/null
  dotnet test "$repo_root/tests/ATrade.Orders.Tests/ATrade.Orders.Tests.csproj" --nologo --verbosity minimal >/dev/null
}

assert_default_mode_endpoints() {
  local api_port="$1"
  local api_url="http://127.0.0.1:${api_port}"

  [[ "$(cat "$health_file")" == 'ok' ]]

  local overview_code
  local status_code
  local simulation_code
  local second_simulation_code

  overview_code="$(curl --silent --output "$overview_file" --write-out '%{http_code}' "$api_url/api/accounts/overview")"
  status_code="$(curl --silent --output "$status_file" --write-out '%{http_code}' "$api_url/api/broker/ibkr/status")"
  simulation_code="$(curl --silent --header 'Content-Type: application/json' --data '{"symbol":"MSFT","side":"Buy","quantity":5,"orderType":"Market"}' --output "$simulation_file" --write-out '%{http_code}' "$api_url/api/orders/simulate")"
  second_simulation_code="$(curl --silent --header 'Content-Type: application/json' --data '{"symbol":"MSFT","side":"Buy","quantity":5,"orderType":"Market"}' --output "$second_simulation_file" --write-out '%{http_code}' "$api_url/api/orders/simulate")"

  [[ "$overview_code" == '200' ]]
  [[ "$status_code" == '200' ]]
  [[ "$simulation_code" == '200' ]]
  [[ "$second_simulation_code" == '200' ]]

  python3 - <<'PY' "$overview_file" "$status_file" "$simulation_file" "$second_simulation_file"
import json, sys
from pathlib import Path
overview = json.loads(Path(sys.argv[1]).read_text())
status = json.loads(Path(sys.argv[2]).read_text())
simulation = json.loads(Path(sys.argv[3]).read_text())
second_simulation = json.loads(Path(sys.argv[4]).read_text())
expected_overview = {
    'module': 'accounts',
    'status': 'bootstrap',
    'brokerConnection': 'not-configured',
    'accounts': [],
}
if overview != expected_overview:
    raise SystemExit(f'unexpected accounts overview payload: {overview!r}')
expected_status_keys = {
    'provider',
    'state',
    'mode',
    'integrationEnabled',
    'hasPaperAccountId',
    'authenticated',
    'connected',
    'competing',
    'message',
    'observedAtUtc',
    'capabilities',
}
if set(status) != expected_status_keys:
    raise SystemExit(f'broker status exposed unexpected fields: {status!r}')
if status['provider'] != 'ibkr' or status['state'] != 'disabled' or status['mode'] != 'paper':
    raise SystemExit(f'unexpected broker status payload: {status!r}')
capabilities = status['capabilities']
if capabilities.get('supportsBrokerOrderPlacement') is not False or capabilities.get('usesOfficialApisOnly') is not True:
    raise SystemExit(f'unexpected broker capability flags: {status!r}')
if 'paperAccountId' in status or 'gatewayUrl' in status:
    raise SystemExit(f'broker status leaked unsafe fields: {status!r}')
if simulation != second_simulation:
    raise SystemExit('simulation payload must be deterministic across repeated identical requests')
if simulation.get('simulated') is not True or simulation.get('brokerOrderPlacementAttempted') is not False:
    raise SystemExit(f'unexpected simulation payload: {simulation!r}')
if simulation.get('module') != 'orders' or simulation.get('status') != 'simulated-filled':
    raise SystemExit(f'unexpected simulation payload: {simulation!r}')
PY
}

assert_live_mode_rejection() {
  local api_port="$1"
  local api_url="http://127.0.0.1:${api_port}"
  local live_status_code
  local live_simulation_code

  live_status_code="$(curl --silent --output "$live_status_file" --write-out '%{http_code}' "$api_url/api/broker/ibkr/status")"
  live_simulation_code="$(curl --silent --header 'Content-Type: application/json' --data '{"symbol":"AAPL","side":"Buy","quantity":1,"orderType":"Market"}' --output "$live_simulation_file" --write-out '%{http_code}' "$api_url/api/orders/simulate")"

  [[ "$live_status_code" == '200' ]]
  [[ "$live_simulation_code" == '409' ]]

  python3 - <<'PY' "$live_status_file" "$live_simulation_file"
import json, sys
from pathlib import Path
status = json.loads(Path(sys.argv[1]).read_text())
simulation = json.loads(Path(sys.argv[2]).read_text())
if status.get('state') != 'rejected-live-mode' or status.get('mode') != 'live':
    raise SystemExit(f'live mode must be rejected before any broker action: {status!r}')
if simulation.get('simulated') is not False or 'Only Paper is supported' not in simulation.get('error', ''):
    raise SystemExit(f'live mode simulation must reject cleanly: {simulation!r}')
PY
}

main() {
  health_file="$(mktemp)"
  overview_file="$(mktemp)"
  status_file="$(mktemp)"
  simulation_file="$(mktemp)"
  second_simulation_file="$(mktemp)"
  live_status_file="$(mktemp)"
  live_simulation_file="$(mktemp)"

  atrade_load_local_port_contract "$repo_root"
  assert_default_contract_and_references
  run_build_and_unit_checks

  local default_port
  default_port="$(allocate_api_port)"
  start_api false Paper "$default_port"
  assert_default_mode_endpoints "$default_port"
  stop_api

  local live_port
  live_port="$(allocate_api_port)"
  start_api true Live "$live_port"
  assert_live_mode_rejection "$live_port"
}

main "$@"
