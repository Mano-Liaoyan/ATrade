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

stop_frontend_lock_owner() {
  local lock_file="$repo_root/frontend/.next/dev/lock"
  local locked_pid=''

  if [[ ! -f "$lock_file" ]]; then
    return 0
  fi

  locked_pid="$(python3 - "$lock_file" <<'PY'
import json
import sys
try:
    with open(sys.argv[1], encoding='utf-8') as handle:
        value = json.load(handle).get('pid', '')
    print(value if isinstance(value, int) else '')
except Exception:
    print('')
PY
)"

  if [[ "$locked_pid" =~ ^[0-9]+$ ]] && kill -0 "$locked_pid" 2>/dev/null; then
    kill "$locked_pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$locked_pid" 2>/dev/null; then
      kill -9 "$locked_pid" 2>/dev/null || true
    fi
  fi

  rm -f "$lock_file" 2>/dev/null || true
}

cleanup() {
  if [[ -n "$frontend_pid" ]]; then
    pkill -TERM -P "$frontend_pid" 2>/dev/null || true
    if kill -0 "$frontend_pid" 2>/dev/null; then
      kill "$frontend_pid" 2>/dev/null || true
      wait "$frontend_pid" 2>/dev/null || true
    fi
    pkill -KILL -P "$frontend_pid" 2>/dev/null || true
  fi

  stop_frontend_lock_owner

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
  assert_file_contains "$repo_root/frontend/lib/watchlistStorage.ts" 'Legacy browser storage is intentionally symbol-only'
  assert_file_contains "$repo_root/frontend/lib/watchlistWorkflow.ts" 'getWatchlist()'
  assert_file_contains "$repo_root/frontend/lib/watchlistWorkflow.ts" 'pinWatchlistSymbol'
  assert_file_contains "$repo_root/frontend/lib/watchlistWorkflow.ts" 'unpinWatchlistInstrument(authoritativePinKey)'
  assert_file_contains "$repo_root/frontend/lib/watchlistWorkflow.ts" 'Cached legacy pins are shown read-only'
  assert_file_contains "$repo_root/frontend/lib/watchlistWorkflow.ts" 'Boolean(watchlistError)'
  assert_file_contains "$repo_root/frontend/lib/watchlistClient.ts" 'instrumentKey: string'
  assert_file_contains "$repo_root/frontend/lib/watchlistClient.ts" 'pinKey: string'
  assert_file_contains "$repo_root/frontend/lib/watchlistClient.ts" 'createWatchlistInstrumentKey'
  assert_file_contains "$repo_root/frontend/lib/watchlistClient.ts" '/api/workspace/watchlist/pins/'

  assert_file_contains "$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts" 'useTerminalMarketMonitorWorkflow'
  assert_file_contains "$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts" 'useSymbolSearchWorkflow({'
  assert_file_contains "$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts" 'useWatchlistWorkflow()'
  assert_file_contains "$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts" 'getTrendingSymbols()'
  assert_file_contains "$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts" 'createChartNavigationIntent'
  assert_file_contains "$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts" 'createAnalysisNavigationIntent'
  assert_file_contains "$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx" 'TerminalMarketMonitor'
  assert_file_contains "$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx" 'Market monitor owns provider state'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalMarketMonitor.tsx" 'data-testid="terminal-market-monitor"'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalMarketMonitor.tsx" 'Backend-owned exact Postgres pins through ATrade.Api.'
  assert_file_contains "$repo_root/frontend/components/terminal/MarketMonitorSearch.tsx" 'data-testid="market-monitor-search-input"'
  assert_file_contains "$repo_root/frontend/components/terminal/MarketMonitorSearch.tsx" 'Bounded IBKR stock search'
  assert_file_contains "$repo_root/frontend/components/terminal/MarketMonitorTable.tsx" 'data-testid="market-monitor-row"'
  assert_file_contains "$repo_root/frontend/components/terminal/MarketMonitorTable.tsx" 'IBKR ${providerSymbolId}'
  assert_file_contains "$repo_root/frontend/components/terminal/MarketMonitorDetailPanel.tsx" 'data-testid="market-monitor-exact-identity"'
  assert_file_contains "$repo_root/frontend/components/terminal/MarketMonitorDetailPanel.tsx" 'Pin key'
  assert_file_contains "$repo_root/frontend/app/globals.css" '.terminal-market-monitor'
  assert_file_contains "$repo_root/frontend/app/globals.css" '.market-monitor-table'

  for obsolete in \
    "$repo_root/frontend/components/SymbolSearch.tsx" \
    "$repo_root/frontend/components/TrendingList.tsx" \
    "$repo_root/frontend/components/Watchlist.tsx" \
    "$repo_root/frontend/components/MarketLogo.tsx"; do
    if [[ -e "$obsolete" ]]; then
      printf 'expected obsolete list component to be removed: %s\n' "$obsolete" >&2
      return 1
    fi
  done

  assert_file_contains "$repo_root/frontend/lib/marketDataClient.ts" '/api/market-data/search'
  assert_file_contains "$repo_root/frontend/types/marketData.ts" 'MarketDataSymbolSearchResult'
  assert_file_contains "$repo_root/frontend/components/CandlestickChart.tsx" 'data-testid="candlestick-chart"'
  assert_file_contains "$repo_root/frontend/types/marketData.ts" "'1min', '5mins', '1h', '6h', '1D', '1m', '6m', '1y', '5y', 'all'"
  assert_file_contains "$repo_root/frontend/types/marketData.ts" 'externalSignal'
  assert_file_contains "$repo_root/frontend/types/marketData.ts" 'source: string'
  assert_file_contains "$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx" 'useTerminalChartWorkspaceWorkflow'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalInstrumentHeader.tsx" 'Chart range lookback controls'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalChartWorkspace.tsx" 'TerminalIndicatorGrid'
  assert_file_not_contains "$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx" 'connectMarketDataStream'
  assert_file_not_contains "$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx" 'fallbackTimer = window.setInterval'
  assert_file_contains "$repo_root/frontend/lib/symbolChartWorkflow.ts" 'connectMarketDataStream'
  assert_file_contains "$repo_root/frontend/lib/symbolChartWorkflow.ts" 'fallbackTimer = window.setInterval'
  assert_file_contains "$repo_root/frontend/lib/symbolChartWorkflow.ts" 'formatMarketDataSourceLabel'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalProviderDiagnostics.tsx" 'Diagnostics only — the workspace renders no order-entry controls and does not call broker order routes.'
  assert_file_contains "$repo_root/frontend/types/analysis.ts" 'AnalysisResult'
  assert_file_contains "$repo_root/frontend/lib/analysisClient.ts" '/api/analysis/engines'
  assert_file_contains "$repo_root/frontend/lib/analysisClient.ts" '/api/analysis/run'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalAnalysisWorkspace.tsx" 'data-testid="analysis-panel"'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalAnalysisWorkspace.tsx" 'data-testid="analysis-run-button"'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalAnalysisWorkspace.tsx" 'data-testid="analysis-unavailable"'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalAnalysisWorkspace.tsx" 'data-testid="analysis-no-automation-note"'
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalAnalysisWorkspace.tsx" 'analysis-timeout'
  assert_file_contains "$repo_root/frontend/lib/terminalAnalysisWorkflow.ts" 'Analysis only — no brokerage routing or automatic order placement.'
  assert_file_contains "$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx" '<TerminalAnalysisWorkspace'
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
  if [[ "$trending_code" != '503' ]]; then
    printf 'expected market-data trending endpoint without IBKR credentials to return HTTP 503, got %s\n' "$trending_code" >&2
    cat "$api_log" >&2
    return 1
  fi
}

