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

assert_terminal_monitor_workflow_exists() {
  local workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"

  assert_file_contains "$workflow" "export function useTerminalMarketMonitorWorkflow"
  assert_file_contains "$workflow" "createTerminalMarketMonitorViewModel"
  assert_file_contains "$workflow" "TerminalMarketMonitorRowSource = 'trending' | 'search' | 'watchlist'"
  assert_file_contains "$workflow" "getTrendingSymbols()"
  assert_file_contains "$workflow" "useSymbolSearchWorkflow({"
  assert_file_contains "$workflow" "useWatchlistWorkflow()"
  assert_file_contains "$workflow" "createTrendingMonitorRow"
  assert_file_contains "$workflow" "createSearchMonitorRow"
  assert_file_contains "$workflow" "createWatchlistMonitorRow"
  assert_file_contains "$workflow" "toggleRowPin"
  assert_file_contains "$workflow" "providerState"
}

assert_bounded_api_only_search() {
  local workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"
  local search_workflow="$repo_root/frontend/lib/symbolSearchWorkflow.ts"
  local market_client="$repo_root/frontend/lib/marketDataClient.ts"

  assert_file_contains "$workflow" "const boundedSearchLimit = clampSymbolSearchLimit(searchLimit);"
  assert_file_contains "$workflow" "limit: boundedSearchLimit"
  assert_file_contains "$search_workflow" "const boundedSearchLimit = clampSymbolSearchLimit(limit);"
  assert_file_contains "$search_workflow" "searchSymbols(trimmedQuery, { assetClass, limit: boundedSearchLimit })"
  assert_file_contains "$market_client" "buildApiUrl(path)"
  assert_file_contains "$market_client" "/api/market-data/search"
  assert_file_contains "$market_client" "params.set('limit', String(options.limit));"

  if grep -RIn \
    --exclude-dir=.next \
    --exclude-dir=node_modules \
    --exclude='package-lock.json' \
    --exclude='marketDataClient.ts' \
    -F '/api/market-data/search' \
    "$repo_root/frontend"; then
    printf 'frontend search requests must stay centralized in marketDataClient.searchSymbols().\n' >&2
    return 1
  fi

  if grep -RIn \
    --exclude-dir=.next \
    --exclude-dir=node_modules \
    --exclude='package-lock.json' \
    -E 'Npgsql|TimescaleConnection|PostgresConnection|Host=|User ID=|Password=|redis://|nats://|Client Portal|ibkr-gateway|iserver/secdef|iserver/scanner' \
    "$repo_root/frontend"; then
    printf 'frontend market monitor must keep browser data access behind ATrade.Api clients.\n' >&2
    return 1
  fi
}

assert_exact_identity_actions() {
  local workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"
  local monitor="$repo_root/frontend/components/terminal/TerminalMarketMonitor.tsx"
  local table="$repo_root/frontend/components/terminal/MarketMonitorTable.tsx"
  local detail="$repo_root/frontend/components/terminal/MarketMonitorDetailPanel.tsx"
  local identity="$repo_root/frontend/lib/instrumentIdentity.ts"
  local terminal_types="$repo_root/frontend/types/terminal.ts"

  assert_file_contains "$workflow" "createSymbolChartHref(identity)"
  assert_file_contains "$workflow" "params.set('module', 'ANALYSIS');"
  assert_file_contains "$workflow" "identity: row.exactIdentity"
  assert_file_contains "$workflow" "providerSymbolId: identity.providerSymbolId"
  assert_file_contains "$workflow" "exchange: identity.exchange ?? ''"
  assert_file_contains "$workflow" "assetClass: identity.assetClass"
  assert_file_contains "$workflow" "createChartNavigationIntent"
  assert_file_contains "$workflow" "createAnalysisNavigationIntent"
  assert_file_contains "$monitor" "onOpenIntent(workflow.openChartIntent(row), buildOpenStatusMessage('CHART', row))"
  assert_file_contains "$monitor" "onOpenIntent(workflow.openAnalysisIntent(row), buildOpenStatusMessage('ANALYSIS', row))"
  assert_file_contains "$table" "href={row.chartHref}"
  assert_file_contains "$table" "href={row.analysisHref}"
  assert_file_contains "$detail" "href={row.chartHref}"
  assert_file_contains "$detail" "href={row.analysisHref}"
  assert_file_contains "$identity" 'providerSymbolId=${encodeSegment(normalized.providerSymbolId)}'
  assert_file_contains "$identity" "params.set('providerSymbolId', identity.providerSymbolId);"
  assert_file_contains "$terminal_types" "identity?: MarketDataSymbolIdentity | null"
}

