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

assert_design_authority_exists
assert_clean_room_guardrails
assert_product_target_decisions

printf 'ATrade Terminal design spec validation passed.\n'
