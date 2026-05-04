#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

types_file="$repo_root/frontend/types/terminal.ts"
module_registry="$repo_root/frontend/lib/terminalModuleRegistry.ts"
command_registry="$repo_root/frontend/lib/terminalCommandRegistry.ts"
disabled_component="$repo_root/frontend/components/terminal/TerminalDisabledModule.tsx"

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

assert_terminal_module_registry_contract() {
  for enabled in HOME SEARCH WATCHLIST CHART ANALYSIS STATUS HELP; do
    assert_file_contains "$types_file" 'ENABLED_TERMINAL_MODULE_IDS'
    assert_file_contains "$types_file" "\"$enabled\""
    assert_file_contains "$module_registry" "id: \"$enabled\""
    assert_file_contains "$module_registry" 'availability: "enabled"'
  done

  for disabled in NEWS PORTFOLIO RESEARCH SCREENER ECON AI NODE ORDERS; do
    assert_file_contains "$types_file" 'DISABLED_TERMINAL_MODULE_IDS'
    assert_file_contains "$types_file" "\"$disabled\""
    assert_file_contains "$module_registry" "id: \"$disabled\""
    assert_file_contains "$module_registry" 'availability: "disabled"'
  done

  assert_file_contains "$module_registry" 'No committed news provider or news API exists in ATrade yet.'
  assert_file_contains "$module_registry" 'No durable positions or portfolio P/L workspace exists'
  assert_file_contains "$module_registry" 'No research-document ingestion, fundamentals provider, or analyst-rating API'
  assert_file_contains "$module_registry" 'The current backend supports scanner/trending and bounded symbol search only.'
  assert_file_contains "$module_registry" 'No economic calendar, macro series, or central-bank feed'
  assert_file_contains "$module_registry" 'No committed AI assistant, model runtime, tool-use backend, or retrieval contract'
  assert_file_contains "$module_registry" 'No node-graph workflow or visual strategy graph runtime'
  assert_file_contains "$module_registry" 'Orders are disabled by the paper-only safety contract.'
  assert_file_contains "$module_registry" 'does not provide order tickets, buy/sell buttons, staged submissions, previews, or confirmations'
}

assert_terminal_command_registry_contract() {
  local command_count
  command_count="$(grep -Ec 'command: "(HOME|SEARCH|CHART|WATCH|WATCHLIST|ANALYSIS|STATUS|HELP)"' "$command_registry")"
  if [[ "$command_count" != '8' ]]; then
    printf 'expected exactly 8 first-release command definitions, found %s\n' "$command_count" >&2
    return 1
  fi

  assert_file_contains "$command_registry" 'Supported commands: HOME, SEARCH <query>, CHART <symbol>, WATCH, WATCHLIST, ANALYSIS <symbol>, STATUS, HELP.'
  assert_file_contains "$command_registry" 'command: "HOME"'
  assert_file_contains "$command_registry" 'command: "SEARCH"'
  assert_file_contains "$command_registry" 'command: "CHART"'
  assert_file_contains "$command_registry" 'command: "WATCH"'
  assert_file_contains "$command_registry" 'command: "WATCHLIST"'
  assert_file_contains "$command_registry" 'command: "ANALYSIS"'
  assert_file_contains "$command_registry" 'command: "STATUS"'
  assert_file_contains "$command_registry" 'command: "HELP"'
  assert_file_contains "$command_registry" 'moduleId: "WATCHLIST"'
  assert_file_contains "$command_registry" 'case "WATCH":'
  assert_file_contains "$command_registry" 'case "WATCHLIST":'
  assert_file_contains "$command_registry" 'Unknown command'
  assert_file_contains "$command_registry" 'CHART requires a symbol, for example CHART AAPL.'
  assert_file_contains "$command_registry" 'isDisabledTerminalModuleId(command)'
  assert_file_contains "$command_registry" 'getTerminalDisabledModuleState(moduleId)'

  assert_file_not_contains "$command_registry" 'command: "QUOTE"'
  assert_file_not_contains "$command_registry" 'command: "ORDER"'
  assert_file_not_contains "$command_registry" 'command: "ORDERS"'
  assert_file_not_contains "$command_registry" 'command: "TRADE"'
  assert_file_not_contains "$command_registry" 'command: "BUY"'
  assert_file_not_contains "$command_registry" 'command: "SELL"'
  assert_file_not_contains "$command_registry" 'command: "W"'
  assert_file_not_contains "$command_registry" 'command: "WL"'
  assert_file_not_contains "$command_registry" 'command: "HELP ME"'
}

assert_no_natural_language_or_backend_command_routing() {
  if grep -RIn --exclude-dir=.next --exclude-dir=node_modules -E 'natural.?language|fuzzy|semantic|OpenAI|ChatGPT|LLM|chat completion|completion API|ai route|ai router' "$command_registry"; then
    printf 'terminal command registry must stay deterministic and must not contain natural-language or LLM routing.\n' >&2
    return 1
  fi

  assert_file_not_contains "$command_registry" 'fetch('
  assert_file_not_contains "$command_registry" 'XMLHttpRequest'
  assert_file_not_contains "$command_registry" 'localStorage'
  assert_file_not_contains "$command_registry" '/api/orders'
  assert_file_not_contains "$command_registry" '/api/analysis/run'
}

assert_disabled_module_component_contract() {
  assert_file_contains "$disabled_component" 'export function TerminalDisabledModule'
  assert_file_contains "$disabled_component" 'data-testid={`terminal-disabled-module-${unavailable.module.id.toLowerCase()}`}'
  assert_file_contains "$disabled_component" 'Visible-disabled module'
  assert_file_contains "$disabled_component" 'Not available'
  assert_file_contains "$disabled_component" 'no fake data, no demo provider responses, and no order-entry controls'
  assert_file_contains "$disabled_component" 'Type HELP for enabled commands.'
  assert_file_not_contains "$disabled_component" 'Place order'
  assert_file_not_contains "$disabled_component" 'Submit order'
  assert_file_not_contains "$disabled_component" 'type="submit"'
}

main() {
  assert_terminal_module_registry_contract
  assert_terminal_command_registry_contract
  assert_no_natural_language_or_backend_command_routing
  assert_disabled_module_component_contract
}

main "$@"