assert_dense_terminal_components() {
  local monitor="$repo_root/frontend/components/terminal/TerminalMarketMonitor.tsx"
  local table="$repo_root/frontend/components/terminal/MarketMonitorTable.tsx"
  local detail="$repo_root/frontend/components/terminal/MarketMonitorDetailPanel.tsx"
  local search="$repo_root/frontend/components/terminal/MarketMonitorSearch.tsx"
  local filters="$repo_root/frontend/components/terminal/MarketMonitorFilters.tsx"
  local css="$repo_root/frontend/app/globals.css"

  assert_file_contains "$monitor" "data-testid=\"terminal-market-monitor\""
  assert_file_contains "$monitor" "MarketMonitorStateStrip"
  assert_file_contains "$monitor" "workflow.statusSummary"
  assert_file_contains "$table" "data-testid=\"market-monitor-row\""
  assert_file_contains "$table" "row.rankLabel"
  assert_file_contains "$table" "row.providerSymbolId"
  assert_file_contains "$table" "row.exchange"
  assert_file_contains "$table" "row.currency"
  assert_file_contains "$table" "row.assetClass"
  assert_file_contains "$table" "row.sourceLabel"
  assert_file_contains "$table" "row.saved ? 'Saved' : 'Not saved'"
  assert_file_contains "$table" "row.saving ? 'Saving'"
  assert_file_contains "$detail" "data-testid=\"market-monitor-exact-identity\""
  assert_file_contains "$detail" "Provider ID"
  assert_file_contains "$detail" "IBKR conid"
  assert_file_contains "$detail" "Pin key"
  assert_file_contains "$search" "data-testid=\"market-monitor-search-input\""
  assert_file_contains "$filters" "data-testid=\"market-monitor-filters\""
  assert_file_contains "$filters" "Filter rows"
  assert_file_contains "$filters" "aria-label=\"Clear all market monitor filters\""
  assert_file_not_contains "$filters" "Refine by source, pin state, provider, market, currency, or asset class without fetching more than the capped search payload."
  assert_file_contains "$css" ".market-monitor-table"
  assert_file_contains "$css" "min-width: 78rem;"
  assert_file_contains "$css" "max-height: min(34rem, 62vh);"
  assert_file_contains "$css" ".market-monitor-filters__groups"
  assert_file_contains "$css" "gap: 0.35rem 0.55rem;"
}

