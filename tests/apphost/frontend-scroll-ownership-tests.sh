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

assert_css_rule_contains() {
  local selector="$1"
  local needle="$2"
  local css_file="$frontend_root/app/globals.css"

  SELECTOR="$selector" NEEDLE="$needle" perl -0ne '
    my $selector = $ENV{"SELECTOR"};
    my $needle = $ENV{"NEEDLE"};
    my $quoted = quotemeta($selector);
    my @matches = /$quoted\s*\{([^{}]*)\}/g;
    if (!@matches) {
      print STDERR "expected CSS selector [$selector] to exist in $ARGV\n";
      exit 1;
    }
    for my $body (@matches) {
      if (index($body, $needle) >= 0) {
        exit 0;
      }
    }
    print STDERR "expected CSS selector [$selector] to contain [$needle]\n";
    exit 1;
  ' "$css_file"
}

assert_shared_wheel_scroll_ownership_contract() {
  local app="$frontend_root/components/terminal/ATradeTerminalApp.tsx"
  local ownership="$frontend_root/lib/terminalWheelScrollOwnership.ts"
  local css="$frontend_root/app/globals.css"

  assert_file_contains "$app" 'attachTerminalWheelScrollOwnership'
  assert_file_contains "$app" 'terminalFrameRef'
  assert_file_contains "$app" 'ref={terminalFrameRef}'

  assert_file_contains "$ownership" 'root.addEventListener("wheel", handleWheel, { passive: false })'
  assert_file_contains "$ownership" 'event.defaultPrevented'
  assert_file_contains "$ownership" 'event.preventDefault()'
  assert_file_contains "$ownership" 'event.deltaMode === WheelEvent.DOM_DELTA_LINE'
  assert_file_contains "$ownership" 'event.deltaMode === WheelEvent.DOM_DELTA_PAGE'
  assert_file_contains "$ownership" 'event.shiftKey && deltaX === 0'
  assert_file_contains "$ownership" 'data-slot="scroll-area-viewport"'
  assert_file_contains "$ownership" 'data-scroll-owner'
  assert_file_contains "$ownership" 'terminal-workspace-scroll-owned'
  assert_file_contains "$ownership" 'remainingDeltaY -= movedY'
  assert_file_contains "$ownership" 'remainingDeltaX -= movedX'

  assert_css_rule_contains '.terminal-scroll-owned' 'overscroll-behavior: auto;'
  assert_file_contains "$css" '.terminal-scroll-owned::-webkit-scrollbar'
  assert_file_contains "$css" 'scrollbar-color: hsl(var(--terminal-accent-amber) / 0.74)'
}

assert_scroll_region_inventory_remains_owned() {
  assert_file_contains "$frontend_root/components/terminal/TerminalModuleRail.tsx" 'data-scroll-owner="module-rail"'
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx" 'data-scroll-owner="primary-workspace"'
  assert_file_contains "$frontend_root/components/terminal/MarketMonitorTable.tsx" 'data-scroll-owner="market-monitor-table"'
  assert_file_contains "$frontend_root/components/terminal/MarketMonitorDetailPanel.tsx" 'data-scroll-owner="market-monitor-detail"'
  assert_file_contains "$frontend_root/components/terminal/TerminalChartWorkspace.tsx" 'data-scroll-owner="chart-workspace-region"'
  assert_file_contains "$frontend_root/components/terminal/TerminalAnalysisWorkspace.tsx" 'data-scroll-owner="analysis-module"'
  assert_file_contains "$frontend_root/components/terminal/TerminalBacktestWorkspace.tsx" 'data-scroll-owner="backtest-module"'
  assert_file_contains "$frontend_root/components/terminal/TerminalStatusModule.tsx" 'data-scroll-owner="status-module"'
  assert_file_contains "$frontend_root/components/terminal/TerminalHelpModule.tsx" 'data-scroll-owner="help-module"'
  assert_file_contains "$frontend_root/components/terminal/TerminalDisabledModule.tsx" 'data-scroll-owner="disabled-module"'
}

assert_validation_is_static_and_provider_independent() {
  local script="$repo_root/tests/apphost/frontend-scroll-ownership-tests.sh"

  assert_file_contains "$script" 'assert_shared_wheel_scroll_ownership_contract'
  if grep -Fq -- "cu""rl " "$script"; then
    printf 'expected %s not to call curl\n' "$script" >&2
    return 1
  fi
  if grep -Fq -- "npm run"" dev" "$script"; then
    printf 'expected %s not to start dev server\n' "$script" >&2
    return 1
  fi
}

main() {
  assert_shared_wheel_scroll_ownership_contract
  assert_scroll_region_inventory_remains_owned
  assert_validation_is_static_and_provider_independent

  printf 'Frontend shared wheel scroll ownership validation passed.\n'
}

main "$@"
