#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
docker_label_filter='label=com.microsoft.developer.usvc-dev.group-version=usvc-dev.developer.microsoft.com/v1'

apphost_pid=''
apphost_log=''
temp_dir=''
api_url=''
postgres_data_volume=''
postgres_password=''
declare -a created_container_ids=()

aapl_nasdaq_key='provider=ibkr|providerSymbolId=265598|ibkrConid=265598|symbol=AAPL|exchange=NASDAQ|currency=USD|assetClass=STK'
aapl_lse_key='provider=ibkr|providerSymbolId=493546048|ibkrConid=493546048|symbol=AAPL|exchange=LSE|currency=GBP|assetClass=STK'
msft_nasdaq_key='provider=ibkr|providerSymbolId=272093|ibkrConid=272093|symbol=MSFT|exchange=NASDAQ|currency=USD|assetClass=STK'

cleanup() {
  stop_apphost_session || true

  if [[ -n "$postgres_data_volume" ]]; then
    docker volume rm "$postgres_data_volume" >/dev/null 2>&1 || true
  fi

  if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
    rm -rf "$temp_dir"
  fi
}

trap cleanup EXIT

skip_without_container_engine() {
  if ! command -v docker >/dev/null 2>&1; then
    printf 'SKIP: docker CLI is not available; skipping AppHost Postgres watchlist volume verification.\n'
    exit 0
  fi

  if ! docker version >/dev/null 2>&1; then
    printf 'SKIP: no healthy Docker-compatible engine is available; skipping AppHost Postgres watchlist volume verification.\n'
    exit 0
  fi
}

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf '%s is required for apphost-postgres-watchlist-volume-tests.sh\n' "$tool" >&2
    return 1
  fi
}

