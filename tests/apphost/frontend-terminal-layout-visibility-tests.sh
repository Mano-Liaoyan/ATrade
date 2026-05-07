#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
frontend_root="$repo_root/frontend"
css="$frontend_root/app/globals.css"

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

  python3 - "$css" "$selector" "$needle" <<'PY'
import re
import sys
from pathlib import Path

css_path = Path(sys.argv[1])
selector = sys.argv[2]
needle = sys.argv[3]
css = css_path.read_text(encoding='utf-8')
pattern = re.escape(selector) + r"\s*\{(?P<body>[^{}]*)\}"
matches = list(re.finditer(pattern, css))
if not matches:
    print(f"expected CSS selector {selector!r} to exist in {css_path}", file=sys.stderr)
    sys.exit(1)
if not any(needle in match.group('body') for match in matches):
    print(f"expected CSS selector {selector!r} to contain {needle!r}", file=sys.stderr)
    sys.exit(1)
PY
}

assert_guardrail_docs() {
  assert_file_contains "$repo_root/AGENTS.md" 'latest stable Safari, Firefox, Chrome, and Edge must behave consistently'
  assert_file_contains "$repo_root/AGENTS.md" 'no content is clipped or unreachable'
  assert_file_contains "$repo_root/AGENTS.md" 'Safari may hide native OS scrollbars'
  assert_file_contains "$repo_root/AGENTS.md" 'Mobile optimization is not in scope'

  assert_file_contains "$repo_root/tasks/CONTEXT.md" 'latest stable desktop'
  assert_file_contains "$repo_root/tasks/CONTEXT.md" 'Safari, Firefox, Chrome, and Edge'
  assert_file_contains "$repo_root/tasks/CONTEXT.md" 'page-level scrolling disabled'
  assert_file_contains "$repo_root/tasks/CONTEXT.md" 'NODE and ORDERS'
  assert_file_contains "$repo_root/tasks/CONTEXT.md" 'app-owned or explicitly styled visible scrollbar tracks/thumbs'

  assert_file_contains "$repo_root/docs/design/atrade-terminal-ui.md" 'latest stable desktop'
  assert_file_contains "$repo_root/docs/design/atrade-terminal-ui.md" 'Safari, Firefox, Chrome, or Edge'
  assert_file_contains "$repo_root/docs/design/atrade-terminal-ui.md" 'page-level `overflow: hidden`'
  assert_file_contains "$repo_root/docs/design/atrade-terminal-ui.md" 'ATrade-owned custom tracks/thumbs'
  assert_file_contains "$repo_root/docs/design/atrade-terminal-ui.md" 'late-list items such as NODE'
  assert_file_contains "$repo_root/docs/design/atrade-terminal-ui.md" 'ORDERS remain fully reachable'
}

assert_shell_scroll_source_contract() {
  local rail="$frontend_root/components/terminal/TerminalModuleRail.tsx"
  local layout="$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx"

  assert_css_rule_contains 'html' 'overflow: hidden;'
  assert_css_rule_contains 'body' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app' 'height: 100dvh;'
  assert_css_rule_contains '.atrade-terminal-app' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app__body' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app__workspace' 'overflow: hidden;'
  assert_css_rule_contains '.terminal-workspace-layout' 'overflow: hidden;'

  assert_file_contains "$rail" 'className="terminal-module-rail__navigation terminal-scroll-owned terminal-rail-scroll-owned"'
  assert_file_contains "$rail" 'data-scroll-owner="module-rail"'
  assert_file_contains "$rail" 'aria-label="Future disabled modules"'
  assert_css_rule_contains '.terminal-module-rail' 'grid-template-rows: auto minmax(0, 1fr);'
  assert_css_rule_contains '.terminal-module-rail' 'max-block-size: 100%;'
  assert_css_rule_contains '.terminal-module-rail' 'overflow: hidden;'
  assert_css_rule_contains '.terminal-module-rail__navigation' 'overflow: auto;'
  assert_css_rule_contains '.terminal-module-rail__navigation' 'min-height: 0;'

  assert_file_contains "$layout" 'className="terminal-workspace-layout__primary terminal-scroll-owned terminal-workspace-scroll-owned"'
  assert_file_contains "$layout" 'data-scroll-owner="primary-workspace"'
  assert_file_contains "$layout" 'data-layout-region="primary"'
  assert_css_rule_contains '.terminal-workspace-layout__primary' 'overflow: auto;'
  assert_css_rule_contains '.terminal-workspace-layout__primary' 'scrollbar-gutter: stable both-edges;'
}

