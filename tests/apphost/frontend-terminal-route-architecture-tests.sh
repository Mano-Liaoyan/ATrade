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
    "$pattern" "$@"; then
    printf 'unexpected %s found.\n' "$description" >&2
    return 1
  fi
}

assert_enabled_route_files() {
  local enabled_pages=(
    "$frontend_root/app/page.tsx"
    "$frontend_root/app/search/page.tsx"
    "$frontend_root/app/watchlist/page.tsx"
    "$frontend_root/app/chart/page.tsx"
    "$frontend_root/app/chart/[symbol]/page.tsx"
    "$frontend_root/app/analysis/page.tsx"
    "$frontend_root/app/analysis/[symbol]/page.tsx"
    "$frontend_root/app/backtest/page.tsx"
    "$frontend_root/app/backtest/[symbol]/page.tsx"
    "$frontend_root/app/status/page.tsx"
    "$frontend_root/app/help/page.tsx"
  )

  for page in "${enabled_pages[@]}"; do
    assert_path_exists "$page"
    assert_file_contains "$page" "TerminalRoutePage"
  done

  assert_file_contains "$frontend_root/app/page.tsx" 'moduleId="HOME"'
  assert_file_contains "$frontend_root/app/search/page.tsx" 'moduleId="SEARCH"'
  assert_file_contains "$frontend_root/app/watchlist/page.tsx" 'moduleId="WATCHLIST"'
  assert_file_contains "$frontend_root/app/chart/page.tsx" 'moduleId="CHART"'
  assert_file_contains "$frontend_root/app/chart/[symbol]/page.tsx" 'moduleId="CHART"'
  assert_file_contains "$frontend_root/app/analysis/page.tsx" 'moduleId="ANALYSIS"'
  assert_file_contains "$frontend_root/app/analysis/[symbol]/page.tsx" 'moduleId="ANALYSIS"'
  assert_file_contains "$frontend_root/app/backtest/page.tsx" 'moduleId="BACKTEST"'
  assert_file_contains "$frontend_root/app/backtest/[symbol]/page.tsx" 'moduleId="BACKTEST"'
  assert_file_contains "$frontend_root/app/status/page.tsx" 'moduleId="STATUS"'
  assert_file_contains "$frontend_root/app/help/page.tsx" 'moduleId="HELP"'
}

assert_disabled_route_files() {
  local disabled_pages=(
    "$frontend_root/app/news/page.tsx:NEWS"
    "$frontend_root/app/portfolio/page.tsx:PORTFOLIO"
    "$frontend_root/app/research/page.tsx:RESEARCH"
    "$frontend_root/app/screener/page.tsx:SCREENER"
    "$frontend_root/app/econ/page.tsx:ECON"
    "$frontend_root/app/ai/page.tsx:AI"
    "$frontend_root/app/node/page.tsx:NODE"
    "$frontend_root/app/orders/page.tsx:ORDERS"
  )

  local entry page module_id
  for entry in "${disabled_pages[@]}"; do
    page="${entry%%:*}"
    module_id="${entry##*:}"
    assert_path_exists "$page"
    assert_file_contains "$page" "TerminalRoutePage"
    assert_file_contains "$page" "disabledModuleId=\"$module_id\""
  done
}

assert_terminal_route_helpers() {
  local routes="$frontend_root/lib/terminalRoutes.ts"
  local wrapper="$frontend_root/components/terminal/TerminalRoutePage.tsx"
  local app="$frontend_root/components/terminal/ATradeTerminalApp.tsx"

  assert_file_contains "$routes" 'HOME: "/"'
  assert_file_contains "$routes" 'SEARCH: "/search"'
  assert_file_contains "$routes" 'WATCHLIST: "/watchlist"'
  assert_file_contains "$routes" 'CHART: "/chart"'
  assert_file_contains "$routes" 'ANALYSIS: "/analysis"'
  assert_file_contains "$routes" 'BACKTEST: "/backtest"'
  assert_file_contains "$routes" 'STATUS: "/status"'
  assert_file_contains "$routes" 'HELP: "/help"'
  assert_file_contains "$routes" 'NEWS: "/news"'
  assert_file_contains "$routes" 'PORTFOLIO: "/portfolio"'
  assert_file_contains "$routes" 'RESEARCH: "/research"'
  assert_file_contains "$routes" 'SCREENER: "/screener"'
  assert_file_contains "$routes" 'ECON: "/econ"'
  assert_file_contains "$routes" 'AI: "/ai"'
  assert_file_contains "$routes" 'NODE: "/node"'
  assert_file_contains "$routes" 'ORDERS: "/orders"'
  assert_file_contains "$routes" 'createTerminalRouteIdentity(initialSymbol, searchParams)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.provider)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.providerSymbolId)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.ibkrConid)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.exchange)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.currency)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.assetClass)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.range)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.chartRange)'
  assert_file_contains "$routes" 'firstTerminalQueryValue(searchParams.timeframe)'
  assert_file_contains "$routes" 'SUPPORTED_CHART_RANGES.includes(normalizedRange)'
  assert_file_contains "$routes" 'createTerminalSymbolRoute('
  assert_file_contains "$routes" '${TERMINAL_SYMBOL_MODULE_ROUTES[moduleId]}/${encodeURIComponent(normalized.symbol)}'

  assert_file_contains "$wrapper" 'createTerminalRouteAppState'
  assert_file_contains "$wrapper" '<ATradeTerminalApp {...routeState} />'
  assert_file_contains "$app" 'initialDisabledModuleId'
  assert_file_contains "$app" 'Opened ${initialModuleId} from the URL route.'
}

