#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

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

assert_path_missing() {
  local file_path="$1"

  if [[ -e "$file_path" ]]; then
    printf 'expected obsolete path to be removed: %s\n' "$file_path" >&2
    return 1
  fi
}

assert_renderer_has_no_watchlist_io() {
  local file_path="$1"

  assert_file_not_contains "$file_path" "watchlistClient"
  assert_file_not_contains "$file_path" "watchlistStorage"
  assert_file_not_contains "$file_path" "createProvisionalInstrumentKey"
  assert_file_not_contains "$file_path" "readCachedWatchlist"
  assert_file_not_contains "$file_path" "writeCachedWatchlist"
  assert_file_not_contains "$file_path" "pinWatchlistSymbol"
  assert_file_not_contains "$file_path" "unpinWatchlistInstrument"
  assert_file_not_contains "$file_path" "unpinWatchlistSymbol"
}

assert_watchlist_workflow_module() {
  local workflow="$repo_root/frontend/lib/watchlistWorkflow.ts"

  assert_file_contains "$workflow" "export function useWatchlistWorkflow"
  assert_file_contains "$workflow" "getWatchlist()"
  assert_file_contains "$workflow" "migrateCachedWatchlistAfterBackendLoad"
  assert_file_contains "$workflow" "readCachedWatchlist()"
  assert_file_contains "$workflow" "markWatchlistMigrationCompleted()"
  assert_file_contains "$workflow" "formatWatchlistWorkflowError"
  assert_file_contains "$workflow" "Cached legacy pins are shown read-only"
  assert_file_contains "$workflow" "pinKeyByOptimisticKey"
  assert_file_contains "$workflow" "Backend persisted pinKey/instrumentKey values are authoritative"
  assert_file_contains "$workflow" "unpinWatchlistInstrument(authoritativePinKey)"
  assert_file_contains "$workflow" "createCachedWatchlistSymbol"
}

assert_terminal_monitor_workflow_module() {
  local workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"

  assert_file_contains "$workflow" "export function useTerminalMarketMonitorWorkflow"
  assert_file_contains "$workflow" "useSymbolSearchWorkflow({"
  assert_file_contains "$workflow" "useWatchlistWorkflow()"
  assert_file_contains "$workflow" "getTrendingSymbols()"
  assert_file_contains "$workflow" "createTerminalMarketMonitorViewModel"
  assert_file_contains "$workflow" "createTrendingMonitorRow"
  assert_file_contains "$workflow" "createSearchMonitorRow"
  assert_file_contains "$workflow" "createWatchlistMonitorRow"
  assert_file_contains "$workflow" "providerState"
  assert_file_contains "$workflow" "watchlistCachedFallback: watchlist.source === 'cache'"
  assert_file_contains "$workflow" "toggleRowPin"
  assert_file_contains "$workflow" "createChartNavigationIntent"
  assert_file_contains "$workflow" "createAnalysisNavigationIntent"
}

assert_storage_authority_boundary() {
  local storage="$repo_root/frontend/lib/watchlistStorage.ts"
  local workflow="$repo_root/frontend/lib/watchlistWorkflow.ts"

  assert_file_contains "$storage" "Legacy browser storage is intentionally symbol-only"
  assert_file_contains "$storage" "atrade.paperTrading.watchlist.v1"
  assert_file_contains "$storage" "backendMigrated"
  assert_file_contains "$workflow" "writeCachedWatchlist(response.symbols.map((symbol) => symbol.symbol))"
  assert_file_contains "$workflow" "provider: 'cache'"
  assert_file_contains "$workflow" "provider: 'manual'"
}

assert_frontend_api_boundary() {
  local market_client="$repo_root/frontend/lib/marketDataClient.ts"
  local stream_client="$repo_root/frontend/lib/marketDataStream.ts"
  local search_workflow="$repo_root/frontend/lib/symbolSearchWorkflow.ts"
  local chart_workflow="$repo_root/frontend/lib/symbolChartWorkflow.ts"

  assert_file_contains "$market_client" "buildApiUrl"
  assert_file_contains "$stream_client" "buildApiUrl('/hubs/market-data')"
  assert_file_contains "$search_workflow" "searchSymbols"
  assert_file_contains "$chart_workflow" "getCandles"
  assert_file_contains "$chart_workflow" "getIndicators"
  assert_file_contains "$chart_workflow" "connectMarketDataStream"

  if grep -RIn \
    --exclude-dir=.next \
    --exclude-dir=node_modules \
    --exclude='package-lock.json' \
    -E 'Npgsql|TimescaleConnection|PostgresConnection|Host=|User ID=|Password=|redis://|nats://|Client Portal|ibkr-gateway' \
    "$repo_root/frontend"; then
    printf 'frontend source must keep browser data access behind ATrade.Api clients.\n' >&2
    return 1
  fi
}

