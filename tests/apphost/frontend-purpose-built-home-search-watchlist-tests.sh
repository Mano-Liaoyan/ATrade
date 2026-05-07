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

assert_distinct_module_components() {
  local app="$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx"
  local home="$repo_root/frontend/components/terminal/TerminalHomeModule.tsx"
  local search="$repo_root/frontend/components/terminal/TerminalSearchModule.tsx"
  local watchlist="$repo_root/frontend/components/terminal/TerminalWatchlistModule.tsx"

  assert_file_contains "$app" 'import { TerminalHomeModule } from "./TerminalHomeModule";'
  assert_file_contains "$app" 'import { TerminalSearchModule } from "./TerminalSearchModule";'
  assert_file_contains "$app" 'import { TerminalWatchlistModule } from "./TerminalWatchlistModule";'
  assert_file_contains "$app" 'return <TerminalHomeModule onOpenIntent={onOpenIntent} searchQuery={searchQuery} />;'
  assert_file_contains "$app" 'return <TerminalSearchModule onOpenIntent={onOpenIntent} searchQuery={searchQuery} />;'
  assert_file_contains "$app" 'return <TerminalWatchlistModule onOpenIntent={onOpenIntent} />;'

  assert_file_not_contains "$app" 'function TerminalHomeModule'
  assert_file_not_contains "$app" 'function TerminalSearchModule'
  assert_file_not_contains "$app" 'function TerminalWatchlistModule'
  assert_file_not_contains "$app" '<TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent} title="Home market monitor" />'
  assert_file_not_contains "$app" '<TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent} title={searchQuery ? `Search monitor · ${searchQuery}` : "Search market monitor"} />'
  assert_file_not_contains "$app" '<TerminalMarketMonitor onOpenIntent={onOpenIntent} title="Watchlist market monitor" />'

  assert_file_not_contains "$home" '<TerminalMarketMonitor'
  assert_file_not_contains "$search" '<TerminalMarketMonitor'
  assert_file_not_contains "$watchlist" '<TerminalMarketMonitor'
}

assert_home_dashboard() {
  local home="$repo_root/frontend/components/terminal/TerminalHomeModule.tsx"
  local css="$repo_root/frontend/app/globals.css"

  assert_file_contains "$home" 'data-testid="terminal-home-module"'
  assert_file_contains "$home" 'Home dashboard'
  assert_file_contains "$home" 'Paper trading command overview'
  assert_file_contains "$home" 'data-testid="terminal-home-status-grid"'
  assert_file_contains "$home" 'ATrade.Api boundary'
  assert_file_contains "$home" 'API only'
  assert_file_contains "$home" 'Paper only · no orders'
  assert_file_contains "$home" 'data-testid="terminal-home-quick-actions"'
  assert_file_contains "$home" "label: '/search'"
  assert_file_contains "$home" "label: '/watchlist'"
  assert_file_contains "$home" "label: '/chart'"
  assert_file_contains "$home" "label: '/analysis'"
  assert_file_contains "$home" "label: '/backtest'"
  assert_file_contains "$home" "label: '/status'"
  assert_file_contains "$home" 'terminal-home-preview-grid'
  assert_file_contains "$home" 'Provider trending preview'
  assert_file_contains "$home" 'Watchlist preview'
  assert_file_contains "$home" 'No provider trending rows are available; Home does not substitute demo symbols.'
  assert_file_contains "$home" 'No backend-stored stocks are saved yet. Use Search to pin exact provider instruments.'
  assert_file_contains "$home" '<TerminalProviderDiagnostics'
  assert_file_not_contains "$home" 'hard-coded'
  assert_file_not_contains "$home" 'synthetic market data'
  assert_file_contains "$home" 'Orders are disabled by the paper-only safety contract.'
  assert_file_not_contains "$home" 'Buy ticket'
  assert_file_not_contains "$home" 'Sell ticket'

  assert_file_contains "$css" '.terminal-home-status-grid'
  assert_file_contains "$css" '.terminal-home-quick-actions'
  assert_file_contains "$css" '.terminal-home-preview-grid'
}

