#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
frontend_root="$repo_root/frontend"

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

assert_css_rule_contains() {
  local selector="$1"
  local needle="$2"
  local css_file="$frontend_root/app/globals.css"

  python3 - "$css_file" "$selector" "$needle" <<'PY'
import re
import sys
from pathlib import Path

css_path = Path(sys.argv[1])
selector = sys.argv[2]
needle = sys.argv[3]
css = css_path.read_text(encoding='utf-8')
pattern = re.escape(selector) + r"\s*\{(?P<body>[^{}]*)\}"
match = re.search(pattern, css)
if not match:
    print(f"expected CSS selector {selector!r} to exist in {css_path}", file=sys.stderr)
    sys.exit(1)
if needle not in match.group('body'):
    print(f"expected CSS selector {selector!r} to contain {needle!r}", file=sys.stderr)
    sys.exit(1)
PY
}

assert_chart_route_and_identity_wiring() {
  local symbol_page="$frontend_root/app/symbols/[symbol]/page.tsx"
  local terminal_app="$frontend_root/components/terminal/ATradeTerminalApp.tsx"
  local monitor_workflow="$frontend_root/lib/terminalMarketMonitorWorkflow.ts"
  local identity="$frontend_root/lib/instrumentIdentity.ts"

  assert_file_contains "$symbol_page" "return 'CHART';"
  assert_file_contains "$symbol_page" 'createQueryIdentity(normalizedSymbol, resolvedSearchParams)'
  assert_file_contains "$symbol_page" 'providerSymbolId'
  assert_file_contains "$symbol_page" 'initialModuleId={initialModuleId}'
  assert_file_contains "$symbol_page" 'initialIdentity={identity}'

  assert_file_contains "$monitor_workflow" 'createChartNavigationIntent(row: TerminalMarketMonitorRow)'
  assert_file_contains "$monitor_workflow" "return createRowNavigationIntent(row, 'CHART');"
  assert_file_contains "$monitor_workflow" 'createSymbolChartHref(identity)'
  assert_file_contains "$monitor_workflow" "route: moduleId === 'ANALYSIS' ? row.analysisHref : row.chartHref"
  assert_file_contains "$monitor_workflow" 'identity: row.exactIdentity'
  assert_file_contains "$monitor_workflow" "chartRange: '1D'"

  assert_file_contains "$identity" "params.set('providerSymbolId', identity.providerSymbolId);"
  assert_file_contains "$identity" "params.set('exchange', identity.exchange);"
  assert_file_contains "$identity" "params.set('currency', identity.currency);"
  assert_file_contains "$identity" "params.set('assetClass', identity.assetClass);"

  assert_file_contains "$terminal_app" 'setActiveModuleId("CHART")'
  assert_file_contains "$terminal_app" 'setActiveSymbol(intent.symbol.toUpperCase())'
  assert_file_contains "$terminal_app" 'setActiveIdentity(intent.identity ?? null)'
  assert_file_contains "$terminal_app" '<TerminalChartWorkspace chart={chart} identity={identity} />'
}

assert_candlestick_chart_visible_sizing_contract() {
  local chart_component="$frontend_root/components/CandlestickChart.tsx"

  assert_file_contains "$chart_component" 'data-testid="candlestick-chart"'
  assert_file_contains "$chart_component" 'data-testid="chart-legend"'
  assert_file_contains "$chart_component" 'createChart(container, {'
  assert_file_contains "$chart_component" 'autoSize: false'
  assert_file_contains "$chart_component" 'width: initialSize.width'
  assert_file_contains "$chart_component" 'height: initialSize.height'
  assert_file_contains "$chart_component" 'measureChartContainer(container)'
  assert_file_contains "$chart_component" 'container.getBoundingClientRect()'
  assert_file_contains "$chart_component" 'ResizeObserver'
  assert_file_contains "$chart_component" 'window.addEventListener('\''resize'\'', scheduleResizeAndFit)'
  assert_file_contains "$chart_component" 'window.requestAnimationFrame'
  assert_file_contains "$chart_component" 'chart.resize(nextSize.width, nextSize.height, true)'
  assert_file_contains "$chart_component" 'chart.timeScale().fitContent()'
  assert_file_contains "$chart_component" 'chart.unsubscribeCrosshairMove(handleCrosshairMove)'
  assert_file_contains "$chart_component" 'chart.remove()'
  assert_file_contains "$chart_component" 'HistogramSeries'
  assert_file_contains "$chart_component" "title: 'SMA 20'"
  assert_file_contains "$chart_component" "title: 'SMA 50'"
}

