#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
frontend_root="$repo_root/frontend"
script_name="$(basename "${BASH_SOURCE[0]}")"

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

assert_path_exists() {
  local path="$1"

  if [[ ! -e "$path" ]]; then
    printf 'expected path to exist: %s\n' "$path" >&2
    return 1
  fi
}

assert_path_missing() {
  local path="$1"

  if [[ -e "$path" ]]; then
    printf 'expected path to be absent: %s\n' "$path" >&2
    return 1
  fi
}

assert_no_grep_matches() {
  local description="$1"
  local pattern="$2"
  shift 2

  if grep -RInE \
    --exclude-dir=.next \
    --exclude-dir=node_modules \
    --exclude='package-lock.json' \
    --exclude="$script_name" \
    --exclude='frontend-terminal-route-architecture-tests.sh' \
    "$pattern" "$@"; then
    printf 'unexpected %s found.\n' "$description" >&2
    return 1
  fi
}

assert_accepted_enabled_route_matrix() {
  local routes="$frontend_root/lib/terminalRoutes.ts"
  local registry="$frontend_root/lib/terminalModuleRegistry.ts"
  local route_matrix=(
    '/|app/page.tsx|HOME|TERMINAL_ENABLED_MODULE_ROUTES.HOME|HOME: "/"'
    '/search|app/search/page.tsx|SEARCH|TERMINAL_ENABLED_MODULE_ROUTES.SEARCH|SEARCH: "/search"'
    '/watchlist|app/watchlist/page.tsx|WATCHLIST|TERMINAL_ENABLED_MODULE_ROUTES.WATCHLIST|WATCHLIST: "/watchlist"'
    '/chart|app/chart/page.tsx|CHART|TERMINAL_ENABLED_MODULE_ROUTES.CHART|CHART: "/chart"'
    '/chart/[symbol]|app/chart/[symbol]/page.tsx|CHART|TERMINAL_SYMBOL_MODULE_ROUTES[moduleId]|CHART: "/chart"'
    '/analysis|app/analysis/page.tsx|ANALYSIS|TERMINAL_ENABLED_MODULE_ROUTES.ANALYSIS|ANALYSIS: "/analysis"'
    '/analysis/[symbol]|app/analysis/[symbol]/page.tsx|ANALYSIS|TERMINAL_SYMBOL_MODULE_ROUTES[moduleId]|ANALYSIS: "/analysis"'
    '/backtest|app/backtest/page.tsx|BACKTEST|TERMINAL_ENABLED_MODULE_ROUTES.BACKTEST|BACKTEST: "/backtest"'
    '/backtest/[symbol]|app/backtest/[symbol]/page.tsx|BACKTEST|TERMINAL_SYMBOL_MODULE_ROUTES[moduleId]|BACKTEST: "/backtest"'
    '/status|app/status/page.tsx|STATUS|TERMINAL_ENABLED_MODULE_ROUTES.STATUS|STATUS: "/status"'
    '/help|app/help/page.tsx|HELP|TERMINAL_ENABLED_MODULE_ROUTES.HELP|HELP: "/help"'
  )

  local entry accepted_route page module_id route_reference route_literal
  for entry in "${route_matrix[@]}"; do
    IFS='|' read -r accepted_route page module_id route_reference route_literal <<< "$entry"
    assert_path_exists "$frontend_root/$page"
    assert_file_contains "$frontend_root/$page" 'TerminalRoutePage'
    assert_file_contains "$frontend_root/$page" "moduleId=\"$module_id\""
    assert_file_contains "$routes" "$route_literal"

    if [[ "$accepted_route" != *'[symbol]' ]]; then
      assert_file_contains "$registry" "route: $route_reference"
    fi
  done

  assert_file_contains "$routes" 'export const TERMINAL_ENABLED_MODULE_ROUTES'
  assert_file_contains "$routes" 'export const TERMINAL_SYMBOL_MODULE_ROUTES'
  assert_file_contains "$routes" '${TERMINAL_SYMBOL_MODULE_ROUTES[moduleId]}/${encodeURIComponent(normalized.symbol)}'
}

assert_accepted_disabled_route_matrix() {
  local routes="$frontend_root/lib/terminalRoutes.ts"
  local registry="$frontend_root/lib/terminalModuleRegistry.ts"
  local route_matrix=(
    '/news|app/news/page.tsx|NEWS|TERMINAL_DISABLED_MODULE_ROUTES.NEWS|NEWS: "/news"'
    '/portfolio|app/portfolio/page.tsx|PORTFOLIO|TERMINAL_DISABLED_MODULE_ROUTES.PORTFOLIO|PORTFOLIO: "/portfolio"'
    '/research|app/research/page.tsx|RESEARCH|TERMINAL_DISABLED_MODULE_ROUTES.RESEARCH|RESEARCH: "/research"'
    '/screener|app/screener/page.tsx|SCREENER|TERMINAL_DISABLED_MODULE_ROUTES.SCREENER|SCREENER: "/screener"'
    '/econ|app/econ/page.tsx|ECON|TERMINAL_DISABLED_MODULE_ROUTES.ECON|ECON: "/econ"'
    '/ai|app/ai/page.tsx|AI|TERMINAL_DISABLED_MODULE_ROUTES.AI|AI: "/ai"'
    '/node|app/node/page.tsx|NODE|TERMINAL_DISABLED_MODULE_ROUTES.NODE|NODE: "/node"'
    '/orders|app/orders/page.tsx|ORDERS|TERMINAL_DISABLED_MODULE_ROUTES.ORDERS|ORDERS: "/orders"'
  )

  local entry accepted_route page module_id route_reference route_literal
  for entry in "${route_matrix[@]}"; do
    IFS='|' read -r accepted_route page module_id route_reference route_literal <<< "$entry"
    assert_path_exists "$frontend_root/$page"
    assert_file_contains "$frontend_root/$page" 'TerminalRoutePage'
    assert_file_contains "$frontend_root/$page" "disabledModuleId=\"$module_id\""
    assert_file_contains "$routes" "$route_literal"
    assert_file_contains "$registry" "route: $route_reference"
  done

  assert_file_contains "$routes" 'export const TERMINAL_DISABLED_MODULE_ROUTES'
}