assert_search_first_workflow() {
  local search="$repo_root/frontend/components/terminal/TerminalSearchModule.tsx"
  local input="$repo_root/frontend/components/terminal/MarketMonitorSearch.tsx"
  local workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"
  local css="$repo_root/frontend/app/globals.css"

  assert_file_contains "$search" 'data-testid="terminal-search-module"'
  assert_file_contains "$search" 'Search-first workflow'
  assert_file_contains "$search" 'Bounded stock search'
  assert_file_contains "$search" 'data-testid="terminal-search-primary-workflow"'
  assert_file_contains "$search" 'initialSelectedFilters: { source: '\''search'\'' }'
  assert_file_contains "$search" '<MarketMonitorSearch'
  assert_file_contains "$search" 'autoFocus'
  assert_file_contains "$search" '<MarketMonitorFilters'
  assert_file_contains "$search" '<MarketMonitorTable'
  assert_file_contains "$search" '<MarketMonitorDetailPanel'
  assert_file_contains "$search" '<MarketMonitorExplorationControls'
  assert_file_contains "$search" 'workflow.toggleRowPin(row)'
  assert_file_contains "$search" 'workflow.openChartIntent(row)'
  assert_file_contains "$search" 'workflow.openAnalysisIntent(row)'
  assert_file_contains "$search" 'workflow.openBacktestIntent(row)'
  assert_file_contains "$search" 'Source: Search'
  assert_file_contains "$input" 'data-search-focus={autoFocus ? '\''primary'\'' : undefined}'
  assert_file_contains "$input" 'autoFocus={autoFocus}'
  assert_file_contains "$input" 'Bounded IBKR stock search'
  assert_file_contains "$workflow" 'initialSelectedFilters?: TerminalMarketMonitorSelectedFilters;'
  assert_file_contains "$workflow" 'normalizeMonitorFilters(initialSelectedFilters)'
  assert_file_contains "$css" '.terminal-search-module__primary-search'
}

assert_watchlist_first_workflow() {
  local watchlist="$repo_root/frontend/components/terminal/TerminalWatchlistModule.tsx"
  local table="$repo_root/frontend/components/terminal/MarketMonitorTable.tsx"
  local detail="$repo_root/frontend/components/terminal/MarketMonitorDetailPanel.tsx"
  local css="$repo_root/frontend/app/globals.css"

  assert_file_contains "$watchlist" 'data-testid="terminal-watchlist-module"'
  assert_file_contains "$watchlist" 'data-testid="terminal-watchlist-saved-first-workflow"'
  assert_file_contains "$watchlist" 'Saved-stocks workflow'
  assert_file_contains "$watchlist" 'Backend watchlist pins'
  assert_file_contains "$watchlist" "initialSelectedFilters: { source: 'watchlist' }"
  assert_file_contains "$watchlist" 'data-watchlist-source={workflow.watchlist.source}'
  assert_file_contains "$watchlist" 'Backend stored pins first.'
  assert_file_contains "$watchlist" 'Add stocks in Search'
  assert_file_contains "$watchlist" 'Retry watchlist'
  assert_file_contains "$watchlist" 'No saved stocks yet'
  assert_file_contains "$watchlist" 'Backend pins cannot be loaded'
  assert_file_contains "$watchlist" '<MarketMonitorFilters'
  assert_file_contains "$watchlist" '<MarketMonitorTable'
  assert_file_contains "$watchlist" '<MarketMonitorDetailPanel'
  assert_file_contains "$watchlist" 'workflow.toggleRowPin(row)'
  assert_file_contains "$watchlist" 'workflow.openChartIntent(row)'
  assert_file_contains "$watchlist" 'workflow.openAnalysisIntent(row)'
  assert_file_contains "$watchlist" 'workflow.openBacktestIntent(row)'
  assert_file_contains "$watchlist" 'Source: Watchlist'
  assert_file_contains "$table" "row.saved ? 'Unpin' : 'Pin'"
  assert_file_contains "$detail" 'Remove exact pin'
  assert_file_contains "$detail" 'data-testid="market-monitor-exact-identity"'
  assert_file_contains "$css" '.terminal-watchlist-module__summary'
}

main() {
  assert_distinct_module_components
  assert_home_dashboard
  assert_search_first_workflow
  assert_watchlist_first_workflow
}

main "$@"