assert_visible_scrollbar_contract() {
  assert_css_rule_contains '.terminal-scroll-owned' 'scrollbar-color:'
  assert_css_rule_contains '.terminal-scroll-owned' 'scrollbar-gutter: stable;'
  assert_css_rule_contains '.terminal-scroll-owned' 'scrollbar-width: thin;'
  assert_file_contains "$css" '.terminal-scroll-owned::-webkit-scrollbar {'
  assert_file_contains "$css" '.terminal-scroll-owned::-webkit-scrollbar-track {'
  assert_file_contains "$css" '.terminal-scroll-owned::-webkit-scrollbar-thumb {'
  assert_file_contains "$css" '.terminal-scroll-owned::-webkit-scrollbar-corner {'
  assert_file_contains "$css" 'background: hsl(var(--terminal-accent-amber) / 0.74);'
}

assert_module_panel_visibility_contract() {
  local detail="$frontend_root/components/terminal/MarketMonitorDetailPanel.tsx"
  local chart="$frontend_root/components/terminal/TerminalChartWorkspace.tsx"
  local analysis="$frontend_root/components/terminal/TerminalAnalysisWorkspace.tsx"
  local backtest="$frontend_root/components/terminal/TerminalBacktestWorkspace.tsx"
  local status="$frontend_root/components/terminal/TerminalStatusModule.tsx"
  local help="$frontend_root/components/terminal/TerminalHelpModule.tsx"
  local disabled="$frontend_root/components/terminal/TerminalDisabledModule.tsx"
  local comparison="$frontend_root/components/terminal/BacktestComparisonPanel.tsx"

  assert_file_contains "$detail" 'data-scroll-owner="market-monitor-detail"'
  assert_file_contains "$detail" 'market-monitor-detail terminal-scroll-owned'
  assert_css_rule_contains '.market-monitor-detail' 'max-block-size: min(34rem, calc(100dvh - 4rem));'
  assert_css_rule_contains '.market-monitor-detail' 'overflow: auto;'
  assert_css_rule_contains '.market-monitor-detail__identity dd' 'overflow-wrap: anywhere;'
  assert_css_rule_contains '.market-monitor-detail__identity dd' 'white-space: normal;'

  assert_file_contains "$chart" 'data-scroll-owner="chart-module"'
  assert_file_contains "$chart" 'data-scroll-owner="chart-workspace-region"'
  assert_file_contains "$chart" 'terminal-chart-workspace__chart-region terminal-scroll-owned'
  assert_css_rule_contains '.terminal-chart-workspace__chart-region' 'overflow: auto;'
  assert_css_rule_contains '.terminal-chart-workspace__chart-region' 'scrollbar-gutter: stable;'

  assert_file_contains "$analysis" 'data-scroll-owner="analysis-module"'
  assert_file_contains "$backtest" 'data-scroll-owner="backtest-module"'
  assert_file_contains "$backtest" 'data-scroll-owner="backtest-history"'
  assert_file_contains "$backtest" 'data-scroll-owner="backtest-signals-list"'
  assert_file_contains "$backtest" 'data-scroll-owner="backtest-trades-list"'
  assert_file_contains "$comparison" 'data-scroll-owner="backtest-comparison-metrics"'
  assert_file_contains "$status" 'data-scroll-owner="status-module"'
  assert_file_contains "$help" 'data-scroll-owner="help-module"'
  assert_file_contains "$disabled" 'data-scroll-owner="disabled-module"'
  assert_css_rule_contains '.terminal-module-scroll-surface' 'overflow-wrap: anywhere;'
  assert_css_rule_contains '.terminal-backtest-history__list' 'overflow: auto;'
  assert_css_rule_contains '.terminal-backtest-detail__scroll-list' 'overflow: auto;'
  assert_css_rule_contains '.terminal-backtest-comparison__table-wrap' 'overflow: auto;'
}

assert_no_page_scroll_regression_or_provider_dependency() {
  local script="$repo_root/tests/apphost/frontend-terminal-layout-visibility-tests.sh"

  assert_file_not_contains "$css" 'overflow-x: hidden'
  assert_file_not_contains "$script" "cu""rl "
  assert_file_not_contains "$script" "npm run"" dev"
  assert_file_not_contains "$script" "NEXT_PUBLIC_ATRADE""_API_BASE_URL="
  assert_file_not_contains "$script" "ATRADE_FRONTEND""_DIRECT_HTTP_PORT"
}

main() {
  assert_guardrail_docs
  assert_shell_scroll_source_contract
  assert_visible_scrollbar_contract
  assert_module_panel_visibility_contract
  assert_no_page_scroll_regression_or_provider_dependency

  printf 'Frontend terminal layout visibility validation passed.\n'
}

main "$@"
