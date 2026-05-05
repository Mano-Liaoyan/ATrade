#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
frontend_root="$repo_root/frontend"
css="$frontend_root/app/globals.css"
tailwind="$frontend_root/tailwind.config.ts"
chart="$frontend_root/components/CandlestickChart.tsx"

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

  if [[ -f "$file_path" ]] && grep -Fqi -- "$needle" "$file_path"; then
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
match = re.search(pattern, css)
if not match:
    print(f"expected CSS selector {selector!r} to exist in {css_path}", file=sys.stderr)
    sys.exit(1)
if needle not in match.group('body'):
    print(f"expected CSS selector {selector!r} to contain {needle!r}", file=sys.stderr)
    sys.exit(1)
PY
}

assert_original_terminal_tokens() {
  assert_file_contains "$css" '--terminal-canvas: 42 18% 3%;'
  assert_file_contains "$css" '--terminal-surface: 40 12% 6%;'
  assert_file_contains "$css" '--terminal-surface-elevated: 38 11% 9%;'
  assert_file_contains "$css" '--terminal-surface-inset: 43 16% 4%;'
  assert_file_contains "$css" '--terminal-border: 38 8% 20%;'
  assert_file_contains "$css" '--terminal-border-strong: 36 10% 30%;'
  assert_file_contains "$css" '--terminal-splitter-active: 35 42% 34%;'
  assert_file_contains "$css" '--terminal-accent-amber: 32 94% 54%;'
  assert_file_contains "$css" '--terminal-accent-orange: 25 88% 50%;'
  assert_file_contains "$css" '--terminal-accent-green: 145 58% 48%;'
  assert_file_contains "$css" '--terminal-accent-red: 356 70% 59%;'
  assert_file_contains "$css" '--terminal-focus-ring: 36 94% 58%;'
  assert_file_contains "$css" '--terminal-chart-background: 42 18% 3%;'
  assert_file_contains "$css" '--terminal-chart-grid: 38 7% 24%;'
  assert_file_contains "$css" '--ui-muted: hsl(var(--terminal-text-muted));'
  assert_file_contains "$css" '--ui-accent: hsl(var(--terminal-accent-amber));'

  assert_file_contains "$tailwind" '"border-strong": "hsl(var(--terminal-border-strong))"'
  assert_file_contains "$tailwind" 'grid: "hsl(var(--terminal-chart-grid))"'
  assert_file_contains "$tailwind" '"splitter-active": "hsl(var(--terminal-splitter-active))"'
  assert_file_contains "$tailwind" 'orange: "hsl(var(--terminal-accent-orange))"'
  assert_file_contains "$tailwind" 'focus: "hsl(var(--terminal-focus-ring))"'
}

assert_black_graphite_shell_and_panels() {
  assert_css_rule_contains 'body' 'linear-gradient(135deg, hsl(var(--terminal-canvas)) 0%, hsl(var(--terminal-surface-inset)) 58%, hsl(var(--terminal-surface)) 100%)'
  assert_css_rule_contains '.atrade-terminal-app' 'background: linear-gradient(135deg, hsl(var(--terminal-canvas) / 0.99), hsl(var(--terminal-surface-inset) / 0.96));'
  assert_css_rule_contains '.terminal-module-rail' 'background: hsl(var(--terminal-surface) / 0.88);'
  assert_css_rule_contains '.terminal-workspace-layout__primary' 'background: hsl(var(--terminal-surface-inset) / 0.56);'
  assert_css_rule_contains '.workspace-panel' 'background: hsl(var(--terminal-surface) / 0.94);'
  assert_css_rule_contains '.terminal-data-panel' 'hsl(var(--terminal-surface) / 0.82)'
}

