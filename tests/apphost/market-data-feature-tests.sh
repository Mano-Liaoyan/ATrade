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

start_api_without_real_credentials() {
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"

  api_log="$(mktemp)"
  health_file="$(mktemp)"
  response_file="$(mktemp)"

  ATRADE_BROKER_INTEGRATION_ENABLED=true \
  ATRADE_BROKER_ACCOUNT_MODE=Paper \
  ATRADE_IBKR_GATEWAY_URL=http://127.0.0.1:5000 \
  ATRADE_IBKR_GATEWAY_PORT=5000 \
  ATRADE_IBKR_GATEWAY_IMAGE=voyz/ibeam:latest \
  ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS=1 \
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
    printf 'expected GET /health to return HTTP 200, got %s\n' "$health_code" >&2
    cat "$api_log" >&2
    return 1
  fi

  if [[ "$(cat "$health_file")" != 'ok' ]]; then
    printf 'expected GET /health to return ok, got %s\n' "$(cat "$health_file")" >&2
    return 1
  fi
}

assert_provider_unavailable_response() {
  local path="$1"
  local status_code

  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url$path")"
  if [[ "$status_code" != '503' ]]; then
    printf 'expected %s to return HTTP 503 provider-not-configured without credentials, got %s\n' "$path" "$status_code" >&2
    cat "$response_file" >&2
    cat "$api_log" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
if payload.get("code") != "provider-not-configured":
    raise SystemExit(f"expected provider-not-configured response, got {payload!r}")
message = payload.get("message", "")
if "IBKR" not in message or "iBeam" not in message:
    raise SystemExit(f"provider-not-configured response must explain IBKR/iBeam state: {payload!r}")
for forbidden in ("mock", "IBKR_USERNAME", "IBKR_PASSWORD", "IBKR_ACCOUNT_ID"):
    if forbidden in json.dumps(payload):
        raise SystemExit(f"provider-unavailable response contained forbidden fake/catalog/credential value: {forbidden}")
PY
}

assert_market_data_source_contract() {
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
  local api_program="$repo_root/src/ATrade.Api/Program.cs"
  local market_data_project="$repo_root/src/ATrade.MarketData/ATrade.MarketData.csproj"
  local ibkr_project="$repo_root/src/ATrade.MarketData.Ibkr/ATrade.MarketData.Ibkr.csproj"

  assert_file_contains "$repo_root/ATrade.slnx" 'ATrade.MarketData.Ibkr'
  assert_file_contains "$api_project" 'ATrade.MarketData.Ibkr.csproj'
  assert_file_contains "$api_project" 'ATrade.MarketData.csproj'
  assert_file_contains "$market_data_project" 'Microsoft.AspNetCore.App'
  assert_file_contains "$ibkr_project" 'ATrade.Brokers.Ibkr.csproj'
  assert_file_contains "$api_program" 'builder.Services.AddMarketDataModule();'
  assert_file_contains "$api_program" 'builder.Services.AddIbkrMarketDataProvider();'
  assert_file_contains "$api_program" '/api/market-data/trending'
  assert_file_contains "$api_program" 'app.MapHub<MarketDataHub>("/hubs/market-data");'
  assert_file_contains "$repo_root/src/ATrade.MarketData/MarketDataModels.cs" 'string Source = "provider"'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs" 'IbkrMarketDataSource.History'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs" 'IbkrMarketDataSource.Snapshot'
  assert_file_not_contains "$repo_root/src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs" 'MockMarketData'
  assert_file_not_contains "$repo_root/frontend/components/TrendingList.tsx" 'Mocked factors'
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for market-data-feature-tests.sh\n' >&2
    return 1
  fi

  assert_market_data_source_contract
  dotnet build "$repo_root/ATrade.slnx" --nologo --verbosity minimal >/dev/null
  start_api_without_real_credentials
  assert_provider_unavailable_response '/api/market-data/trending'
  assert_provider_unavailable_response '/api/market-data/UNCONFIGURED/candles?timeframe=1D'
  assert_provider_unavailable_response '/api/market-data/UNCONFIGURED/indicators?timeframe=1D'
}

main "$@"
