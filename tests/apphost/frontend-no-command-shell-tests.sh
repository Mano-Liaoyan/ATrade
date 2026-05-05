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

assert_path_missing() {
  local path="$1"

  if [[ -e "$path" ]]; then
    printf 'expected command-system path to be absent: %s\n' "$path" >&2
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
    --exclude='frontend-no-command-shell-tests.sh' \
    "$pattern" \
    "$@"; then
    printf 'unexpected %s found.\n' "$description" >&2
    return 1
  fi
}

assert_command_system_removed_from_frontend() {
  assert_path_missing "$frontend_root/components/terminal/TerminalCommandInput.tsx"
  assert_path_missing "$frontend_root/lib/terminalCommandRegistry.ts"

  assert_no_grep_matches \
    'command input, parser, registry, command feedback, or command grammar in active frontend source' \
    'TerminalCommandInput|terminalCommandRegistry|TerminalCommand(Parse|Action)|parseTerminalCommand|TERMINAL_COMMAND|terminal-command-input|data-testid="terminal-command-input"|commandLabel|commandFeedback|handleCommand|deterministic command|command grammar|command input|command help|Type a command|Supported commands:|CHART <symbol>|SEARCH <query>|ANALYSIS <symbol>' \
    "$frontend_root/app" "$frontend_root/components" "$frontend_root/lib" "$frontend_root/types"

  assert_no_grep_matches \
    'visible retired terminal brand or command-first product copy in active frontend source' \
    'ATrade Terminal|ATrade Terminal Shell|Command-first paper workspace' \
    "$frontend_root/app" "$frontend_root/components" "$frontend_root/lib" "$frontend_root/types" "$frontend_root/app/globals.css"
}

assert_validation_scripts_have_no_stale_command_assertions() {
  assert_no_grep_matches \
    'stale positive command-shell assertions in frontend apphost validation scripts' \
    'frontend-terminal-shell-command-tests\.sh|assert_file_contains[^\n]*(TerminalCommandInput|terminalCommandRegistry|terminal-command-input|parseTerminalCommand|TERMINAL_COMMAND|Supported commands:|ATrade Terminal Shell|Command-first paper workspace|CHART <symbol>|SEARCH <query>|ANALYSIS <symbol>|deterministic command|command input|command help|Type a command)' \
    "$repo_root/tests/apphost"/frontend-*.sh
}

assert_module_and_workflow_navigation_preserved() {
  local app="$frontend_root/components/terminal/ATradeTerminalApp.tsx"
  local rail="$frontend_root/components/terminal/TerminalModuleRail.tsx"
  local monitor="$frontend_root/components/terminal/TerminalMarketMonitor.tsx"
  local monitor_workflow="$frontend_root/lib/terminalMarketMonitorWorkflow.ts"
  local module_registry="$frontend_root/lib/terminalModuleRegistry.ts"
  local terminal_types="$frontend_root/types/terminal.ts"

  for enabled in HOME SEARCH WATCHLIST CHART ANALYSIS STATUS HELP; do
    assert_file_contains "$terminal_types" "\"$enabled\""
    assert_file_contains "$module_registry" "id: \"$enabled\""
    assert_file_contains "$module_registry" 'availability: "enabled"'
  done

  assert_file_contains "$app" '<TerminalModuleRail'
  assert_file_contains "$app" 'function handleModuleSelect(moduleId: EnabledTerminalModuleId)'
  assert_file_contains "$app" 'openIntent('
  assert_file_contains "$app" 'getModuleFocusTargetId(moduleId)'
  assert_file_contains "$rail" 'data-testid="terminal-module-rail"'
  assert_file_contains "$rail" 'getEnabledTerminalModules'
  assert_file_contains "$rail" 'getDisabledTerminalModules'
  assert_file_contains "$monitor" 'workflow.openChartIntent(row)'
  assert_file_contains "$monitor" 'workflow.openAnalysisIntent(row)'
  assert_file_contains "$monitor_workflow" 'createChartNavigationIntent'
  assert_file_contains "$monitor_workflow" 'createAnalysisNavigationIntent'
  assert_file_contains "$monitor_workflow" 'identity: row.exactIdentity'
  assert_file_contains "$monitor_workflow" "route: moduleId === 'ANALYSIS' ? row.analysisHref : row.chartHref"
}

assert_safety_boundaries_preserved() {
  local app="$frontend_root/components/terminal/ATradeTerminalApp.tsx"
  local help="$frontend_root/components/terminal/TerminalHelpModule.tsx"
  local status="$frontend_root/components/terminal/TerminalStatusModule.tsx"
  local diagnostics="$frontend_root/components/terminal/TerminalProviderDiagnostics.tsx"
  local disabled="$frontend_root/components/terminal/TerminalDisabledModule.tsx"
  local module_registry="$frontend_root/lib/terminalModuleRegistry.ts"

  assert_file_contains "$app" 'ATrade.Api boundary'
  assert_file_contains "$app" 'exact instrument identity'
  assert_file_contains "$app" 'Orders are disabled by the paper-only safety contract.'
  assert_file_contains "$help" 'All browser-visible data flows through ATrade.Api'
  assert_file_contains "$help" 'Provider-not-configured, provider-unavailable, authentication-required, and no-analysis-engine states remain explicit'
  assert_file_contains "$help" 'no order tickets, buy/sell controls, previews, or submit actions'
  assert_file_contains "$status" 'Browser routes through ATrade.Api only.'
  assert_file_contains "$diagnostics" 'workspace renders no order-entry controls and does not call broker order routes.'
  assert_file_contains "$disabled" 'no fake data, no demo provider responses, and no order-entry controls'

  for disabled_module in NEWS PORTFOLIO RESEARCH SCREENER ECON AI NODE ORDERS; do
    assert_file_contains "$module_registry" "id: \"$disabled_module\""
    assert_file_contains "$module_registry" 'availability: "disabled"'
  done

  assert_no_grep_matches \
    'secrets, account identifiers, tokens, or session cookies in frontend source' \
    'DU[0-9]{6,}|U[0-9]{7,}|IBKR_(USERNAME|PASSWORD)[[:space:]]*=|([Aa]ccess|[Rr]efresh|[Ss]ession)[_-]?[Tt]oken[[:space:]]*[:=]|Cookie:|Set-Cookie|sessionid=|JSESSIONID=|Bearer[[:space:]]+[A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.|password[[:space:]]*[:=][[:space:]]*['"'"'][^'"'"']+' \
    "$frontend_root/app" "$frontend_root/components" "$frontend_root/lib" "$frontend_root/types"
}

main() {
  assert_command_system_removed_from_frontend
  assert_validation_scripts_have_no_stale_command_assertions
  assert_module_and_workflow_navigation_preserved
  assert_safety_boundaries_preserved

  printf 'No-command shell validation passed.\n'
}

main "$@"
