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
timescale_data_volume=''
timescale_password=''
declare -a created_container_ids=()

fresh_symbol='TPV035'
stale_symbol='TPS035'
fresh_source='ibkr-ibeam-history'
trending_source='ibkr-ibeam-scanner:STK.US.MAJOR:TOP_PERC_GAIN'

cleanup() {
  stop_apphost_session || true

  if command -v docker >/dev/null 2>&1; then
    if [[ -n "$postgres_data_volume" ]]; then
      docker volume rm "$postgres_data_volume" >/dev/null 2>&1 || true
    fi
    if [[ -n "$timescale_data_volume" ]]; then
      docker volume rm "$timescale_data_volume" >/dev/null 2>&1 || true
    fi
  fi

  if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
    rm -rf "$temp_dir"
  fi
}

trap cleanup EXIT

skip_without_container_engine() {
  if ! command -v docker >/dev/null 2>&1; then
    printf 'SKIP: docker CLI is not available; skipping AppHost Timescale cache volume verification.\n'
    exit 0
  fi

  if ! docker version >/dev/null 2>&1; then
    printf 'SKIP: no healthy Docker-compatible engine is available; skipping AppHost Timescale cache volume verification.\n'
    exit 0
  fi
}

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf '%s is required for apphost-timescale-cache-volume-tests.sh\n' "$tool" >&2
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
  local prefix="$1"
  local candidate=''

  for _ in $(seq 1 20); do
    candidate="${prefix}-$(date +%s)-$$-$RANDOM"
    if ! docker volume inspect "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  printf 'failed to allocate a unique temporary volume name for %s\n' "$prefix" >&2
  return 1
}