assert_amber_primary_focus_and_rectangular_density() {
  assert_css_rule_contains '::selection' 'background: hsl(var(--terminal-accent-amber) / 0.28);'
  assert_css_rule_contains '.terminal-module-rail__item--active' 'hsl(var(--terminal-accent-amber)'
  assert_css_rule_contains '.terminal-chart-range-button--active' 'hsl(var(--terminal-accent-amber) / 0.16)'
  assert_css_rule_contains '.chart-container' 'border-radius: 2px;'
  assert_css_rule_contains '.workspace-panel' 'border-radius: 2px;'
  assert_file_contains "$frontend_root/components/ui/button.tsx" 'focus-visible:ring-terminal-amber'
  assert_file_contains "$frontend_root/components/ui/button.tsx" 'border-terminal-amber/50 bg-terminal-amber/16 text-terminal-amber'
  assert_file_contains "$frontend_root/components/ui/input.tsx" 'focus:border-terminal-amber focus:ring-2 focus:ring-terminal-amber/30'
  assert_file_contains "$frontend_root/components/ui/tabs.tsx" 'data-[state=active]:bg-terminal-amber/12 data-[state=active]:text-terminal-amber'
  assert_file_contains "$frontend_root/components/terminal/TerminalSectionHeader.tsx" 'text-terminal-amber'
  assert_file_contains "$frontend_root/components/terminal/TerminalPanel.tsx" 'compact: "p-2.5"'
  assert_file_contains "$frontend_root/components/ui/scroll-area.tsx" 'rounded-[1px] bg-terminal-splitter-active/75'
}

assert_market_state_and_chart_palette() {
  assert_file_contains "$css" '--status-success: 145 58% 48%;'
  assert_file_contains "$css" '--status-danger: 356 70% 59%;'
  assert_file_contains "$css" '--status-warning: 32 94% 54%;'
  assert_file_contains "$chart" 'const ChartColors = {'
  assert_file_contains "$chart" "background: '#090806'"
  assert_file_contains "$chart" "text: '#e9e4d8'"
  assert_file_contains "$chart" "up: '#36bf73'"
  assert_file_contains "$chart" "down: '#e35d6a'"
  assert_file_contains "$chart" "neutralVolume: 'rgba(196, 124, 28, 0.28)'"
  assert_file_contains "$chart" "smaFast: '#ee9f22'"
  assert_file_contains "$chart" "smaSlow: '#9aa8ba'"
  assert_file_contains "$chart" 'color: candle.close >= candle.open ? ChartColors.upVolume : ChartColors.downVolume'
}

assert_no_cyan_blue_dominance_or_token_mismatches() {
  assert_file_not_contains "$css" 'var(--muted)'
  assert_file_not_contains "$css" 'var(--accent)'
  assert_file_not_contains "$css" 'rgba(56, 189, 248'
  assert_file_not_contains "$css" '#38bdf8'
  assert_file_not_contains "$css" 'terminal-accent-cyan) / 0.'

  if grep -RIn --exclude-dir=.next --exclude-dir=node_modules -E 'terminal-cyan|bg-terminal-blue|text-terminal-blue|border-terminal-blue|ring-terminal-blue|from-blue|to-blue|from-cyan|to-cyan|sky-' \
    "$frontend_root/app" "$frontend_root/components" "$frontend_root/lib"; then
    printf 'frontend theme must not use cyan/blue utilities as the dominant active palette.\n' >&2
    return 1
  fi
}

assert_clean_room_and_provider_independent_sources() {
  if grep -RIn --exclude-dir=.next --exclude-dir=node_modules -E 'Fincept|FinceptTerminal|Bloomberg|BLOOMBERG|BLP|bbg-terminal|bloomberg-terminal|proprietary screenshot|copied asset' \
    "$frontend_root/app" "$frontend_root/components" "$frontend_root/lib" "$frontend_root/types" "$frontend_root/tailwind.config.ts" "$frontend_root/package.json"; then
    printf 'active frontend source must not include third-party terminal branding, copied assets, or proprietary references.\n' >&2
    return 1
  fi

  if grep -RIn --exclude-dir=.next --exclude-dir=node_modules -E 'IBKR_USERNAME|IBKR_PASSWORD|IBeam|Client Portal|ATRADE_IBKR|ATRADE_LEAN|postgres://|timescaledb://|redis://|nats://' \
    "$frontend_root/app" "$frontend_root/components" "$frontend_root/lib" "$frontend_root/types"; then
    printf 'theme validation must remain browser/API-boundary safe and provider-independent.\n' >&2
    return 1
  fi
}

main() {
  assert_original_terminal_tokens
  assert_black_graphite_shell_and_panels
  assert_amber_primary_focus_and_rectangular_density
  assert_market_state_and_chart_palette
  assert_no_cyan_blue_dominance_or_token_mismatches
  assert_clean_room_and_provider_independent_sources
  (cd "$frontend_root" && npm ci --no-fund --no-audit >/dev/null && npm run build)
  printf 'ATrade terminal theme refactor validation passed.\n'
}

main "$@"
