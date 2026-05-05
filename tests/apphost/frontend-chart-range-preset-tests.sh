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

assert_chart_range_types() {
  local types_file="$repo_root/frontend/types/marketData.ts"

  assert_file_contains "$types_file" "export type ChartRange = '1min' | '5mins' | '1h' | '6h' | '1D' | '1m' | '6m' | '1y' | '5y' | 'all'"
  assert_file_contains "$types_file" "SUPPORTED_CHART_RANGES: ChartRange[] = ['1min', '5mins', '1h', '6h', '1D', '1m', '6m', '1y', '5y', 'all']"
  assert_file_contains "$types_file" "all: 'All time'"
  assert_file_contains "$types_file" "'1D': 'Past day from now'"
  assert_file_contains "$types_file" "'1m': 'Past month from now'"
  assert_file_contains "$types_file" "'6m': 'Past six months from now'"
  assert_file_not_contains "$types_file" "'5m'"
}

assert_chart_range_controls() {
  local header="$repo_root/frontend/components/terminal/TerminalInstrumentHeader.tsx"
  local chart_workspace="$repo_root/frontend/components/terminal/TerminalChartWorkspace.tsx"
  local terminal_app="$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx"

  assert_file_contains "$header" "Chart range lookback controls"
  assert_file_contains "$header" "data-testid=\"chart-range-controls\""
  assert_file_contains "$header" "data-testid=\"chart-range-help\""
  assert_file_contains "$header" "chart.view.rangeHelpCopy"
  assert_file_contains "$header" "chart.view.supportedRanges.map"
  assert_file_contains "$header" "CHART_RANGE_LABELS[chartRange]"
  assert_file_not_contains "$header" "Chart timeframe controls"

  assert_file_contains "$chart_workspace" "Lookback candlestick chart"
  assert_file_contains "$chart_workspace" "selected lookback range from now"
  assert_file_contains "$chart_workspace" "chart.candles && chart.view.hasCandleData"
  assert_file_contains "$chart_workspace" "!chart.candles || !chart.view.hasCandleData"
  assert_file_contains "$chart_workspace" "<TerminalAnalysisWorkspace symbol={chart.normalizedSymbol} chartRange={chart.chartRange}"
  assert_file_contains "$terminal_app" "initialChartRange"
}

assert_frontend_client_params() {
  local market_client="$repo_root/frontend/lib/marketDataClient.ts"
  local stream_client="$repo_root/frontend/lib/marketDataStream.ts"
  local workflow="$repo_root/frontend/lib/symbolChartWorkflow.ts"

  assert_file_contains "$market_client" "getCandles(symbol: string, chartRange: ChartRange"
  assert_file_contains "$market_client" "getIndicators(symbol: string, chartRange: ChartRange"
  assert_file_contains "$market_client" "new URLSearchParams({ range: chartRange })"
  assert_file_contains "$market_client" "appendIdentityQueryParams(params, identity)"
  assert_file_not_contains "$market_client" "new URLSearchParams({ timeframe })"

  assert_file_contains "$stream_client" "chartRange: ChartRange"
  assert_file_contains "$stream_client" "connection.invoke('Subscribe', options.symbol.toUpperCase(), options.chartRange)"
  assert_file_contains "$stream_client" "connection.invoke('Unsubscribe', options.symbol.toUpperCase(), options.chartRange)"

  assert_file_contains "$workflow" "chartRange: ChartRange"
  assert_file_contains "$workflow" "getCandles(normalizedSymbol, chartRange, chartIdentity)"
  assert_file_contains "$workflow" "getIndicators(normalizedSymbol, chartRange, chartIdentity)"
  assert_file_contains "$workflow" "fallbackTimer = window.setInterval(() => void refreshChartData(false)"
}

assert_symbol_page_ssr_markers() {
  local symbol_page="$repo_root/frontend/app/symbols/[symbol]/page.tsx"
  local terminal_app="$repo_root/frontend/components/terminal/ATradeTerminalApp.tsx"
  local chart_workspace="$repo_root/frontend/components/terminal/TerminalChartWorkspace.tsx"

  assert_file_contains "$symbol_page" "<ATradeTerminalApp initialChartRange={initialChartRange} initialIdentity={identity} initialModuleId={initialModuleId} initialSymbol={normalizedSymbol} />"
  assert_file_contains "$symbol_page" "createInitialChartRange"
  assert_file_contains "$symbol_page" "SUPPORTED_CHART_RANGES.includes"
  assert_file_contains "$terminal_app" "data-testid=\"terminal-chart-module\""
  assert_file_contains "$chart_workspace" "data-testid=\"chart-workspace\""
  assert_file_contains "$repo_root/frontend/components/terminal/TerminalInstrumentHeader.tsx" "Dense chart workspace header"
  assert_file_contains "$repo_root/frontend/components/CandlestickChart.tsx" "chart.timeScale().fitContent()"
  assert_file_contains "$chart_workspace" "chart.view.streamLabel"
}

main() {
  assert_chart_range_types
  assert_chart_range_controls
  assert_frontend_client_params
  assert_symbol_page_ssr_markers
}

main "$@"