print_debug_state() {
  if [[ -n "$apphost_log" && -f "$apphost_log" ]]; then
    printf '\n=== AppHost log tail ===\n' >&2
    tail -n 180 "$apphost_log" >&2 || true
  fi

  if [[ ${#created_container_ids[@]} -gt 0 ]]; then
    printf '\n=== Created container state ===\n' >&2
    local id
    for id in "${created_container_ids[@]}"; do
      docker inspect "$id" --format '{{.Name}} {{.Config.Image}} Status={{.State.Status}} ExitCode={{.State.ExitCode}} Mounts={{range .Mounts}}{{.Name}}:{{.Destination}}:{{.RW}} {{end}}' >&2 || true
      printf -- '--- logs for %s ---\n' "$id" >&2
      docker logs "$id" 2>&1 | tail -n 100 >&2 || true
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
      fail_with_debug 'AppHost exited before the Timescale cache volume test observed its infrastructure containers.'
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

assert_database_uses_test_volume() {
  local image="$1"
  local resource_name="$2"
  local expected_volume="$3"
  local container_id
  local matching_mount

  container_id="$(find_created_container_by_image "$image")" || fail_with_debug "Failed to find the AppHost-managed $resource_name container."
  matching_mount="$(docker inspect "$container_id" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}} {{.RW}}{{end}}{{end}}')"

  if [[ "$matching_mount" != "$expected_volume true" ]]; then
    fail_with_debug "Expected $resource_name to mount writable test volume '$expected_volume' at /var/lib/postgresql/data, got '$matching_mount'."
  fi
}

get_timescaledb_container_id() {
  find_created_container_by_image 'docker.io/timescale/timescaledb:latest-pg17' || fail_with_debug 'Failed to find the AppHost-managed timescaledb container.'
}

wait_for_timescaledb_ready() {
  local timescaledb_id
  timescaledb_id="$(get_timescaledb_container_id)"

  for _ in $(seq 1 90); do
    if docker exec -e PGPASSWORD="$timescale_password" "$timescaledb_id" pg_isready -U postgres -d postgres >/dev/null 2>&1; then
      return 0
    fi

    if ! kill -0 "$apphost_pid" 2>/dev/null; then
      fail_with_debug 'AppHost exited while waiting for TimescaleDB readiness.'
    fi

    sleep 1
  done

  fail_with_debug 'Timed out waiting for AppHost-managed TimescaleDB to accept connections.'
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
      ATRADE_TIMESCALEDB_DATA_VOLUME="$timescale_data_volume" \
      ATRADE_TIMESCALEDB_PASSWORD="$timescale_password" \
      ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES=5 \
      ATRADE_BROKER_INTEGRATION_ENABLED=false \
      ATRADE_ANALYSIS_ENGINE=none \
      ATRADE_IBKR_USERNAME=IBKR_USERNAME \
      ATRADE_IBKR_PASSWORD=IBKR_PASSWORD \
      ATRADE_IBKR_PAPER_ACCOUNT_ID=IBKR_ACCOUNT_ID \
      ./start run >"$apphost_log" 2>&1
  ) &
  apphost_pid=$!

  wait_for_new_infra_containers "$before_ids"
  assert_database_uses_test_volume 'docker.io/library/postgres:17.6' postgres "$postgres_data_volume"
  assert_database_uses_test_volume 'docker.io/timescale/timescaledb:latest-pg17' timescaledb "$timescale_data_volume"
  wait_for_timescaledb_ready

  health_response="$(mktemp "$temp_dir/health-${session_name}-XXXXXX.response")"
  wait_for_http_200 "$api_url/health" "$health_response"
  if [[ "$(cat "$health_response")" != 'ok' ]]; then
    fail_with_debug 'Expected AppHost-managed ATrade.Api health endpoint to return ok.'
  fi
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
  local output_file="$3"
  local expected_code="$4"
  local code=''

  code="$(curl --silent --show-error --output "$output_file" --write-out '%{http_code}' \
    --request "$method" \
    --header 'Accept: application/json' \
    "$api_url$path")"

  if [[ "$code" != "$expected_code" ]]; then
    printf 'expected %s %s to return HTTP %s, got %s\n' "$method" "$path" "$expected_code" "$code" >&2
    cat "$output_file" >&2 || true
    printf '\n' >&2
    fail_with_debug 'Unexpected AppHost-managed API response.'
  fi
}

assert_market_data_error_code() {
  local response_file="$1"
  local expected_code="$2"

  python3 - "$response_file" "$expected_code" <<'PY'
import json
import sys

response_path, expected_code = sys.argv[1:]
with open(response_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)
if payload.get("code") != expected_code:
    raise SystemExit(f"expected error code {expected_code!r}, got {payload!r}")
if "source" in payload:
    raise SystemExit(f"error response must not include cache source metadata: {payload!r}")
PY
}

wait_for_market_data_schema() {
  local response_file
  local timescaledb_id
  local initialized

  response_file="$(mktemp "$temp_dir/market-data-schema-XXXXXX.json")"
  request_json GET '/api/market-data/trending' "$response_file" 503
  assert_market_data_error_code "$response_file" provider-not-configured

  timescaledb_id="$(get_timescaledb_container_id)"
  for _ in $(seq 1 30); do
    initialized="$(docker exec -e PGPASSWORD="$timescale_password" "$timescaledb_id" \
      psql -U postgres -d postgres -tAc "SELECT to_regclass('atrade_market_data.trending_snapshots') IS NOT NULL AND to_regclass('atrade_market_data.candles') IS NOT NULL;" | tr -d '[:space:]')"
    if [[ "$initialized" == 't' ]]; then
      return 0
    fi
    sleep 1
  done

  fail_with_debug 'Timed out waiting for API to initialize the Timescale market-data schema.'
}

seed_timescale_cache_rows() {
  local timescaledb_id
  timescaledb_id="$(get_timescaledb_container_id)"

  docker exec -i -e PGPASSWORD="$timescale_password" "$timescaledb_id" \
    psql -v ON_ERROR_STOP=1 -U postgres -d postgres >/dev/null <<SQL
INSERT INTO atrade_market_data.trending_snapshots (
  provider, source, provider_symbol_id, symbol, name, exchange, currency, asset_class, sector,
  generated_at_utc, last_price, change_percent, score, volume_spike, price_momentum, volatility,
  external_signal, reasons, created_at_utc, updated_at_utc)
VALUES (
  'ibkr', '$trending_source', 'tp035-cache-volume', '$fresh_symbol', 'TP-035 Cache Volume Corp',
  'NASDAQ', 'USD', 'STK', 'Technology', now() - interval '1 minute', 123.45, 1.23, 99.10,
  2.00, 1.50, 0.50, 0.10, '["apphost-timescale-cache-volume"]'::jsonb, now(), now())
ON CONFLICT (provider, source, symbol, generated_at_utc) DO NOTHING;

INSERT INTO atrade_market_data.candles (
  provider, source, provider_symbol_id, symbol, name, exchange, currency, asset_class, timeframe,
  candle_time_utc, generated_at_utc, open, high, low, close, volume, created_at_utc, updated_at_utc)
VALUES
  ('ibkr', '$fresh_source', 'tp035-cache-volume', '$fresh_symbol', 'TP-035 Cache Volume Corp', 'NASDAQ', 'USD', 'STK', '1D', now() - interval '3 days', now() - interval '1 minute', 100.00, 105.00, 99.00, 104.00, 1000000, now(), now()),
  ('ibkr', '$fresh_source', 'tp035-cache-volume', '$fresh_symbol', 'TP-035 Cache Volume Corp', 'NASDAQ', 'USD', 'STK', '1D', now() - interval '2 days', now() - interval '1 minute', 104.00, 108.00, 103.00, 107.00, 1100000, now(), now()),
  ('ibkr', '$fresh_source', 'tp035-cache-volume', '$fresh_symbol', 'TP-035 Cache Volume Corp', 'NASDAQ', 'USD', 'STK', '1D', now() - interval '1 day', now() - interval '1 minute', 107.00, 111.00, 106.00, 110.00, 1200000, now(), now())
ON CONFLICT (provider, source, symbol, timeframe, candle_time_utc) DO NOTHING;

INSERT INTO atrade_market_data.candles (
  provider, source, provider_symbol_id, symbol, name, exchange, currency, asset_class, timeframe,
  candle_time_utc, generated_at_utc, open, high, low, close, volume, created_at_utc, updated_at_utc)
VALUES
  ('ibkr', '$fresh_source', 'tp035-cache-volume-stale', '$stale_symbol', 'TP-035 Stale Cache Corp', 'NASDAQ', 'USD', 'STK', '1D', now() - interval '3 days', now() - interval '30 minutes', 50.00, 51.00, 49.00, 50.50, 900000, now(), now()),
  ('ibkr', '$fresh_source', 'tp035-cache-volume-stale', '$stale_symbol', 'TP-035 Stale Cache Corp', 'NASDAQ', 'USD', 'STK', '1D', now() - interval '2 days', now() - interval '30 minutes', 50.50, 52.00, 50.00, 51.50, 950000, now(), now())
ON CONFLICT (provider, source, symbol, timeframe, candle_time_utc) DO NOTHING;
SQL
}

assert_trending_cache_response() {
  local response_file="$1"

  python3 - "$response_file" "$fresh_symbol" "$trending_source" <<'PY'
import json
import sys

response_path, expected_symbol, expected_source = sys.argv[1:]
with open(response_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)
expected_cache_source = f"timescale-cache:{expected_source}"
if payload.get("source") != expected_cache_source:
    raise SystemExit(f"expected trending source {expected_cache_source!r}, got {payload!r}")
symbols = payload.get("symbols") or []
if not any(symbol.get("symbol") == expected_symbol for symbol in symbols):
    raise SystemExit(f"expected trending symbols to include {expected_symbol!r}, got {payload!r}")
PY
}

assert_candle_cache_response() {
  local response_file="$1"

  python3 - "$response_file" "$fresh_symbol" "$fresh_source" <<'PY'
import json
import sys

response_path, expected_symbol, expected_source = sys.argv[1:]
with open(response_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)
expected_cache_source = f"timescale-cache:{expected_source}"
if payload.get("source") != expected_cache_source:
    raise SystemExit(f"expected candle source {expected_cache_source!r}, got {payload!r}")
if payload.get("symbol") != expected_symbol:
    raise SystemExit(f"expected candle symbol {expected_symbol!r}, got {payload!r}")
if len(payload.get("candles") or []) < 3:
    raise SystemExit(f"expected persisted candles in response, got {payload!r}")
PY
}

assert_post_reboot_cache_responses() {
  local trending_response="$1"
  local candle_response="$2"
  local stale_response="$3"

  request_json GET '/api/market-data/trending' "$trending_response" 200
  assert_trending_cache_response "$trending_response"

  request_json GET "/api/market-data/${fresh_symbol}/candles?timeframe=1D" "$candle_response" 200
  assert_candle_cache_response "$candle_response"

  request_json GET "/api/market-data/${stale_symbol}/candles?timeframe=1D" "$stale_response" 503
  assert_market_data_error_code "$stale_response" provider-not-configured
}

main() {
  skip_without_container_engine
  require_tool curl
  require_tool dotnet
  require_tool python3

  temp_dir="$(mktemp -d)"
  postgres_data_volume="$(unique_volume_name atrade-postgres-timescale-cache-test)"
  postgres_password="ATradePostgresTimescaleCacheTestPassword${RANDOM}${RANDOM}"
  timescale_data_volume="$(unique_volume_name atrade-timescaledb-cache-volume-test)"
  timescale_password="ATradeTimescaleCacheVolumeTestPassword${RANDOM}${RANDOM}"

  local first_api_port
  local second_api_port
  local frontend_direct_port
  local apphost_frontend_port
  local first_trending_response
  local first_candle_response
  local first_stale_response
  local reboot_trending_response
  local reboot_candle_response
  local reboot_stale_response

  first_api_port="$(free_port)"
  second_api_port="$(free_port)"
  frontend_direct_port="$(free_port)"
  apphost_frontend_port="$(free_port)"
  first_trending_response="$(mktemp "$temp_dir/first-trending-XXXXXX.json")"
  first_candle_response="$(mktemp "$temp_dir/first-candles-XXXXXX.json")"
  first_stale_response="$(mktemp "$temp_dir/first-stale-XXXXXX.json")"
  reboot_trending_response="$(mktemp "$temp_dir/reboot-trending-XXXXXX.json")"
  reboot_candle_response="$(mktemp "$temp_dir/reboot-candles-XXXXXX.json")"
  reboot_stale_response="$(mktemp "$temp_dir/reboot-stale-XXXXXX.json")"

  start_apphost_session first "$first_api_port" "$frontend_direct_port" "$apphost_frontend_port"
  wait_for_market_data_schema
  seed_timescale_cache_rows
  assert_post_reboot_cache_responses "$first_trending_response" "$first_candle_response" "$first_stale_response"
  stop_apphost_session

  start_apphost_session second "$second_api_port" "$frontend_direct_port" "$apphost_frontend_port"
  assert_post_reboot_cache_responses "$reboot_trending_response" "$reboot_candle_response" "$reboot_stale_response"

  printf 'AppHost Timescale cache persistence verified across full AppHost restart using isolated volume %s.\n' "$timescale_data_volume"
}

main "$@"
