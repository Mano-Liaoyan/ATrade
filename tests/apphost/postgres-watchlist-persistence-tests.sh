#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
postgres_image='postgres:17.6'
postgres_password='atrade_watchlist_test_password'
postgres_db='atrade_watchlist_test'
postgres_container=''
api_pid=''
api_url=''
temp_dir=''

cleanup() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  if [[ -n "$postgres_container" ]]; then
    docker rm -f "$postgres_container" >/dev/null 2>&1 || true
  fi

  if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
    rm -rf "$temp_dir"
  fi
}

trap cleanup EXIT

skip_without_container_engine() {
  if ! command -v docker >/dev/null 2>&1; then
    printf 'SKIP: docker CLI is not available; skipping Postgres watchlist persistence verification.\n'
    exit 0
  fi

  if ! docker version >/dev/null 2>&1; then
    printf 'SKIP: no healthy Docker-compatible engine is available; skipping Postgres watchlist persistence verification.\n'
    exit 0
  fi
}

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf '%s is required for postgres-watchlist-persistence-tests.sh\n' "$tool" >&2
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

urlencode() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import quote
print(quote(sys.argv[1], safe=""))
PY
}

fail_with_logs() {
  printf '%s\n' "$1" >&2

  if [[ -n "$api_pid" && -d "$temp_dir" ]]; then
    printf '\n=== API log tail ===\n' >&2
    find "$temp_dir" -name 'api-*.log' -print -exec tail -n 120 {} \; >&2 || true
  fi

  if [[ -n "$postgres_container" ]]; then
    printf '\n=== Postgres container logs ===\n' >&2
    docker logs "$postgres_container" 2>&1 | tail -n 120 >&2 || true
  fi

  return 1
}

wait_for_postgres() {
  for _ in $(seq 1 60); do
    if docker exec -e PGPASSWORD="$postgres_password" "$postgres_container" pg_isready -U postgres -d "$postgres_db" >/dev/null 2>&1; then
      return 0
    fi

    sleep 1
  done

  fail_with_logs 'Timed out waiting for disposable Postgres to accept connections.'
}

wait_for_http_200() {
  local url="$1"
  local output_file="$2"
  local code=''

  for _ in $(seq 1 120); do
    code="$(curl --silent --output "$output_file" --write-out '%{http_code}' "$url" || true)"
    if [[ "$code" == '200' ]]; then
      return 0
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
      fail_with_logs "ATrade.Api exited before $url returned HTTP 200."
      return 1
    fi

    sleep 0.5
  done

  fail_with_logs "Expected $url to return HTTP 200, got $code."
}

start_postgres() {
  local postgres_port="$1"
  postgres_container="atrade-watchlist-test-$RANDOM-$RANDOM"

  docker run \
    --detach \
    --name "$postgres_container" \
    --pids-limit 2048 \
    --publish "127.0.0.1:${postgres_port}:5432" \
    --env POSTGRES_PASSWORD="$postgres_password" \
    --env POSTGRES_DB="$postgres_db" \
    "$postgres_image" >/dev/null

  wait_for_postgres
}

start_api() {
  local api_port="$1"
  local postgres_port="$2"
  local api_log
  local health_response
  local connection_string

  api_url="http://127.0.0.1:${api_port}"
  api_log="$(mktemp "$temp_dir/api-XXXXXX.log")"
  health_response="$(mktemp "$temp_dir/health-XXXXXX.response")"
  connection_string="Host=127.0.0.1;Port=${postgres_port};Database=${postgres_db};Username=postgres;Password=${postgres_password};Include Error Detail=true"

  ASPNETCORE_URLS="$api_url" \
    ConnectionStrings__postgres="$connection_string" \
    dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  wait_for_http_200 "$api_url/health" "$health_response"
  if [[ "$(cat "$health_response")" != 'ok' ]]; then
    fail_with_logs 'Expected ATrade.Api health endpoint to return ok.'
    return 1
  fi
}

