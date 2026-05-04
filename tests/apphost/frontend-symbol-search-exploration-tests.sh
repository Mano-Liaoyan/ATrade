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

assert_search_workflow_view_model() {
  local workflow="$repo_root/frontend/lib/symbolSearchWorkflow.ts"

  assert_file_contains "$workflow" 'DefaultSymbolSearchRequestLimit = 25'
  assert_file_contains "$workflow" 'MaximumSymbolSearchRequestLimit = 50'
  assert_file_contains "$workflow" 'DefaultSymbolSearchVisibleLimit = 5'
  assert_file_contains "$workflow" 'SymbolSearchVisibleResultIncrement = 5'
  assert_file_contains "$workflow" 'createSymbolSearchResultsViewModel'
  assert_file_contains "$workflow" 'rankSymbolSearchResults'
  assert_file_contains "$workflow" 'bestMatch: filteredResults[0] ?? null'
  assert_file_contains "$workflow" 'visibleResults = filteredResults.slice(0, boundedVisibleLimit)'
  assert_file_contains "$workflow" "SymbolSearchFilterKey = 'exchange' | 'currency' | 'assetClass' | 'provider'"
  assert_file_contains "$workflow" 'applySymbolSearchFilters'
  assert_file_contains "$workflow" 'selectedFilters'
  assert_file_contains "$workflow" 'setFilter: (key: SymbolSearchFilterKey, value: string | null) => void'
  assert_file_contains "$workflow" 'clearFilters: () => void'
}

assert_bounded_backend_search() {
  local workflow="$repo_root/frontend/lib/symbolSearchWorkflow.ts"
  local monitor_workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"
  local market_client="$repo_root/frontend/lib/marketDataClient.ts"

  assert_file_contains "$workflow" 'const boundedSearchLimit = clampSymbolSearchLimit(limit);'
  assert_file_contains "$workflow" 'searchSymbols(trimmedQuery, { assetClass, limit: boundedSearchLimit })'
  assert_file_not_contains "$workflow" 'searchSymbols(trimmedQuery)'
  assert_file_contains "$monitor_workflow" 'const boundedSearchLimit = clampSymbolSearchLimit(searchLimit);'
  assert_file_contains "$monitor_workflow" 'useSymbolSearchWorkflow({'
  assert_file_contains "$monitor_workflow" 'limit: boundedSearchLimit'
  assert_file_contains "$market_client" '/api/market-data/search'
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
    -E 'Npgsql|TimescaleConnection|PostgresConnection|Host=|User ID=|Password=|redis://|nats://|Client Portal|ibkr-gateway' \
    "$repo_root/frontend"; then
    printf 'frontend source must keep browser search behind ATrade.Api clients.\n' >&2
    return 1
  fi
}

assert_terminal_monitor_search_contract() {
  local terminal_app="$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx"
  local monitor="$repo_root/frontend/components/terminal/TerminalMarketMonitor.tsx"
  local monitor_workflow="$repo_root/frontend/lib/terminalMarketMonitorWorkflow.ts"
  local search_component="$repo_root/frontend/components/terminal/MarketMonitorSearch.tsx"
  local filters_component="$repo_root/frontend/components/terminal/MarketMonitorFilters.tsx"
  local table_component="$repo_root/frontend/components/terminal/MarketMonitorTable.tsx"
  local css="$repo_root/frontend/app/globals.css"

  assert_file_contains "$terminal_app" '<TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent}'
  assert_file_contains "$terminal_app" 'case "SEARCH"'
  assert_file_contains "$terminal_app" 'return <TerminalSearchModule onOpenIntent={onOpenIntent} searchQuery={searchQuery} />;'
  assert_file_contains "$monitor" 'data-testid="terminal-market-monitor"'
  assert_file_contains "$monitor" 'MarketMonitorSearch'
  assert_file_contains "$monitor" 'MarketMonitorFilters'
  assert_file_contains "$monitor" 'MarketMonitorTable'
  assert_file_contains "$monitor" 'Show more rows'
  assert_file_contains "$monitor" 'Show less'
  assert_file_contains "$monitor_workflow" 'createSearchMonitorRow'
  assert_file_contains "$monitor_workflow" 'getSearchResultIdentity(result)'
  assert_file_contains "$monitor_workflow" 'search.searchView.filteredResults.map'
  assert_file_contains "$search_component" 'data-testid="market-monitor-search-input"'
  assert_file_contains "$search_component" 'Bounded IBKR stock search'
  assert_file_contains "$search_component" 'Minimum {MinimumSymbolSearchQueryLength} chars'
  assert_file_contains "$filters_component" "['source', 'saved', 'provider', 'exchange', 'currency', 'assetClass']"
  assert_file_contains "$filters_component" 'aria-pressed={active}'
  assert_file_contains "$table_component" 'aria-sort={getAriaSort(column.key, sort)}'
  assert_file_contains "$table_component" 'data-testid="market-monitor-row"'
  assert_file_contains "$css" '.market-monitor-table-scroll'
  assert_file_contains "$css" 'max-height: min(34rem, 62vh);'
}

assert_old_search_list_components_retired() {
  assert_path_missing "$repo_root/frontend/components/SymbolSearch.tsx"
  assert_path_missing "$repo_root/frontend/components/TrendingList.tsx"
  assert_path_missing "$repo_root/frontend/components/Watchlist.tsx"
  assert_path_missing "$repo_root/frontend/components/MarketLogo.tsx"

  if grep -RIn --exclude-dir=.next --exclude-dir=node_modules -E '<(SymbolSearch|TrendingList|Watchlist|MarketLogo)([[:space:]>])|from ["'"'"'][^"'"'"']*/(SymbolSearch|TrendingList|Watchlist|MarketLogo)["'"'"']' "$repo_root/frontend"; then
    printf 'old search/list rendering components must not be imported by active frontend source.\n' >&2
    return 1
  fi
}

main() {
  assert_search_workflow_view_model
  assert_bounded_backend_search
  assert_terminal_monitor_search_contract
  assert_old_search_list_components_retired
}

main "$@"
