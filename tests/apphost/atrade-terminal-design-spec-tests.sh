#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
spec="$repo_root/docs/design/atrade-terminal-ui.md"

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

assert_design_authority_exists() {
  assert_file_contains "$spec" 'status: active'
  assert_file_contains "$spec" 'summary: Active ATrade Terminal UI design authority'
  assert_file_contains "$spec" '# ATrade Terminal UI Design Spec'
  assert_file_contains "$spec" '../architecture/paper-trading-workspace.md'
  assert_file_contains "$spec" '../architecture/modules.md'
  assert_file_contains "$spec" '../architecture/provider-abstractions.md'
  assert_file_contains "$spec" '../architecture/analysis-engines.md'
  assert_file_contains "$spec" '../../README.md'
  assert_file_contains "$spec" '../../PLAN.md'
}

assert_clean_room_guardrails() {
  assert_file_contains "$spec" 'FinceptTerminal-style public product imagery and'
  assert_file_contains "$spec" 'Bloomberg-like command workflows only as broad visual and interaction'
  assert_file_contains "$spec" 'Do not copy FinceptTerminal source code'
  assert_file_contains "$spec" 'assets, screenshots, icons, names, trademarks, branding'
  assert_file_contains "$spec" 'Do not copy Bloomberg Terminal proprietary layouts'
  assert_file_contains "$spec" 'Do not import, trace, crop, or recreate proprietary screenshots'
  assert_file_contains "$spec" 'The shipped interface must read as ATrade'
}

assert_product_target_decisions() {
  assert_file_contains "$spec" 'full frontend reconstruction'
  assert_file_contains "$spec" 'not a light reskin'
  assert_file_contains "$spec" 'Next.js web terminal first'
  assert_file_contains "$spec" 'Future wrapper compatibility'
  assert_file_contains "$spec" 'desktop and laptop screens'
  assert_file_contains "$spec" 'simplified responsive fallback'
  assert_file_contains "$spec" 'not expected to'
  assert_file_contains "$spec" 'full multi-panel terminal experience'
}

assert_enabled_modules() {
  for module in HOME SEARCH WATCHLIST CHART ANALYSIS STATUS HELP; do
    assert_file_contains "$spec" "\`$module\`"
  done

  assert_file_contains "$spec" 'GET /api/market-data/trending'
  assert_file_contains "$spec" 'GET /api/market-data/search?query=...&assetClass=stock&limit=...'
  assert_file_contains "$spec" 'GET /api/market-data/{symbol}/candles?range=...'
  assert_file_contains "$spec" 'GET /api/market-data/{symbol}/indicators?range=...'
  assert_file_contains "$spec" 'GET /api/analysis/engines'
  assert_file_contains "$spec" 'POST /api/analysis/run'
  assert_file_contains "$spec" 'GET` / `PUT` / `POST /api/workspace/watchlist'
  assert_file_contains "$spec" 'exact `DELETE /api/workspace/watchlist/pins/{instrumentKey}`'
}

assert_disabled_modules() {
  for module in NEWS PORTFOLIO RESEARCH SCREENER ECON AI NODE ORDERS; do
    assert_file_contains "$spec" "\`$module\`"
  done

  assert_file_contains "$spec" 'must not be keyboard-selectable as'
  assert_file_contains "$spec" 'honest unavailable copy instead of mock data'
  assert_file_contains "$spec" 'No provider configured in ATrade yet'
  assert_file_contains "$spec" 'Orders are disabled by the paper-only safety contract'
  assert_file_contains "$spec" 'must not display fake tables'
}

assert_terminal_commands() {
  assert_file_contains "$spec" 'The command bar is a deterministic router'
  assert_file_contains "$spec" '`HOME` | Open/focus the `HOME` module.'
  assert_file_contains "$spec" '`SEARCH <query>`'
  assert_file_contains "$spec" '`CHART <symbol>`'
  assert_file_contains "$spec" '`WATCH` | Open/focus the `WATCHLIST` module.'
  assert_file_contains "$spec" '`WATCHLIST` | Alias for `WATCH`'
  assert_file_contains "$spec" '`ANALYSIS <symbol>`'
  assert_file_contains "$spec" '`STATUS` | Open/focus the `STATUS` module.'
  assert_file_contains "$spec" '`HELP` | Open/focus the `HELP` module'
  assert_file_contains "$spec" 'Unknown commands must not try fuzzy execution or AI completion'
}

assert_layout_behavior() {
  assert_file_contains "$spec" 'Resizable Multi-Panel Workspace'
  assert_file_contains "$spec" 'top command/header region, left module'
  assert_file_contains "$spec" 'accessible handles'
  assert_file_contains "$spec" 'atrade.terminal.layout.v1'
  assert_file_contains "$spec" 'The rail lists enabled modules'
  assert_file_contains "$spec" 'Top Command/Header Region'
  assert_file_contains "$spec" 'Status/Ticker Strip'
  assert_file_contains "$spec" 'Responsive And Laptop Fallback Rules'
  assert_file_contains "$spec" 'single-column flow'
}

assert_visual_system() {
  assert_file_contains "$spec" 'modern institutional'
  assert_file_contains "$spec" 'Dark dense panels'
  assert_file_contains "$spec" 'High-contrast data hierarchy'
  assert_file_contains "$spec" 'Compact typography'
  assert_file_contains "$spec" 'Grid/table density'
  assert_file_contains "$spec" 'amber, cyan, green, and red accents'
  assert_file_contains "$spec" 'Rectangular/resizable paneling'
  assert_file_contains "$spec" 'Non-generic shadcn styling'
}

assert_stack_direction() {
  assert_file_contains "$spec" 'shadcn/ui-style'
  assert_file_contains "$spec" 'Tailwind CSS and Radix primitives'
  assert_file_contains "$spec" 'define ATrade'
  assert_file_contains "$spec" 'terminal tokens for shell backgrounds'
  assert_file_contains "$spec" 'Generated/default examples must be heavily restyled'
  assert_file_contains "$spec" 'Build reusable original ATrade primitives'
}

assert_replacement_rules() {
  assert_file_contains "$spec" 'aggressively replace frontend rendering and styling'
  assert_file_contains "$spec" 'Existing page layouts, visual components'
  assert_file_contains "$spec" 'Preserve browser-facing `ATrade.Api` endpoint contracts'
  assert_file_contains "$spec" 'watchlist load/migration/pin/unpin logic'
  assert_file_contains "$spec" 'Preserve exact instrument identity handoff'
}

assert_safety_constraints() {
  assert_file_contains "$spec" 'Do not add order-entry UI in this batch'
  assert_file_contains "$spec" 'Do not add a simulated-submit workflow'
  assert_file_contains "$spec" 'Do not add real or live order placement behavior'
  assert_file_contains "$spec" 'Do not let the browser connect directly to Postgres, TimescaleDB, Redis, NATS,'
  assert_file_contains "$spec" 'IBKR/iBeam, LEAN, or any provider runtime'
  assert_file_contains "$spec" 'All browser-visible data must flow through `ATrade.Api`'
  assert_file_contains "$spec" 'rather than fallback mocks'
}

assert_design_authority_exists
assert_clean_room_guardrails
assert_product_target_decisions
assert_enabled_modules
assert_disabled_modules
assert_terminal_commands
assert_layout_behavior
assert_visual_system
assert_stack_direction
assert_replacement_rules
assert_safety_constraints

printf 'ATrade Terminal design spec validation passed.\n'