assert_monitor_interactions_and_responsiveness() {
  local workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"
  local monitor="$repo_root/frontend/components/terminal/TerminalMarketMonitor.tsx"
  local table="$repo_root/frontend/components/terminal/MarketMonitorTable.tsx"
  local filters="$repo_root/frontend/components/terminal/MarketMonitorFilters.tsx"
  local css="$repo_root/frontend/app/globals.css"

  assert_file_contains "$workflow" "setSort: (key: TerminalMarketMonitorSortKey) => void"
  assert_file_contains "$workflow" "showMoreRows"
  assert_file_contains "$workflow" "showLessRows"
  assert_file_contains "$workflow" "selectRow: setSelectedRowId"
  assert_file_contains "$workflow" "rowMatchesFilters"
  assert_file_contains "$workflow" "buildAvailableMonitorFilters"
  assert_file_contains "$monitor" "MarketMonitorExplorationControls"
  assert_file_contains "$monitor" "Show more rows"
  assert_file_contains "$monitor" "Show less"
  assert_file_contains "$table" "aria-sort={getAriaSort(column.key, sort)}"
  assert_file_contains "$table" "onSelectRow(row.id)"
  assert_file_contains "$table" "aria-selected={selected}"
  assert_file_contains "$filters" "aria-pressed={active}"
  assert_file_contains "$filters" "data-monitor-filter-key={key}"
  assert_file_contains "$filters" "data-monitor-filter-value={option.value}"
  assert_file_contains "$filters" 'aria-label={`${option.count} rows`}'
  assert_file_contains "$filters" "disabled={selectedCount === 0}"
  assert_file_contains "$css" ".terminal-market-monitor--compact .terminal-market-monitor__grid"
  assert_file_contains "$css" "@media (max-width: 1100px)"
  assert_file_contains "$css" ".market-monitor-state-strip"
}

assert_screener_remains_disabled() {
  local module_registry="$repo_root/frontend/lib/terminalModuleRegistry.ts"
  local monitor="$repo_root/frontend/components/terminal/TerminalMarketMonitor.tsx"
  local filters="$repo_root/frontend/components/terminal/MarketMonitorFilters.tsx"

  assert_file_contains "$module_registry" 'id: "SCREENER"'
  assert_file_contains "$module_registry" 'availability: "disabled"'
  assert_file_contains "$module_registry" "The current backend supports scanner/trending and bounded symbol search only."
  assert_file_contains "$module_registry" "No arbitrary multi-factor screen-building API exists yet."
  assert_file_not_contains "$monitor" "SCREENER"
  assert_file_not_contains "$filters" "Screener"
}

assert_watchlist_and_error_copy_preserved() {
  local workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"
  local search_workflow="$repo_root/frontend/lib/symbolSearchWorkflow.ts"
  local watchlist_workflow="$repo_root/frontend/lib/watchlistWorkflow.ts"
  local market_client="$repo_root/frontend/lib/marketDataClient.ts"

  assert_file_contains "$workflow" "watchlist.getTrendingPinState(symbol)"
  assert_file_contains "$workflow" "watchlist.getSearchResultPinState(result)"
  assert_file_contains "$workflow" "watchlist.getWatchlistSymbolPinState(symbol)"
  assert_file_contains "$workflow" "watchlist.toggleTrendingPin(row.trendingSymbol)"
  assert_file_contains "$workflow" "watchlist.toggleSearchPin(row.searchResult)"
  assert_file_contains "$workflow" "watchlist.removePin(row.watchlistSymbol)"
  assert_file_contains "$workflow" "watchlistCachedFallback: watchlist.source === 'cache'"
  assert_file_contains "$watchlist_workflow" "Backend persisted pinKey/instrumentKey values are authoritative"
  assert_file_contains "$watchlist_workflow" "Cached legacy pins are shown read-only"
  assert_file_contains "$watchlist_workflow" "setWatchlistSource('cache')"
  assert_file_contains "$search_workflow" "MinimumSymbolSearchQueryLength = 2"
  assert_file_contains "$search_workflow" "SymbolSearchDebounceMs = 350"
  assert_file_contains "$search_workflow" 'Type at least ${minimumQueryLength} characters to search IBKR stocks.'
  assert_file_contains "$market_client" "provider-not-configured"
  assert_file_contains "$market_client" "provider-unavailable"
  assert_file_contains "$market_client" "authentication-required"
}

main() {
  assert_terminal_monitor_workflow_exists
  assert_bounded_api_only_search
  assert_exact_identity_actions
  assert_dense_terminal_components
  assert_monitor_interactions_and_responsiveness
  assert_screener_remains_disabled
  assert_watchlist_and_error_copy_preserved
}

main "$@"
