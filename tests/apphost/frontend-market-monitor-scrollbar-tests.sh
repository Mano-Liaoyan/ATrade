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
matches = list(re.finditer(pattern, css))
if not matches:
    print(f"expected CSS selector {selector!r} to exist in {css_path}", file=sys.stderr)
    sys.exit(1)
if not any(needle in match.group('body') for match in matches):
    print(f"expected CSS selector {selector!r} to contain {needle!r}", file=sys.stderr)
    sys.exit(1)
PY
}

assert_table_scroll_source_contract() {
  local table="$frontend_root/components/terminal/MarketMonitorTable.tsx"
  local scroll_area="$frontend_root/components/ui/scroll-area.tsx"
  local css="$frontend_root/app/globals.css"

  assert_file_contains "$table" 'data-scroll-owner="market-monitor-table"'
  assert_file_contains "$table" 'data-scrollbars="vertical horizontal"'
  assert_file_contains "$table" 'data-scroll-axis="vertical horizontal"'
  assert_file_contains "$table" 'type="always"'
  assert_file_contains "$table" 'className="market-monitor-table-scroll"'

  assert_file_contains "$scroll_area" 'data-slot="scroll-area-viewport"'
  assert_file_contains "$scroll_area" '<ScrollBar orientation="vertical" />'
  assert_file_contains "$scroll_area" '<ScrollBar orientation="horizontal" />'
  assert_file_contains "$scroll_area" 'data-slot="scroll-area-scrollbar"'
  assert_file_contains "$scroll_area" 'data-slot="scroll-area-thumb"'
  assert_file_contains "$scroll_area" 'data-slot="scroll-area-corner"'

  assert_css_rule_contains '.terminal-market-monitor__table-region' 'display: grid;'
  assert_css_rule_contains '.terminal-market-monitor__table-region' 'min-height: 0;'
  assert_css_rule_contains '.market-monitor-table-shell' 'overflow: hidden;'
  assert_css_rule_contains '.market-monitor-table-scroll' 'height: min(34rem, 62vh);'
  assert_css_rule_contains '.market-monitor-table-scroll' 'min-height: 16rem;'
  assert_css_rule_contains '.market-monitor-table-scroll' 'max-height: min(34rem, 62vh);'
  assert_css_rule_contains '.market-monitor-table-scroll' 'overflow: hidden;'
  assert_css_rule_contains '.market-monitor-table-scroll [data-slot="scroll-area-viewport"]' 'height: 100%;'
  assert_css_rule_contains '.market-monitor-table-scroll [data-slot="scroll-area-viewport"]' 'scrollbar-gutter: stable both-edges;'
  assert_css_rule_contains '.market-monitor-table-scroll [data-slot="scroll-area-scrollbar"]' 'opacity: 1;'
  assert_css_rule_contains '.market-monitor-table-scroll [data-slot="scroll-area-scrollbar"][data-orientation="vertical"]' 'width: 0.85rem;'
  assert_css_rule_contains '.market-monitor-table-scroll [data-slot="scroll-area-scrollbar"][data-orientation="horizontal"]' 'height: 0.85rem;'
  assert_css_rule_contains '.market-monitor-table-scroll [data-slot="scroll-area-thumb"]' 'background: hsl(var(--terminal-accent-amber) / 0.72);'
  assert_css_rule_contains '.market-monitor-table-scroll [data-slot="scroll-area-corner"]' 'background: hsl(var(--terminal-surface-elevated));'

  assert_file_contains "$css" '.terminal-market-monitor--compact .market-monitor-table-scroll,'
  assert_file_contains "$css" 'height: min(26rem, 54vh);'
  assert_file_contains "$css" '@media (max-width: 1100px)'
  assert_file_contains "$css" '.terminal-market-monitor__grid {'
  assert_file_contains "$css" 'height: min(28rem, 58dvh);'
}

assert_wide_table_and_sticky_header_contract() {
  local table="$frontend_root/components/terminal/MarketMonitorTable.tsx"
  local css="$frontend_root/app/globals.css"

  assert_file_contains "$table" "{ key: 'provider', label: 'Provider' }"
  assert_file_contains "$table" "{ key: 'providerSymbolId', label: 'Provider ID' }"
  assert_file_contains "$table" "{ key: 'exchange', label: 'Market' }"
  assert_file_contains "$table" "{ key: 'currency', label: 'CCY' }"
  assert_file_contains "$table" "{ key: 'assetClass', label: 'Asset' }"
  assert_file_contains "$table" "{ key: 'source', label: 'Source' }"
  assert_file_contains "$table" "{ key: 'score', label: 'Score' }"
  assert_file_contains "$table" "{ key: 'saved', label: 'Pin' }"
  assert_file_contains "$table" '<th scope="col">Actions</th>'
  assert_file_contains "$table" 'href={row.chartHref}'
  assert_file_contains "$table" 'href={row.analysisHref}'
  assert_file_contains "$table" 'onClick={() => onTogglePin(row)}'

  assert_css_rule_contains '.market-monitor-table' 'min-width: 78rem;'
  assert_css_rule_contains '.market-monitor-table thead th' 'position: sticky;'
  assert_css_rule_contains '.market-monitor-table thead th' 'top: 0;'
  assert_css_rule_contains '.market-monitor-table thead th' 'z-index: 1;'
}

assert_no_page_level_scroll_or_provider_dependency() {
  local css="$frontend_root/app/globals.css"
  local table="$frontend_root/components/terminal/MarketMonitorTable.tsx"

  assert_css_rule_contains 'html' 'overflow: hidden;'
  assert_css_rule_contains 'body' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app__body' 'overflow: hidden;'
  assert_css_rule_contains '.atrade-terminal-app__workspace' 'overflow: hidden;'
  assert_css_rule_contains '.terminal-workspace-layout' 'overflow: hidden;'
  assert_file_not_contains "$css" 'overflow-x: hidden'

  assert_file_not_contains "$table" 'fetch('
  assert_file_not_contains "$table" 'NEXT_PUBLIC_ATRADE_API_BASE_URL'
}

assert_validation_is_static_and_provider_independent() {
  local script="$repo_root/tests/apphost/frontend-market-monitor-scrollbar-tests.sh"

  assert_file_not_contains "$script" "cu""rl "
  assert_file_not_contains "$script" "npm run"" dev"
  assert_file_not_contains "$script" "NEXT_PUBLIC_ATRADE""_API_BASE_URL="
  assert_file_not_contains "$script" "ATRADE_FRONTEND""_DIRECT_HTTP_PORT"
}

main() {
  assert_table_scroll_source_contract
  assert_wide_table_and_sticky_header_contract
  assert_no_page_level_scroll_or_provider_dependency
  assert_validation_is_static_and_provider_independent

  printf 'Market monitor visible scrollbar validation passed.\n'
}

main "$@"
