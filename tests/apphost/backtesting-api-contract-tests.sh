#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
postgres_image='postgres:17.6'
postgres_password='atrade_backtesting_test_password'
postgres_db='atrade_backtesting_test'
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

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf '%s is required for backtesting-api-contract-tests.sh\n' "$tool" >&2
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

assert_file_not_contains() {
  local file_path="$1"
  local needle="$2"

  if grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

fail_with_logs() {
  printf '%s\n' "$1" >&2

  if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
    printf '\n=== API log tail ===\n' >&2
    find "$temp_dir" -name 'api-*.log' -print -exec tail -n 160 {} \; >&2 || true
  fi

  if [[ -n "$postgres_container" ]]; then
    printf '\n=== Postgres container logs ===\n' >&2
    docker logs "$postgres_container" 2>&1 | tail -n 120 >&2 || true
  fi

  return 1
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

request_json() {
  local method="$1"
  local path="$2"
  local payload_file="$3"
  local output_file="$4"
  local expected_code="$5"
  local code

  if [[ -n "$payload_file" ]]; then
    code="$(curl --silent --show-error --output "$output_file" --write-out '%{http_code}' \
      --request "$method" \
      --header 'Accept: application/json' \
      --header 'Content-Type: application/json' \
      --data @"$payload_file" \
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

start_api() {
  local api_port="$1"
  local postgres_port="$2"
  local api_log
  local health_response
  local connection_string="Host=127.0.0.1;Port=${postgres_port};Database=${postgres_db};Username=postgres;Password=${postgres_password};Include Error Detail=true"

  api_url="http://127.0.0.1:${api_port}"
  api_log="$(mktemp "$temp_dir/api-log-XXXXXX")"
  health_response="$(mktemp "$temp_dir/health-response-XXXXXX")"

  ASPNETCORE_URLS="$api_url" \
    ATRADE_IBKR_INTEGRATION_ENABLED='false' \
    ATRADE_ANALYSIS_ENGINE='none' \
    ConnectionStrings__postgres="$connection_string" \
    dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  wait_for_http_200 "$api_url/health" "$health_response"
  if [[ "$(cat "$health_response")" != 'ok' ]]; then
    fail_with_logs 'Expected ATrade.Api health endpoint to return ok.'
    return 1
  fi
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

start_postgres() {
  local postgres_port="$1"
  postgres_container="atrade-backtesting-test-$RANDOM-$RANDOM"

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

write_valid_backtest_request() {
  local file_path="$1"
  cat >"$file_path" <<'JSON'
{
  "symbol": {
    "symbol": "AAPL",
    "provider": "ibkr",
    "providerSymbolId": "265598",
    "assetClass": "STK",
    "exchange": "NASDAQ",
    "currency": "USD"
  },
  "strategyId": "sma-crossover",
  "parameters": {
    "fastPeriod": 20,
    "slowPeriod": 50
  },
  "chartRange": "1y",
  "costModel": {
    "commissionPerTrade": 0,
    "commissionBps": 0,
    "currency": "USD"
  },
  "slippageBps": 0,
  "benchmarkMode": "none"
}
JSON
}

write_direct_bars_request() {
  local file_path="$1"
  cat >"$file_path" <<'JSON'
{
  "symbolCode": "AAPL",
  "strategyId": "sma-crossover",
  "parameters": {},
  "chartRange": "1y",
  "bars": [
    { "time": "2026-05-01T14:30:00Z", "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000 }
  ]
}
JSON
}

write_sensitive_request() {
  local file_path="$1"
  cat >"$file_path" <<'JSON'
{
  "symbolCode": "AAPL",
  "strategyId": "sma-crossover",
  "parameters": {},
  "chartRange": "1y",
  "accountId": "DU1234567",
  "gatewayUrl": "https://127.0.0.1:5000"
}
JSON
}

assert_no_sensitive_response_values() {
  local response_file="$1"
  if grep -Eiq 'PAPER_TEST_ACCOUNT|DU[0-9]{4,}|password|secret|token|cookie|session|https?://' "$response_file"; then
    printf 'backtest response leaked a sensitive value:\n' >&2
    cat "$response_file" >&2
    return 1
  fi
}

assert_error_payload() {
  local response_file="$1"
  local expected_code="$2"
  python3 - "$response_file" "$expected_code" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
assert payload["code"] == sys.argv[2], payload
assert "DU1234567" not in payload.get("message", ""), payload
assert "https://" not in payload.get("message", "").lower(), payload
assert "password" not in payload.get("message", "").lower(), payload
assert "token" not in payload.get("message", "").lower(), payload
PY
  assert_no_sensitive_response_values "$response_file"
}

assert_created_run_payload() {
  local response_file="$1"
  local expected_status="$2"
  local expected_source_run_id="${3:-}"
  python3 - "$response_file" "$expected_status" "$expected_source_run_id" <<'PY'
import json, sys
from decimal import Decimal
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
expected_status = sys.argv[2]
expected_source_run_id = sys.argv[3] or None
assert payload["id"].startswith("bt_"), payload
assert payload["status"] == expected_status, payload
assert payload.get("sourceRunId") == expected_source_run_id, payload
request = payload["request"]
assert request["symbol"]["symbol"] == "AAPL", payload
assert request["symbol"]["provider"] == "ibkr", payload
assert request["strategyId"] == "sma-crossover", payload
assert request["chartRange"] == "1y", payload
assert "bars" not in request, payload
assert "accountId" not in request, payload
capital = payload["capital"]
assert Decimal(str(capital["initialCapital"])) == Decimal("100000.13"), payload
assert capital["currency"] == "USD", payload
assert capital["capitalSource"] == "local-paper-ledger", payload
assert payload.get("result") is None, payload
PY
  assert_no_sensitive_response_values "$response_file"
}

extract_run_id() {
  local response_file="$1"
  python3 - "$response_file" <<'PY'
import json, sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["id"])
PY
}

assert_list_contains_run() {
  local response_file="$1"
  local expected_id="$2"
  python3 - "$response_file" "$expected_id" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
expected_id = sys.argv[2]
assert isinstance(payload, list), payload
assert any(item.get("id") == expected_id for item in payload), payload
for item in payload:
    assert "account" not in json.dumps(item).lower(), item
PY
  assert_no_sensitive_response_values "$response_file"
}

assert_schema_and_rows_exclude_sensitive_values() {
  local sensitive_column_count
  local sensitive_request_count

  sensitive_column_count="$(docker exec -e PGPASSWORD="$postgres_password" "$postgres_container" \
    psql -U postgres -d "$postgres_db" -tAc "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'atrade_backtesting' AND table_name = 'saved_backtest_runs' AND (column_name ILIKE '%account%' OR column_name ILIKE '%credential%' OR column_name ILIKE '%password%' OR column_name ILIKE '%secret%' OR column_name ILIKE '%token%' OR column_name ILIKE '%cookie%' OR column_name ILIKE '%session%' OR column_name ILIKE '%gateway%' OR column_name ILIKE '%url%' OR column_name ILIKE '%bars%' OR column_name ILIKE '%candles%');" | tr -d '[:space:]')"

  if [[ "$sensitive_column_count" != '0' ]]; then
    fail_with_logs 'Backtesting saved-run schema must not persist sensitive or direct-bar columns.'
    return 1
  fi

  sensitive_request_count="$(docker exec -e PGPASSWORD="$postgres_password" "$postgres_container" \
    psql -U postgres -d "$postgres_db" -tAc "SELECT count(*) FROM atrade_backtesting.saved_backtest_runs WHERE request_json::text ~* '(account|DU[0-9]{4,}|credential|password|secret|token|cookie|session|gateway|https?://|bars|candles)';" | tr -d '[:space:]')"

  if [[ "$sensitive_request_count" != '0' ]]; then
    fail_with_logs 'Backtesting saved-run request snapshots must not contain sensitive values or direct bars.'
    return 1
  fi
}

validate_source_contract() {
  local api_program="$repo_root/src/ATrade.Api/Program.cs"
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
  local backtesting_project="$repo_root/src/ATrade.Backtesting/ATrade.Backtesting.csproj"
  local module_extensions="$repo_root/src/ATrade.Backtesting/BacktestingModuleServiceCollectionExtensions.cs"
  local contracts="$repo_root/src/ATrade.Backtesting/BacktestingContracts.cs"
  local repository="$repo_root/src/ATrade.Backtesting/BacktestRunRepository.cs"

  assert_file_contains "$repo_root/ATrade.slnx" 'ATrade.Backtesting'
  assert_file_contains "$api_project" 'ATrade.Backtesting.csproj'
  assert_file_contains "$backtesting_project" 'ATrade.Accounts.csproj'
  assert_file_contains "$backtesting_project" 'ATrade.MarketData.csproj'
  assert_file_contains "$module_extensions" 'AddBacktestingModule'
  assert_file_contains "$module_extensions" 'IBacktestRunRepository'
  assert_file_contains "$api_program" 'builder.Services.AddBacktestingModule(builder.Configuration);'
  assert_file_contains "$api_program" '"/api/backtests"'
  assert_file_contains "$api_program" '"/api/backtests/{id}"'
  assert_file_contains "$api_program" '"/api/backtests/{id}/cancel"'
  assert_file_contains "$api_program" '"/api/backtests/{id}/retry"'
  assert_file_contains "$contracts" 'BacktestRunStatuses'
  assert_file_contains "$contracts" 'BacktestCapitalSnapshot'
  assert_file_contains "$repository" 'CreateRetryAsync'
  assert_file_contains "$repository" 'BacktestPersistenceSafety.SerializeRequestSnapshot'
  assert_file_not_contains "$api_program" 'accountId'
  assert_file_not_contains "$api_program" 'GatewayBaseUrl'
  assert_file_not_contains "$api_program" 'Password'
}

run_with_postgres_checks() {
  if ! command -v docker >/dev/null 2>&1; then
    printf 'SKIP: docker CLI is not available; skipping Postgres-backed backtesting API checks.\n'
    return 0
  fi

  if ! docker version >/dev/null 2>&1; then
    printf 'SKIP: no healthy Docker-compatible engine is available; skipping Postgres-backed backtesting API checks.\n'
    return 0
  fi

  local postgres_port
  local api_port
  local valid_request
  local direct_bars_request
  local sensitive_request
  local response
  local created_id
  local retry_id

  postgres_port="$(free_port)"
  start_postgres "$postgres_port"

  api_port="$(free_port)"
  start_api "$api_port" "$postgres_port"

  valid_request="$(mktemp "$temp_dir/backtest-valid-XXXXXX.json")"
  direct_bars_request="$(mktemp "$temp_dir/backtest-direct-bars-XXXXXX.json")"
  sensitive_request="$(mktemp "$temp_dir/backtest-sensitive-XXXXXX.json")"
  write_valid_backtest_request "$valid_request"
  write_direct_bars_request "$direct_bars_request"
  write_sensitive_request "$sensitive_request"

  response="$(mktemp "$temp_dir/backtest-missing-capital-XXXXXX.json")"
  request_json POST '/api/backtests' "$valid_request" "$response" 409
  assert_error_payload "$response" 'backtest-capital-unavailable'

  response="$(mktemp "$temp_dir/backtest-direct-bars-response-XXXXXX.json")"
  request_json POST '/api/backtests' "$direct_bars_request" "$response" 400
  assert_error_payload "$response" 'backtest-forbidden-field'

  response="$(mktemp "$temp_dir/backtest-sensitive-response-XXXXXX.json")"
  request_json POST '/api/backtests' "$sensitive_request" "$response" 400
  assert_error_payload "$response" 'backtest-forbidden-field'

  response="$(mktemp "$temp_dir/backtest-not-found-XXXXXX.json")"
  request_json GET '/api/backtests/bt_missing' '' "$response" 404
  assert_error_payload "$response" 'backtest-run-not-found'

  response="$(mktemp "$temp_dir/paper-capital-set-XXXXXX.json")"
  request_json PUT '/api/accounts/local-paper-capital' <(printf '{"amount":100000.129,"currency":"usd"}') "$response" 200
  assert_no_sensitive_response_values "$response"

  response="$(mktemp "$temp_dir/backtest-created-XXXXXX.json")"
  request_json POST '/api/backtests' "$valid_request" "$response" 202
  assert_created_run_payload "$response" 'queued'
  created_id="$(extract_run_id "$response")"

  response="$(mktemp "$temp_dir/backtest-list-XXXXXX.json")"
  request_json GET '/api/backtests?limit=10' '' "$response" 200
  assert_list_contains_run "$response" "$created_id"

  response="$(mktemp "$temp_dir/backtest-get-XXXXXX.json")"
  request_json GET "/api/backtests/$created_id" '' "$response" 200
  assert_created_run_payload "$response" 'queued'

  response="$(mktemp "$temp_dir/backtest-cancel-XXXXXX.json")"
  request_json POST "/api/backtests/$created_id/cancel" '' "$response" 200
  assert_created_run_payload "$response" 'cancelled'

  response="$(mktemp "$temp_dir/backtest-retry-XXXXXX.json")"
  request_json POST "/api/backtests/$created_id/retry" '' "$response" 202
  assert_created_run_payload "$response" 'queued' "$created_id"
  retry_id="$(extract_run_id "$response")"
  if [[ "$retry_id" == "$created_id" ]]; then
    fail_with_logs 'Retry must create a new backtest run id instead of mutating the source run.'
    return 1
  fi

  response="$(mktemp "$temp_dir/backtest-running-retry-XXXXXX.json")"
  request_json POST "/api/backtests/$retry_id/retry" '' "$response" 409
  assert_error_payload "$response" 'backtest-invalid-status-transition'

  assert_schema_and_rows_exclude_sensitive_values
}

main() {
  require_tool curl
  require_tool python3

  temp_dir="$(mktemp -d)"
  validate_source_contract
  dotnet build "$repo_root/ATrade.slnx" --nologo --verbosity minimal >/dev/null
  run_with_postgres_checks
}

main "$@"