assert_registry_rail_and_workflow_routes() {
  local registry="$frontend_root/lib/terminalModuleRegistry.ts"
  local rail="$frontend_root/components/terminal/TerminalModuleRail.tsx"
  local app="$frontend_root/components/terminal/ATradeTerminalApp.tsx"
  local monitor_workflow="$frontend_root/lib/terminalMarketMonitorWorkflow.ts"
  local identity="$frontend_root/lib/instrumentIdentity.ts"

  assert_file_contains "$registry" 'TERMINAL_ENABLED_MODULE_ROUTES'
  assert_file_contains "$registry" 'TERMINAL_DISABLED_MODULE_ROUTES'
  assert_file_contains "$registry" 'route: TERMINAL_ENABLED_MODULE_ROUTES.HOME'
  assert_file_contains "$registry" 'route: TERMINAL_ENABLED_MODULE_ROUTES.SEARCH'
  assert_file_contains "$registry" 'route: TERMINAL_ENABLED_MODULE_ROUTES.WATCHLIST'
  assert_file_contains "$registry" 'route: TERMINAL_ENABLED_MODULE_ROUTES.CHART'
  assert_file_contains "$registry" 'route: TERMINAL_ENABLED_MODULE_ROUTES.ANALYSIS'
  assert_file_contains "$registry" 'route: TERMINAL_ENABLED_MODULE_ROUTES.BACKTEST'
  assert_file_contains "$registry" 'route: TERMINAL_ENABLED_MODULE_ROUTES.STATUS'
  assert_file_contains "$registry" 'route: TERMINAL_ENABLED_MODULE_ROUTES.HELP'
  assert_file_contains "$registry" 'route: TERMINAL_DISABLED_MODULE_ROUTES.NEWS'
  assert_file_contains "$registry" 'route: TERMINAL_DISABLED_MODULE_ROUTES.PORTFOLIO'
  assert_file_contains "$registry" 'route: TERMINAL_DISABLED_MODULE_ROUTES.RESEARCH'
  assert_file_contains "$registry" 'route: TERMINAL_DISABLED_MODULE_ROUTES.SCREENER'
  assert_file_contains "$registry" 'route: TERMINAL_DISABLED_MODULE_ROUTES.ECON'
  assert_file_contains "$registry" 'route: TERMINAL_DISABLED_MODULE_ROUTES.AI'
  assert_file_contains "$registry" 'route: TERMINAL_DISABLED_MODULE_ROUTES.NODE'
  assert_file_contains "$registry" 'route: TERMINAL_DISABLED_MODULE_ROUTES.ORDERS'

  assert_file_contains "$rail" 'data-module-route={module.route}'
  assert_file_contains "$rail" 'aria-current={isSelected ? "page" : undefined}'
  assert_file_contains "$app" 'createTerminalModuleRoute(moduleId)'
  assert_file_contains "$app" 'pushTerminalRoute(createTerminalModuleRoute(moduleId), router.push)'
  assert_file_contains "$app" 'createTerminalSymbolRoute(intent.moduleId'
  assert_file_contains "$app" 'pushTerminalRoute(route, router.push)'

  assert_file_contains "$monitor_workflow" "createTerminalSymbolRoute('CHART', identity)"
  assert_file_contains "$monitor_workflow" 'return createTerminalSymbolRoute(moduleId, identity);'
  assert_file_contains "$monitor_workflow" 'identity: row.exactIdentity'
  assert_file_contains "$monitor_workflow" "route: moduleId === 'ANALYSIS' ? row.analysisHref : moduleId === 'BACKTEST' ? row.backtestHref : row.chartHref"
  assert_file_contains "$monitor_workflow" "chartRange: '1D'"
  assert_file_contains "$identity" 'return `/chart/${encodeURIComponent(normalized.symbol)}'
}

assert_old_symbols_route_removed_without_alias() {
  assert_path_missing "$frontend_root/app/symbols"
  assert_file_not_contains "$frontend_root/next.config.ts" 'redirects'
  assert_file_not_contains "$frontend_root/next.config.ts" '/symbols'

  assert_no_grep_matches \
    'old symbol route or redirect alias in active frontend source' \
    '/symbols|symbols/\[symbol\]|NextResponse\.redirect|permanentRedirect|redirect\(' \
    "$frontend_root/app" \
    "$frontend_root/components" \
    "$frontend_root/lib" \
    "$frontend_root/types"

  assert_no_grep_matches \
    'stale old symbol route expectations in frontend apphost tests' \
    '/symbols|symbols/\[symbol\]|module=ANALYSIS|module=BACKTEST|module=HELP|module=STATUS|#terminal' \
    "$repo_root/tests/apphost"
}

assert_provider_runtime_independent_validation() {
  local api_base_token="NEXT_PUBLIC_ATRADE_API""_BASE""_URL"
  local curl_token="cu""rl "
  local frontend_build_token="npm ""run"" build"
  local dotnet_token="dot""net "
  local ibkr_env_token="ATRADE_""IBKR"
  local ibkr_password_token="IBKR_""PASSWORD"

  assert_file_not_contains "${BASH_SOURCE[0]}" "$api_base_token"
  assert_file_not_contains "${BASH_SOURCE[0]}" "$curl_token"
  assert_file_not_contains "${BASH_SOURCE[0]}" "$frontend_build_token"
  assert_file_not_contains "${BASH_SOURCE[0]}" "$dotnet_token"
  assert_file_not_contains "${BASH_SOURCE[0]}" "$ibkr_env_token"
  assert_file_not_contains "${BASH_SOURCE[0]}" "$ibkr_password_token"
}

main() {
  assert_enabled_route_files
  assert_disabled_route_files
  assert_terminal_route_helpers
  assert_registry_rail_and_workflow_routes
  assert_old_symbols_route_removed_without_alias
  assert_provider_runtime_independent_validation

  printf 'frontend terminal route architecture validation passed.\n'
}

main "$@"