start_frontend_and_assert_markers() {
  stop_frontend_lock_owner

  frontend_log="$(mktemp)"
  root_response="$(mktemp)"
  chart_response="$(mktemp)"

  (
    cd "$repo_root/frontend"
    PORT="${frontend_url##*:}" NEXT_PUBLIC_ATRADE_API_BASE_URL="$api_url" npm run dev >"$frontend_log" 2>&1
  ) &
  frontend_pid=$!

  wait_for_http_200 "$frontend_url/" "$root_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$root_response" 'Paper Trading Workspace'
  assert_file_contains "$root_response" 'Module-driven paper workspace'
  assert_file_not_contains "$root_response" 'ATrade Terminal Shell'
  assert_file_not_contains "$root_response" 'Command-first paper workspace'
  assert_file_contains "$root_response" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$root_response" 'data-testid="terminal-module-rail"'
  assert_file_contains "$root_response" 'data-testid="terminal-workspace-layout"'
  assert_file_contains "$root_response" 'data-testid="terminal-market-monitor"'
  assert_file_contains "$root_response" 'Bounded IBKR stock search'
  assert_file_contains "$root_response" 'Market monitor'
  assert_file_contains "$root_response" 'Backend-owned exact Postgres pins through ATrade.Api.'
  assert_file_contains "$root_response" 'Paper-only workspace'
  assert_file_contains "$root_response" 'exact instrument identity'
  assert_file_contains "$root_response" 'Orders are disabled by the paper-only safety contract.'
  assert_file_not_contains "$root_response" 'Mocked factors'
  assert_file_not_contains "$root_response" 'Trading workspace MVP'
  assert_file_not_contains "$root_response" 'workspace-navigation'

  wait_for_http_200 "$frontend_url/symbols/AAPL" "$chart_response" "$frontend_pid" "$frontend_log"
  assert_file_contains "$chart_response" 'AAPL'
  assert_file_contains "$chart_response" 'chart workspace'
  assert_file_contains "$chart_response" 'data-testid="atrade-terminal-app"'
  assert_file_contains "$chart_response" 'data-testid="terminal-module-rail"'
  assert_file_contains "$chart_response" 'data-testid="terminal-workspace-layout"'
  assert_file_contains "$chart_response" 'data-testid="terminal-chart-module"'
  assert_file_contains "$chart_response" 'Lookback candlestick chart'
  assert_file_contains "$chart_response" 'Chart range lookback controls'
  assert_file_contains "$chart_response" '1min'
  assert_file_contains "$chart_response" '5mins'
  assert_file_contains "$chart_response" '1h'
  assert_file_contains "$chart_response" '6h'
  assert_file_contains "$chart_response" '1D'
  assert_file_contains "$chart_response" '1m'
  assert_file_contains "$chart_response" '6m'
  assert_file_contains "$chart_response" '1y'
  assert_file_contains "$chart_response" '5y'
  assert_file_contains "$chart_response" 'All time'
  assert_file_not_contains "$chart_response" '>5m<'
  assert_file_contains "$chart_response" 'SignalR'
  assert_file_contains "$chart_response" 'IBKR/iBeam'
  assert_file_contains "$chart_response" 'data-testid="terminal-analysis-workspace"'
  assert_file_contains "$chart_response" 'provider-neutral analysis'
  assert_file_contains "$chart_response" 'Analysis only'
  assert_file_not_contains "$chart_response" 'mocked'
  assert_file_contains "$chart_response" 'No orders'

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
