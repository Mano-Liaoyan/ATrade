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
export ATRADE_FRONTEND_DIRECT_HTTP_PORT="$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"
atrade_load_local_port_contract "$repo_root"

api_pid=''
frontend_pid=''
api_log=''
frontend_log=''
root_response=''
chart_response=''
api_health_response=''
api_url="http://127.0.0.1:${ATRADE_API_HTTP_PORT}"
frontend_url="http://127.0.0.1:${ATRADE_FRONTEND_DIRECT_HTTP_PORT}"

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

  if [[ -f "$file_path" ]] && grep -Fqi -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

cleanup() {
  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill "$frontend_pid" 2>/dev/null || true
    wait "$frontend_pid" 2>/dev/null || true
  fi

  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  for temp_file in "$api_log" "$frontend_log" "$root_response" "$chart_response" "$api_health_response"; do
    if [[ -n "$temp_file" && -f "$temp_file" ]]; then
      rm -f "$temp_file"
    fi
  done
}

trap cleanup EXIT

wait_for_http_200() {
  local url="$1"
  local output_file="$2"
  local pid_to_check="$3"
  local log_file="$4"
  local code=''

  for _ in {1..80}; do
    code="$(curl --silent --output "$output_file" --write-out '%{http_code}' "$url" || true)"
    if [[ "$code" == '200' ]]; then
      return 0
    fi

    if ! kill -0 "$pid_to_check" 2>/dev/null; then
      printf 'process exited before %s returned HTTP 200.\n' "$url" >&2
      cat "$log_file" >&2
      return 1
    fi

    sleep 0.5
  done

  printf 'expected %s to return HTTP 200, got %s\n' "$url" "$code" >&2
  cat "$log_file" >&2
  return 1
}

assert_frontend_dependencies_and_source() {
  local package_json="$repo_root/frontend/package.json"
  local package_lock="$repo_root/frontend/package-lock.json"

  assert_file_contains "$package_json" '"lightweight-charts"'
  assert_file_contains "$package_json" '"@microsoft/signalr"'
  assert_file_contains "$package_lock" '"node_modules/lightweight-charts"'
  assert_file_contains "$package_lock" '"node_modules/@microsoft/signalr"'

  assert_file_not_contains "$package_json" 'TradingView Charting Library'
  assert_file_not_contains "$package_json" 'charting_library'
  assert_file_not_contains "$package_lock" 'TradingView Charting Library'
  assert_file_not_contains "$package_lock" 'charting_library'

  if grep -RIn --exclude-dir=.next --exclude-dir=node_modules --exclude='package-lock.json' --exclude='package.json' 'tradingview\|charting_library' "$repo_root/frontend" | grep -Fvi 'lightweight'; then
    printf 'unexpected proprietary TradingView source reference found.\n' >&2
    return 1
  fi

  assert_file_contains "$repo_root/frontend/lib/watchlistClient.ts" '/api/workspace/watchlist'
  assert_file_contains "$repo_root/frontend/lib/watchlistClient.ts" 'buildApiUrl'
  assert_file_contains "$repo_root/frontend/lib/watchlistStorage.ts" 'atrade.paperTrading.watchlist.v1'
  assert_file_contains "$repo_root/frontend/lib/watchlistStorage.ts" 'backendMigrated'
  assert_file_contains "$repo_root/frontend/components/TradingWorkspace.tsx" 'getWatchlist'
  assert_file_contains "$repo_root/frontend/components/TradingWorkspace.tsx" 'pinWatchlistSymbol'
  assert_file_contains "$repo_root/frontend/components/TradingWorkspace.tsx" 'unpinWatchlistSymbol'
  assert_file_contains "$repo_root/frontend/components/TrendingList.tsx" 'data-testid="trending-list"'
  assert_file_contains "$repo_root/frontend/components/Watchlist.tsx" 'data-testid="watchlist-panel"'
  assert_file_contains "$repo_root/frontend/components/Watchlist.tsx" 'Backend workspace preference'
  assert_file_contains "$repo_root/frontend/components/Watchlist.tsx" 'Postgres'
  assert_file_not_contains "$repo_root/frontend/components/Watchlist.tsx" 'localStorage'
  assert_file_not_contains "$repo_root/frontend/components/Watchlist.tsx" 'Local browser preference'
  assert_file_contains "$repo_root/frontend/components/CandlestickChart.tsx" 'data-testid="candlestick-chart"'
  assert_file_contains "$repo_root/frontend/types/marketData.ts" "'1m', '5m', '1h', '1D'"
  assert_file_contains "$repo_root/frontend/components/SymbolChartView.tsx" 'connectMarketDataStream'
  assert_file_contains "$repo_root/frontend/components/SymbolChartView.tsx" 'fallbackTimer = window.setInterval'
  assert_file_contains "$repo_root/frontend/components/BrokerPaperStatus.tsx" 'No real orders'
}

assert_frontend_build() {
  (cd "$repo_root/frontend" && npm ci --no-fund --no-audit >/dev/null && npm run build)
}

start_api() {
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
  api_log="$(mktemp)"
  api_health_response="$(mktemp)"

  ASPNETCORE_URLS="$api_url" dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  wait_for_http_200 "$api_url/health" "$api_health_response" "$api_pid" "$api_log"
  if [[ "$(cat "$api_health_response")" != 'ok' ]]; then
    printf 'expected API health endpoint to return ok.\n' >&2
    cat "$api_health_response" >&2
    return 1
  fi

  local trending_code
  trending_code="$(curl --silent --output /dev/null --write-out '%{http_code}' "$api_url/api/market-data/trending")"
  if [[ "$trending_code" != '200' ]]; then
    printf 'expected market-data trending endpoint to return HTTP 200, got %s\n' "$trending_code" >&2
    cat "$api_log" >&2
    return 1
  fi
}

start_frontend_and_assert_markers() {
  frontend_log="$(mktemp)"
  root_response="$(mktemp)"
  chart_response="$(mktemp)"

  (
    cd "$repo_root/frontend"
    PORT="${frontend_url##*:}" NEXT_PUBLIC_ATRADE_API_BASE_URL="$api_url" npm run dev >"$frontend_log" 2>&1
  ) &
  frontend_pid=$!

  wait_for_http_200 "$frontend_url/" "$root_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$root_response" 'ATrade Frontend Home'
  assert_file_contains "$root_response" 'Next.js Bootstrap Slice'
  assert_file_contains "$root_response" 'Aspire AppHost Frontend Contract'
  assert_file_contains "$root_response" 'Trading workspace MVP'
  assert_file_contains "$root_response" 'backend-saved watchlists'
  assert_file_contains "$root_response" 'Postgres-backed workspace watchlists'
  assert_file_contains "$root_response" 'Loading backend-driven trending'

  wait_for_http_200 "$frontend_url/symbols/AAPL" "$chart_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$chart_response" 'AAPL'
  assert_file_contains "$chart_response" 'chart workspace'
  assert_file_contains "$chart_response" 'Interactive candlestick chart'
  assert_file_contains "$chart_response" 'Chart timeframe controls'
  assert_file_contains "$chart_response" '1m'
  assert_file_contains "$chart_response" '5m'
  assert_file_contains "$chart_response" '1h'
  assert_file_contains "$chart_response" '1D'
  assert_file_contains "$chart_response" 'SignalR'
  assert_file_contains "$chart_response" 'No real orders'
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for frontend-trading-workspace-tests.sh\n' >&2
    return 1
  fi

  assert_frontend_dependencies_and_source
  assert_frontend_build
  start_api
  start_frontend_and_assert_markers
}

main "$@"