assert_old_symbol_route_absent_without_alias() {
  local old_route_segment="symbols"
  local old_route="/""$old_route_segment"
  local old_symbol_pattern="/""symbols|symbols/""\\[symbol\\]"
  local app_symbols_path="$frontend_root/app/$old_route_segment"

  assert_path_missing "$app_symbols_path"
  assert_file_not_contains "$frontend_root/next.config.ts" 'redirects'
  assert_file_not_contains "$frontend_root/next.config.ts" "$old_route"

  assert_no_grep_matches \
    'retired symbol route or redirect alias in active frontend source' \
    "$old_symbol_pattern|NextResponse[.]redirect|permanentRedirect|redirect[(]" \
    "$frontend_root/app" \
    "$frontend_root/components" \
    "$frontend_root/lib" \
    "$frontend_root/types"

  assert_no_grep_matches \
    'stale retired symbol-route expectations in frontend validation scripts' \
    "$old_symbol_pattern" \
    "$repo_root/tests/apphost"
}

assert_exact_identity_query_preservation() {
  local routes="$frontend_root/lib/terminalRoutes.ts"
  local identity="$frontend_root/lib/instrumentIdentity.ts"
  local workflow="$frontend_root/lib/terminalMarketMonitorWorkflow.ts"

  assert_file_contains "$routes" 'const params = appendIdentityQueryParams(new URLSearchParams(), normalized);'
  assert_file_contains "$routes" 'params.set("range", options.chartRange);'
  assert_file_contains "$routes" '${TERMINAL_SYMBOL_MODULE_ROUTES[moduleId]}/${encodeURIComponent(normalized.symbol)}${query ? `?${query}` : ""}'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.provider)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.providerSymbolId)'
  assert_file_not_contains "$routes" 'firstTerminalQueryValue(searchParams.ibkrConid)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.exchange)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.currency)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.assetClass)'

  assert_file_contains "$identity" "params.set('provider', identity.provider);"
  assert_file_contains "$identity" "params.set('providerSymbolId', identity.providerSymbolId);"
  assert_file_not_contains "$identity" "params.set('ibkrConid', String(identity.ibkrConid));"
  assert_file_not_contains "$identity" "\`ibkrConid="
  assert_file_contains "$identity" "params.set('exchange', identity.exchange);"
  assert_file_contains "$identity" "params.set('currency', identity.currency);"
  assert_file_contains "$identity" "params.set('assetClass', identity.assetClass);"

  assert_file_contains "$workflow" "const chartHref = createTerminalSymbolRoute('CHART', identity);"
  assert_file_contains "$workflow" "const analysisHref = createModuleHref(identity, 'ANALYSIS');"
  assert_file_contains "$workflow" "const backtestHref = createModuleHref(identity, 'BACKTEST');"
  assert_file_contains "$workflow" 'return createTerminalSymbolRoute(moduleId, identity);'
  assert_file_contains "$workflow" 'identity: row.exactIdentity'
  assert_file_contains "$workflow" "route: moduleId === 'ANALYSIS' ? row.analysisHref : moduleId === 'BACKTEST' ? row.backtestHref : row.chartHref"
}

run_static_validation_script() {
  local script_path="$1"

  assert_path_exists "$script_path"
  bash "$script_path" >/dev/null
}

assert_layout_visibility_guardrails() {
  run_static_validation_script "$repo_root/tests/apphost/frontend-terminal-layout-visibility-tests.sh"
}

assert_chart_landing_default_guardrails() {
  run_static_validation_script "$repo_root/tests/apphost/frontend-chart-watchlist-default-tests.sh"
}

assert_purpose_built_module_guardrails() {
  run_static_validation_script "$repo_root/tests/apphost/frontend-purpose-built-home-search-watchlist-tests.sh"
}

assert_provider_runtime_independent_validation() {
  local validation_scripts=(
    "${BASH_SOURCE[0]}"
    "$repo_root/tests/apphost/frontend-terminal-route-architecture-tests.sh"
    "$repo_root/tests/apphost/frontend-terminal-layout-visibility-tests.sh"
    "$repo_root/tests/apphost/frontend-chart-watchlist-default-tests.sh"
    "$repo_root/tests/apphost/frontend-purpose-built-home-search-watchlist-tests.sh"
  )
  local forbidden_tokens=(
    "NEXT_PUBLIC_ATRADE_API""_BASE""_URL"
    "ATRADE_""IBKR"
    "IBKR_""PASSWORD"
    "cu""rl "
    "npm ""run ""dev"
    "npm ""run ""build"
    "dot""net "
    "doc""ker "
  )

  local validation_script forbidden_token
  for validation_script in "${validation_scripts[@]}"; do
    assert_path_exists "$validation_script"
    for forbidden_token in "${forbidden_tokens[@]}"; do
      assert_file_not_contains "$validation_script" "$forbidden_token"
    done
  done
}

main() {
  assert_accepted_enabled_route_matrix
  assert_accepted_disabled_route_matrix
  assert_old_symbol_route_absent_without_alias
  assert_exact_identity_query_preservation
  assert_layout_visibility_guardrails
  assert_chart_landing_default_guardrails
  assert_purpose_built_module_guardrails
  assert_provider_runtime_independent_validation

  printf 'frontend terminal consolidated regression validation passed.\n'
}

main "$@"