stop_api() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  api_pid=''
}

request_json() {
  local method="$1"
  local path="$2"
  local payload="$3"
  local output_file="$4"
  local expected_code="$5"
  local code

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
    printf 'Expected %s %s to return HTTP %s, got %s. Response:\n' "$method" "$path" "$expected_code" "$code" >&2
    cat "$output_file" >&2
    printf '\n' >&2
    fail_with_logs 'Unexpected API response.'
    return 1
  fi
}

assert_schema_initialized() {
  local initialized
  initialized="$(docker exec -e PGPASSWORD="$postgres_password" "$postgres_container" \
    psql -U postgres -d "$postgres_db" -tAc "SELECT to_regclass('atrade_workspaces.workspace_watchlist_pins') IS NOT NULL;" | tr -d '[:space:]')"

  if [[ "$initialized" != 't' ]]; then
    fail_with_logs 'Expected watchlist schema table to exist after first API watchlist request.'
    return 1
  fi
}

assert_watchlist_keys_exactly() {
  local response_file="$1"
  shift

  python3 - "$response_file" "$@" <<'PY'
import json
import sys

response_path = sys.argv[1]
expected = sys.argv[2:]
with open(response_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

entries = payload.get("symbols", [])
keys = [entry.get("instrumentKey") for entry in entries]
if sorted(keys) != sorted(expected):
    raise SystemExit(f"expected instrument keys {expected}, got {keys} in {entries!r}")
for entry in entries:
    if not entry.get("instrumentKey") or not entry.get("pinKey"):
        raise SystemExit(f"expected instrumentKey and pinKey in {entry!r}")
    if entry.get("instrumentKey") != entry.get("pinKey"):
        raise SystemExit(f"pinKey must alias instrumentKey in {entry!r}")
PY
}

assert_symbol_count() {
  local response_file="$1"
  local symbol="$2"
  local expected_count="$3"

  python3 - "$response_file" "$symbol" "$expected_count" <<'PY'
import json
import sys

response_path, expected_symbol, expected_count = sys.argv[1:]
with open(response_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)
count = sum(1 for entry in payload.get("symbols", []) if entry.get("symbol") == expected_symbol)
if count != int(expected_count):
    raise SystemExit(f"expected {expected_count} {expected_symbol} entries, got {count}: {payload!r}")
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

assert_error_code() {
  local response_file="$1"
  local expected_code="$2"

  python3 - "$response_file" "$expected_code" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)

if payload.get("code") != sys.argv[2]:
    raise SystemExit(f"expected {sys.argv[2]} code, got {payload!r}")
if not payload.get("error"):
    raise SystemExit(f"expected non-empty validation error message, got {payload!r}")
PY
}

main() {
  skip_without_container_engine
  require_tool curl
  require_tool dotnet
  require_tool python3

  temp_dir="$(mktemp -d)"
  local postgres_port
  local api_port
  local response_file
  local invalid_response_file
  local ambiguous_response_file
  postgres_port="$(free_port)"
  api_port="$(free_port)"
  response_file="$(mktemp "$temp_dir/watchlist-XXXXXX.json")"
  invalid_response_file="$(mktemp "$temp_dir/invalid-XXXXXX.json")"
  ambiguous_response_file="$(mktemp "$temp_dir/ambiguous-XXXXXX.json")"

  local aapl_nasdaq_key='provider=ibkr|providerSymbolId=265598|ibkrConid=265598|symbol=AAPL|exchange=NASDAQ|currency=USD|assetClass=STK'
  local aapl_lse_key='provider=ibkr|providerSymbolId=493546048|ibkrConid=493546048|symbol=AAPL|exchange=LSE|currency=GBP|assetClass=STK'
  local msft_nasdaq_key='provider=ibkr|providerSymbolId=272093|ibkrConid=272093|symbol=MSFT|exchange=NASDAQ|currency=USD|assetClass=STK'

  start_postgres "$postgres_port"
  start_api "$api_port" "$postgres_port"

  request_json GET '/api/workspace/watchlist' '' "$response_file" 200
  assert_schema_initialized
  assert_watchlist_keys_exactly "$response_file"

  request_json POST '/api/workspace/watchlist' '{"symbol":"AAPL","provider":"ibkr","providerSymbolId":"265598","ibkrConid":265598,"name":"Apple Inc.","exchange":"NASDAQ","currency":"USD","assetClass":"STK"}' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file" "$aapl_nasdaq_key"
  assert_symbol_metadata_by_key "$response_file" "$aapl_nasdaq_key" AAPL ibkr 265598 265598 'Apple Inc.' NASDAQ USD STK

  request_json POST '/api/workspace/watchlist' '{"symbol":"AAPL","provider":"ibkr","providerSymbolId":"493546048","ibkrConid":493546048,"name":"Apple Inc.","exchange":"LSE","currency":"GBP","assetClass":"STK"}' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file" "$aapl_nasdaq_key" "$aapl_lse_key"
  assert_symbol_count "$response_file" AAPL 2
  assert_symbol_metadata_by_key "$response_file" "$aapl_lse_key" AAPL ibkr 493546048 493546048 'Apple Inc.' LSE GBP STK

  request_json DELETE '/api/workspace/watchlist/AAPL' '' "$ambiguous_response_file" 400
  assert_error_code "$ambiguous_response_file" ambiguous-symbol
  request_json GET '/api/workspace/watchlist' '' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file" "$aapl_nasdaq_key" "$aapl_lse_key"

  request_json DELETE "/api/workspace/watchlist/pins/$(urlencode "$aapl_lse_key")" '' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file" "$aapl_nasdaq_key"
  assert_symbol_count "$response_file" AAPL 1

  request_json POST '/api/workspace/watchlist' '{"symbol":"AAPL","provider":"ibkr","providerSymbolId":"493546048","ibkrConid":493546048,"name":"Apple Inc.","exchange":"LSE","currency":"GBP","assetClass":"STK"}' "$response_file" 200
  request_json POST '/api/workspace/watchlist' '{"symbol":"MSFT","provider":"ibkr","providerSymbolId":"272093","ibkrConid":272093,"name":"Microsoft Corp.","exchange":"NASDAQ","currency":"USD","assetClass":"STK"}' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file" "$aapl_nasdaq_key" "$aapl_lse_key" "$msft_nasdaq_key"

  request_json POST '/api/workspace/watchlist' '{"symbol":"not a valid symbol"}' "$invalid_response_file" 400
  assert_error_code "$invalid_response_file" invalid-symbol

  stop_api
  start_api "$api_port" "$postgres_port"

  request_json GET '/api/workspace/watchlist' '' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file" "$aapl_nasdaq_key" "$aapl_lse_key" "$msft_nasdaq_key"
  assert_symbol_metadata_by_key "$response_file" "$aapl_nasdaq_key" AAPL ibkr 265598 265598 'Apple Inc.' NASDAQ USD STK
  assert_symbol_metadata_by_key "$response_file" "$aapl_lse_key" AAPL ibkr 493546048 493546048 'Apple Inc.' LSE GBP STK
  assert_symbol_metadata_by_key "$response_file" "$msft_nasdaq_key" MSFT ibkr 272093 272093 'Microsoft Corp.' NASDAQ USD STK

  request_json DELETE "/api/workspace/watchlist/pins/$(urlencode "$aapl_nasdaq_key")" '' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file" "$aapl_lse_key" "$msft_nasdaq_key"
  assert_symbol_count "$response_file" AAPL 1

  request_json DELETE '/api/workspace/watchlist/MSFT' '' "$response_file" 200
  assert_watchlist_keys_exactly "$response_file" "$aapl_lse_key"

  printf 'Postgres watchlist exact instrument persistence verified across API restart.\n'
}

main "$@"
