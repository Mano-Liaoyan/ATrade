#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$repo_root/scripts/local-env.sh"

export ATRADE_API_HTTP_PORT="$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"
atrade_load_local_port_contract "$repo_root"

api_pid=''
api_log=''
health_file=''
response_file=''
api_url="http://127.0.0.1:${ATRADE_API_HTTP_PORT}"

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

  if [[ -f "$file_path" ]] && grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

cleanup() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  for temp_file in "$api_log" "$health_file" "$response_file"; do
    if [[ -n "$temp_file" && -f "$temp_file" ]]; then
      rm -f "$temp_file"
    fi
  done
}

trap cleanup EXIT

start_api_without_ibkr_credentials() {
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"

  api_log="$(mktemp)"
  health_file="$(mktemp)"
  response_file="$(mktemp)"

  ATRADE_BROKER_INTEGRATION_ENABLED=true \
  ATRADE_BROKER_ACCOUNT_MODE=Paper \
  ATRADE_IBKR_GATEWAY_URL=http://127.0.0.1:5000 \
  ATRADE_IBKR_GATEWAY_PORT=5000 \
  ATRADE_IBKR_GATEWAY_IMAGE=voyz/ibeam:latest \
  ATRADE_IBKR_USERNAME=IBKR_USERNAME \
  ATRADE_IBKR_PASSWORD=IBKR_PASSWORD \
  ATRADE_IBKR_PAPER_ACCOUNT_ID=IBKR_ACCOUNT_ID \
  ASPNETCORE_URLS="$api_url" dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  local attempt
  local health_code=''
  for attempt in {1..60}; do
    health_code="$(curl --silent --show-error --output "$health_file" --write-out '%{http_code}' "$api_url/health" || true)"
    if [[ "$health_code" == '200' ]]; then
      break
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
      printf 'ATrade.Api exited before becoming healthy.\n' >&2
      cat "$api_log" >&2
      return 1
    fi

    sleep 0.5
  done

  if [[ "$health_code" != '200' ]]; then
    printf 'expected API health endpoint to return HTTP 200, got %s\n' "$health_code" >&2
    cat "$api_log" >&2
    return 1
  fi
}

assert_market_data_provider_source_contract() {
  assert_file_contains "$repo_root/ATrade.slnx" 'ATrade.MarketData.Ibkr'
  assert_file_contains "$repo_root/src/ATrade.Api/ATrade.Api.csproj" 'ATrade.MarketData.Ibkr.csproj'
  assert_file_contains "$repo_root/src/ATrade.Api/Program.cs" 'AddIbkrMarketDataProvider'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs" '/v1/api/iserver/secdef/search'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs" '/v1/api/iserver/marketdata/snapshot'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs" '/v1/api/iserver/marketdata/history'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs" '/v1/api/iserver/scanner/run'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs" 'IbkrMarketDataSource.Scanner'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs" 'UsesMockData: false'
  assert_file_not_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs" 'Environment.GetEnvironmentVariable'
  assert_file_not_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs" 'ATRADE_IBKR_PASSWORD'
  assert_file_not_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs" 'ATRADE_IBKR_USERNAME'
}

assert_api_returns_provider_unavailable_without_credentials() {
  local status_code
  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/market-data/trending")"
  if [[ "$status_code" != '503' ]]; then
    printf 'expected no-credential trending endpoint to return HTTP 503, got %s\n' "$status_code" >&2
    cat "$response_file" >&2
    cat "$api_log" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
if payload.get("code") != "provider-not-configured":
    raise SystemExit(f"expected provider-not-configured error, got {payload!r}")
message = payload.get("message", "")
if "IBKR" not in message or "iBeam" not in message:
    raise SystemExit(f"expected IBKR/iBeam unavailable message, got {payload!r}")
for forbidden in ("IBKR_USERNAME", "IBKR_PASSWORD", "IBKR_ACCOUNT_ID"):
    if forbidden in json.dumps(payload):
        raise SystemExit(f"provider-unavailable response leaked placeholder credential: {forbidden}")
PY
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for ibkr-market-data-provider-tests.sh\n' >&2
    return 1
  fi

  assert_market_data_provider_source_contract
  dotnet test "$repo_root/tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj" --nologo --verbosity minimal
  start_api_without_ibkr_credentials
  assert_api_returns_provider_unavailable_without_credentials
}

main "$@"
