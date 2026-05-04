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
  local market_client="$repo_root/frontend/lib/marketDataClient.ts"

  assert_file_contains "$workflow" 'const boundedSearchLimit = clampSymbolSearchLimit(limit);'
  assert_file_contains "$workflow" 'searchSymbols(trimmedQuery, { assetClass, limit: boundedSearchLimit })'
  assert_file_not_contains "$workflow" 'searchSymbols(trimmedQuery)'
  assert_file_contains "$market_client" '/api/market-data/search'
  assert_file_contains "$market_client" "params.set('limit', String(options.limit));"

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

assert_existing_search_contracts_preserved() {
  local workflow="$repo_root/frontend/lib/symbolSearchWorkflow.ts"
  local search="$repo_root/frontend/components/SymbolSearch.tsx"

  assert_file_contains "$workflow" 'MinimumSymbolSearchQueryLength = 2'
  assert_file_contains "$workflow" 'SymbolSearchDebounceMs = 350'
  assert_file_contains "$workflow" 'Type at least ${minimumQueryLength} characters to search IBKR stocks.'
  assert_file_contains "$workflow" 'formatSymbolSearchWorkflowError'
  assert_file_contains "$workflow" 'IBKR stock search is unavailable.'
  assert_file_contains "$search" 'getSearchResultIdentity(result)'
  assert_file_contains "$search" 'createSymbolChartHref(identity)'
  assert_file_contains "$search" 'getPinState?.(result)'
  assert_file_contains "$search" 'onTogglePin(result)'
}

assert_search_ui_exploration_contract() {
  local search="$repo_root/frontend/components/SymbolSearch.tsx"
  local chart="$repo_root/frontend/components/SymbolChartView.tsx"
  local workspace="$repo_root/frontend/components/TradingWorkspace.tsx"
  local css="$repo_root/frontend/app/globals.css"

  assert_file_contains "$search" 'Ranked results'
  assert_file_contains "$search" 'Best match'
  assert_file_contains "$search" 'formatResultCount(searchView.filteredResultCount, searchView.totalResultCount)'
  assert_file_contains "$search" 'Refine by market metadata'
  assert_file_contains "$search" "VisibleSymbolSearchFilterKeys: SymbolSearchFilterKey[] = ['exchange', 'currency', 'assetClass']"
  assert_file_contains "$search" 'aria-pressed={active}'
  assert_file_contains "$search" 'Show more results'
  assert_file_contains "$search" 'Show less'
  assert_file_contains "$search" 'aria-controls={resultListId}'
  assert_file_contains "$search" 'symbol-search-panel--compact'
  assert_file_contains "$workspace" '<SymbolSearch'
  assert_file_contains "$workspace" 'getSearchResultPinState'
  assert_file_contains "$chart" '<SymbolSearch'
  assert_file_contains "$chart" 'compact'
  assert_file_not_contains "$chart" 'limit={6}'
  assert_file_contains "$css" '.symbol-search-results'
  assert_file_contains "$css" 'max-height: min(34rem, 58vh);'
  assert_file_contains "$css" 'overflow-y: auto;'
  assert_file_contains "$css" 'symbol-search-panel--compact .symbol-search-results'
  assert_file_contains "$css" 'max-height: 44vh;'
}

main() {
  assert_search_workflow_view_model
  assert_bounded_backend_search
  assert_existing_search_contracts_preserved
  assert_search_ui_exploration_contract
}

main "$@"