free_port() {
  python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

unique_volume_name() {
  local candidate=''

  for _ in $(seq 1 20); do
    candidate="atrade-postgres-watchlist-volume-test-$(date +%s)-$$-$RANDOM"
    if ! docker volume inspect "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  printf 'failed to allocate a unique temporary Postgres volume name\n' >&2
  return 1
}

print_debug_state() {
  if [[ -n "$apphost_log" && -f "$apphost_log" ]]; then
    printf '\n=== AppHost log tail ===\n' >&2
    tail -n 160 "$apphost_log" >&2 || true
  fi

  if [[ ${#created_container_ids[@]} -gt 0 ]]; then
    printf '\n=== Created container state ===\n' >&2
    local id
    for id in "${created_container_ids[@]}"; do
      docker inspect "$id" --format '{{.Name}} {{.Config.Image}} Status={{.State.Status}} ExitCode={{.State.ExitCode}} Mounts={{range .Mounts}}{{.Name}}:{{.Destination}}:{{.RW}} {{end}}' >&2 || true
      printf -- '--- logs for %s ---\n' "$id" >&2
      docker logs "$id" 2>&1 | tail -n 80 >&2 || true
    done
  fi
}

fail_with_debug() {
  printf '%s\n' "$1" >&2
  print_debug_state
  exit 1
}

capture_new_container_ids() {
  local before_ids="$1"
  local current_ids
  local new_ids

  current_ids="$(docker ps -aq --filter "$docker_label_filter" | sort || true)"
  new_ids="$(comm -13 <(printf '%s\n' "$before_ids") <(printf '%s\n' "$current_ids") | sed '/^$/d' || true)"

  created_container_ids=()
  if [[ -n "$new_ids" ]]; then
    mapfile -t created_container_ids < <(printf '%s\n' "$new_ids")
  fi
}

wait_for_new_infra_containers() {
  local before_ids="$1"

  for _ in $(seq 1 90); do
    sleep 1

    if ! kill -0 "$apphost_pid" 2>/dev/null; then
      fail_with_debug 'AppHost exited before the watchlist volume test observed its infrastructure containers.'
    fi

    capture_new_container_ids "$before_ids"
    if [[ ${#created_container_ids[@]} -ge 4 ]]; then
      return 0
    fi
  done

  fail_with_debug 'Timed out waiting for AppHost-managed infrastructure containers.'
}

find_created_container_by_image() {
  local image="$1"
  local id

  for id in "${created_container_ids[@]}"; do
    if [[ "$(docker inspect "$id" --format '{{.Config.Image}}')" == "$image" ]]; then
      printf '%s\n' "$id"
      return 0
    fi
  done

  return 1
}

assert_postgres_uses_test_volume() {
  local postgres_id
  local matching_mount

  postgres_id="$(find_created_container_by_image 'docker.io/library/postgres:17.6')" || fail_with_debug 'Failed to find the AppHost-managed postgres container.'
  matching_mount="$(docker inspect "$postgres_id" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}} {{.RW}}{{end}}{{end}}')"

  if [[ "$matching_mount" != "$postgres_data_volume true" ]]; then
    fail_with_debug "Expected postgres to mount writable test volume '$postgres_data_volume' at /var/lib/postgresql/data, got '$matching_mount'."
  fi
}

wait_for_http_200() {
  local url="$1"
  local output_file="$2"
  local code=''

  for _ in $(seq 1 180); do
    code="$(curl --silent --output "$output_file" --write-out '%{http_code}' "$url" || true)"
    if [[ "$code" == '200' ]]; then
      return 0
    fi

    if ! kill -0 "$apphost_pid" 2>/dev/null; then
      fail_with_debug "AppHost exited before $url returned HTTP 200."
    fi

    sleep 1
  done

  fail_with_debug "Expected $url to return HTTP 200, got $code."
}

wait_for_watchlist_available() {
  local output_file="$1"
  local code=''

  for _ in $(seq 1 180); do
    code="$(curl --silent --show-error --output "$output_file" --write-out '%{http_code}' \
      --header 'Accept: application/json' \
      "$api_url/api/workspace/watchlist" || true)"
    if [[ "$code" == '200' ]]; then
      return 0
    fi

    if ! kill -0 "$apphost_pid" 2>/dev/null; then
      fail_with_debug 'AppHost exited before the watchlist API became available.'
    fi

    sleep 1
  done

  printf 'expected GET /api/workspace/watchlist to become available, got HTTP %s\n' "$code" >&2
  cat "$output_file" >&2 || true
  printf '\n' >&2
  fail_with_debug 'Timed out waiting for AppHost-managed watchlist API storage readiness.'
}

start_apphost_session() {
  local session_name="$1"
  local api_port="$2"
  local frontend_direct_port="$3"
  local apphost_frontend_port="$4"
  local before_ids
  local health_response

  before_ids="$(docker ps -aq --filter "$docker_label_filter" | sort || true)"
  apphost_log="$(mktemp "$temp_dir/apphost-${session_name}-XXXXXX.log")"
  api_url="http://127.0.0.1:${api_port}"

  (
    cd "$repo_root"
    ATRADE_API_HTTP_PORT="$api_port" \
      ATRADE_FRONTEND_DIRECT_HTTP_PORT="$frontend_direct_port" \
      ATRADE_APPHOST_FRONTEND_HTTP_PORT="$apphost_frontend_port" \
      ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=0 \
      ATRADE_POSTGRES_DATA_VOLUME="$postgres_data_volume" \
      ATRADE_POSTGRES_PASSWORD="$postgres_password" \
      ATRADE_BROKER_INTEGRATION_ENABLED=false \
      ATRADE_ANALYSIS_ENGINE=none \
      ATRADE_IBKR_USERNAME=IBKR_USERNAME \
      ATRADE_IBKR_PASSWORD=IBKR_PASSWORD \
      ATRADE_IBKR_PAPER_ACCOUNT_ID=IBKR_ACCOUNT_ID \
      ./start run >"$apphost_log" 2>&1
  ) &
  apphost_pid=$!

  wait_for_new_infra_containers "$before_ids"
  assert_postgres_uses_test_volume

  health_response="$(mktemp "$temp_dir/health-${session_name}-XXXXXX.response")"
  wait_for_http_200 "$api_url/health" "$health_response"
  if [[ "$(cat "$health_response")" != 'ok' ]]; then
    fail_with_debug 'Expected AppHost-managed ATrade.Api health endpoint to return ok.'
  fi

  wait_for_watchlist_available "$(mktemp "$temp_dir/watchlist-ready-${session_name}-XXXXXX.json")"
}

stop_apphost_session() {
  if [[ -n "$apphost_pid" ]] && kill -0 "$apphost_pid" 2>/dev/null; then
    kill "$apphost_pid" 2>/dev/null || true
    wait "$apphost_pid" 2>/dev/null || true
  fi
  apphost_pid=''

  if [[ ${#created_container_ids[@]} -gt 0 ]]; then
    docker rm -f "${created_container_ids[@]}" >/dev/null 2>&1 || true
  fi
  created_container_ids=()
}

request_json() {
  local method="$1"
  local path="$2"
  local payload="$3"
  local output_file="$4"
  local expected_code="$5"
  local code=''

  if [[ -n "$payload" ]]; then
    code="$(curl --silent --show-error --output "$output_file" --write-out '%{http_code}' \
      --request "$method" \
      --header 'Accept: application/json' \
      --header 'Content-Type: application/json' \
      --data "$payload" \
      "$api_url$path")"
  else
    code="$(curl --silent --show-error --output "$output_file" --write-out '%{http_code}' \
      --request "$method" \
      --header 'Accept: application/json' \
      "$api_url$path")"
  fi

  if [[ "$code" != "$expected_code" ]]; then
    printf 'expected %s %s to return HTTP %s, got %s\n' "$method" "$path" "$expected_code" "$code" >&2
    cat "$output_file" >&2 || true
    printf '\n' >&2
    fail_with_debug 'Unexpected AppHost-managed API response.'
  fi
}

assert_watchlist_keys_exactly() {
  local response_file="$1"
  shift

  python3 - "$response_file" "$@" <<'PY'
import json
import sys

response_path = sys.argv[1]
expected = sorted(sys.argv[2:])
with open(response_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)
actual = sorted(entry.get("instrumentKey") for entry in payload.get("symbols", []))
if actual != expected:
    raise SystemExit(f"expected watchlist keys {expected!r}, got {actual!r}: {payload!r}")
PY
}

assert_symbol_metadata_by_key() {
  local response_file="$1"
  local instrument_key="$2"
  local symbol="$3"
  local provider="$4"
  local provider_symbol_id="$5"
  local ibkr_conid="$6"
  local name="$7"
  local exchange="$8"
  local currency="$9"
  local asset_class="${10}"

  python3 - "$response_file" "$instrument_key" "$symbol" "$provider" "$provider_symbol_id" "$ibkr_conid" "$name" "$exchange" "$currency" "$asset_class" <<'PY'
import json
import sys

response_path, expected_key, expected_symbol, expected_provider, expected_provider_symbol_id, expected_ibkr_conid, expected_name, expected_exchange, expected_currency, expected_asset_class = sys.argv[1:]
with open(response_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

matches = [entry for entry in payload.get("symbols", []) if entry.get("instrumentKey") == expected_key]
if len(matches) != 1:
    raise SystemExit(f"expected one entry for {expected_key}, got {matches!r} in {payload!r}")
entry = matches[0]
expected = {
    "symbol": expected_symbol,
    "pinKey": expected_key,
    "provider": expected_provider,
    "providerSymbolId": expected_provider_symbol_id,
    "ibkrConid": int(expected_ibkr_conid),
    "name": expected_name,
    "exchange": expected_exchange,
    "currency": expected_currency,
    "assetClass": expected_asset_class,
}
for key, value in expected.items():
    if entry.get(key) != value:
        raise SystemExit(f"expected {expected_key}.{key}={value!r}, got {entry.get(key)!r} in {entry!r}")
PY
}

pin_watchlist_entries() {
  local response_file="$1"

  request_json POST '/api/workspace/watchlist' '{"symbol":"AAPL","provider":"ibkr","providerSymbolId":"265598","ibkrConid":265598,"name":"Apple Inc.","exchange":"NASDAQ","currency":"USD","assetClass":"STK"}' "$response_file" 200
  request_json POST '/api/workspace/watchlist' '{"symbol":"AAPL","provider":"ibkr","providerSymbolId":"493546048","ibkrConid":493546048,"name":"Apple Inc.","exchange":"LSE","currency":"GBP","assetClass":"STK"}' "$response_file" 200
  request_json POST '/api/workspace/watchlist' '{"symbol":"MSFT","provider":"ibkr","providerSymbolId":"272093","ibkrConid":272093,"name":"Microsoft Corp.","exchange":"NASDAQ","currency":"USD","assetClass":"STK"}' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file" "$aapl_nasdaq_key" "$aapl_lse_key" "$msft_nasdaq_key"
}

assert_persisted_watchlist_entries() {
  local response_file="$1"

  request_json GET '/api/workspace/watchlist' '' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file" "$aapl_nasdaq_key" "$aapl_lse_key" "$msft_nasdaq_key"
  assert_symbol_metadata_by_key "$response_file" "$aapl_nasdaq_key" AAPL ibkr 265598 265598 'Apple Inc.' NASDAQ USD STK
  assert_symbol_metadata_by_key "$response_file" "$aapl_lse_key" AAPL ibkr 493546048 493546048 'Apple Inc.' LSE GBP STK
  assert_symbol_metadata_by_key "$response_file" "$msft_nasdaq_key" MSFT ibkr 272093 272093 'Microsoft Corp.' NASDAQ USD STK
}

main() {
  skip_without_container_engine
  require_tool curl
  require_tool dotnet
  require_tool python3

  temp_dir="$(mktemp -d)"
  postgres_data_volume="$(unique_volume_name)"
  postgres_password="ATradePostgresVolumeTestPassword${RANDOM}${RANDOM}"

  local first_api_port
  local second_api_port
  local frontend_direct_port
  local apphost_frontend_port
  local response_file

  first_api_port="$(free_port)"
  second_api_port="$(free_port)"
  frontend_direct_port="$(free_port)"
  apphost_frontend_port="$(free_port)"
  response_file="$(mktemp "$temp_dir/watchlist-XXXXXX.json")"

  start_apphost_session first "$first_api_port" "$frontend_direct_port" "$apphost_frontend_port"
  request_json GET '/api/workspace/watchlist' '' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file"
  pin_watchlist_entries "$response_file"
  stop_apphost_session

  start_apphost_session second "$second_api_port" "$frontend_direct_port" "$apphost_frontend_port"
  assert_persisted_watchlist_entries "$response_file"

  printf 'AppHost Postgres watchlist persistence verified across full AppHost restart using isolated volume %s.\n' "$postgres_data_volume"
}

main "$@"