assert_behavioral_fallbacks() {
  local workflow="$repo_root/frontend/lib/watchlistWorkflow.ts"
  local monitor_workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"
  local market_client="$repo_root/frontend/lib/marketDataClient.ts"
  local search_workflow="$repo_root/frontend/lib/symbolSearchWorkflow.ts"
  local chart_workflow="$repo_root/frontend/lib/symbolChartWorkflow.ts"
  local monitor="$repo_root/frontend/components/terminal/TerminalMarketMonitor.tsx"
  local search="$repo_root/frontend/components/terminal/MarketMonitorSearch.tsx"
  local detail="$repo_root/frontend/components/terminal/MarketMonitorDetailPanel.tsx"
  local chart="$repo_root/frontend/components/terminal/TerminalChartWorkspace.tsx"

  assert_file_contains "$workflow" "getTrendingPinState"
  assert_file_contains "$workflow" "getSearchResultPinState"
  assert_file_contains "$workflow" "getWatchlistSymbolPinState"
  assert_file_contains "$workflow" "unpinWatchlistInstrument(authoritativePinKey)"
  assert_file_contains "$workflow" "setWatchlistSource('cache')"
  assert_file_contains "$workflow" "Cached legacy pins are shown read-only"
  assert_file_contains "$workflow" "provider: 'cache'"
  assert_file_contains "$workflow" "provider: 'manual'"

  assert_file_contains "$market_client" "provider-not-configured"
  assert_file_contains "$market_client" "provider-unavailable"
  assert_file_contains "$market_client" "authentication-required"
  assert_file_contains "$monitor" "label: 'Search'"
  assert_file_contains "$monitor" "Cached legacy pins are read-only until backend returns."
  assert_file_contains "$monitor_workflow" "formatTerminalMarketMonitorError"
  assert_file_contains "$search" "Search unavailable"
  assert_file_contains "$search_workflow" "IBKR stock search is unavailable."
  assert_file_contains "$chart" "IBKR chart data unavailable."
  assert_file_contains "$chart_workflow" "IBKR chart data is unavailable."
  assert_file_contains "$detail" "No row selected."

  assert_file_contains "$chart_workflow" "connectMarketDataStream"
  assert_file_contains "$chart_workflow" "startPollingFallback"
  assert_file_contains "$chart_workflow" "window.setInterval(() => void refreshChartData(false)"
  assert_file_contains "$chart_workflow" "state === 'closed'"
  assert_file_contains "$chart" "polling continues against the IBKR/iBeam HTTP provider"
}

assert_renderer_boundaries() {
  local terminal_app="$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx"
  local monitor="$repo_root/frontend/components/terminal/TerminalMarketMonitor.tsx"
  local table="$repo_root/frontend/components/terminal/MarketMonitorTable.tsx"
  local detail="$repo_root/frontend/components/terminal/MarketMonitorDetailPanel.tsx"
  local search="$repo_root/frontend/components/terminal/MarketMonitorSearch.tsx"
  local filters="$repo_root/frontend/components/terminal/MarketMonitorFilters.tsx"

  assert_file_contains "$terminal_app" "TerminalMarketMonitor"
  assert_file_contains "$terminal_app" "onOpenIntent={onOpenIntent}"
  assert_file_contains "$monitor" "useTerminalMarketMonitorWorkflow"
  assert_file_contains "$monitor" "MarketMonitorTable"
  assert_file_contains "$monitor" "MarketMonitorDetailPanel"
  assert_file_contains "$table" "TerminalMarketMonitorRow"
  assert_file_contains "$detail" "TerminalMarketMonitorRow"
  assert_file_contains "$search" "MarketMonitorSearch"
  assert_file_contains "$filters" "MarketMonitorFilterOrder"

  for renderer in "$terminal_app" "$monitor" "$table" "$detail" "$search" "$filters"; do
    assert_renderer_has_no_watchlist_io "$renderer"
  done

  assert_path_missing "$repo_root/frontend/components/SymbolSearch.tsx"
  assert_path_missing "$repo_root/frontend/components/TrendingList.tsx"
  assert_path_missing "$repo_root/frontend/components/Watchlist.tsx"
}

main() {
  assert_watchlist_workflow_module
  assert_terminal_monitor_workflow_module
  assert_storage_authority_boundary
  assert_frontend_api_boundary
  assert_behavioral_fallbacks
  assert_renderer_boundaries
}

main "$@"