assert_truthful_provider_empty_and_no_fake_candle_states() {
  local chart_workspace="$frontend_root/components/terminal/TerminalChartWorkspace.tsx"
  local terminal_workflow="$frontend_root/lib/terminalChartWorkspaceWorkflow.ts"
  local symbol_workflow="$frontend_root/lib/symbolChartWorkflow.ts"
  local market_client="$frontend_root/lib/marketDataClient.ts"

  assert_file_contains "$terminal_workflow" 'hasCandleData: Boolean(chart.candles && chart.candles.candles.length > 0)'
  assert_file_contains "$terminal_workflow" 'isEmpty: !hasCandleData'
  assert_file_contains "$chart_workspace" 'chart.candles && chart.view.hasCandleData'
  assert_file_contains "$chart_workspace" '!chart.candles || !chart.view.hasCandleData'
  assert_file_contains "$chart_workspace" 'no synthetic chart data is shown'
  assert_file_contains "$chart_workspace" 'chart.loading ? <div className="loading-state" role="status">Loading OHLC candlestick chart data…</div>'
  assert_file_contains "$chart_workspace" '!chart.loading && chart.error'

  assert_file_contains "$market_client" "error?.code === 'provider-not-configured'"
  assert_file_contains "$market_client" "error?.code === 'provider-unavailable'"
  assert_file_contains "$market_client" "error?.code === 'authentication-required'"
  assert_file_contains "$symbol_workflow" 'setCandles(candleResponse)'
  assert_file_contains "$symbol_workflow" 'setIndicators(indicatorResponse)'
  assert_file_not_contains "$symbol_workflow" 'sampleCandles'
  assert_file_not_contains "$symbol_workflow" 'mockCandles'
  assert_file_not_contains "$chart_workspace" 'fakeCandles'
}

assert_chart_css_non_collapse_contract() {
  assert_css_rule_contains '.terminal-chart-workspace' 'min-height: min(44rem, calc(100dvh - 4rem));'
  assert_css_rule_contains '.terminal-chart-workspace__market-grid' 'min-height: min(42rem, 72dvh);'
  assert_css_rule_contains '.terminal-chart-workspace__chart-region' 'grid-template-rows: auto minmax(26rem, 1fr) auto;'
  assert_css_rule_contains '.terminal-chart-workspace__chart-region' 'min-height: 30rem;'
  assert_css_rule_contains '.terminal-chart-workspace__chart-region' 'overflow: auto;'
  assert_css_rule_contains '.chart-shell' 'grid-template-rows: auto minmax(26rem, 1fr) auto;'
  assert_css_rule_contains '.chart-shell' 'min-height: 30rem;'
  assert_css_rule_contains '.chart-container' 'width: 100%;'
  assert_css_rule_contains '.chart-container' 'min-width: 1px;'
  assert_css_rule_contains '.chart-container' 'height: clamp(420px, 56dvh, 680px);'
  assert_css_rule_contains '.chart-container' 'min-height: 420px;'
  assert_css_rule_contains '.chart-container' 'overflow: hidden;'

  assert_file_contains "$frontend_root/app/globals.css" '.terminal-chart-workspace,'
  assert_file_contains "$frontend_root/app/globals.css" 'height: clamp(360px, 54dvh, 560px);'
  assert_file_contains "$frontend_root/app/globals.css" 'min-height: 360px;'
}

assert_no_generated_or_hardcoded_candle_fallbacks() {
  local scan_paths=(
    "$frontend_root/components/CandlestickChart.tsx"
    "$frontend_root/components/terminal/TerminalChartWorkspace.tsx"
    "$frontend_root/lib/symbolChartWorkflow.ts"
    "$frontend_root/lib/terminalChartWorkspaceWorkflow.ts"
    "$frontend_root/lib/marketDataClient.ts"
  )

  if grep -RInE --exclude-dir=.next --exclude-dir=node_modules 'fakeCandle|mockCandle|sampleCandle|fixtureCandle|demoCandle|hardcoded.*candle|Math\.random\(\).*candle' "${scan_paths[@]}"; then
    printf 'chart visibility must not be restored with fake or generated candle data.\n' >&2
    return 1
  fi
}

main() {
  assert_chart_route_and_identity_wiring
  assert_candlestick_chart_visible_sizing_contract
  assert_truthful_provider_empty_and_no_fake_candle_states
  assert_chart_css_non_collapse_contract
  assert_no_generated_or_hardcoded_candle_fallbacks
}

main "$@"
