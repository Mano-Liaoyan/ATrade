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

assert_exact_count() {
  local description="$1"
  local expected="$2"
  local actual="$3"

  if [[ "$actual" != "$expected" ]]; then
    printf 'expected %s to be %s but was %s\n' "$description" "$expected" "$actual" >&2
    return 1
  fi
}

assert_one_global_indicator_in_top_right_workspace() {
  local layout="$frontend_root/components/terminal/TerminalWorkspaceLayout.tsx"
  local indicator="$frontend_root/components/terminal/TerminalWorkspaceStatusIndicator.tsx"
  local css="$frontend_root/app/globals.css"

  assert_file_contains "$layout" 'import { TerminalWorkspaceStatusIndicator } from "./TerminalWorkspaceStatusIndicator";'
  assert_exact_count \
    'global workspace SignalR indicator render count' \
    '1' \
    "$(grep -Fo '<TerminalWorkspaceStatusIndicator />' "$layout" | wc -l | tr -d '[:space:]')"
  assert_file_contains "$layout" 'className="terminal-workspace-layout__status"'
  assert_file_contains "$layout" 'aria-label="Global workspace status"'
  assert_file_contains "$indicator" 'data-testid="terminal-global-signalr-status"'
  assert_file_contains "$indicator" 'aria-live="polite"'
  assert_file_contains "$indicator" 'SignalR {projection.label}'
  assert_file_contains "$css" '.terminal-workspace-layout__status {'
  assert_file_contains "$css" 'justify-content: flex-end;'
}

assert_status_initializes_before_remote_checks() {
  local client="$frontend_root/lib/workspaceStatusClient.ts"
  local indicator="$frontend_root/components/terminal/TerminalWorkspaceStatusIndicator.tsx"

  assert_file_contains "$client" 'export function createInitialWorkspaceStatusState(): WorkspaceStatusState'
  assert_file_contains "$client" "signalRState: 'connecting'"
  assert_file_contains "$client" "httpReadState: 'unchecked'"
  assert_file_contains "$client" 'readLocalWorkspaceCacheState()'
  assert_file_contains "$indicator" 'useState<WorkspaceStatusState>(() => createInitialWorkspaceStatusState())'
}

assert_status_projection_covers_required_states() {
  local client="$frontend_root/lib/workspaceStatusClient.ts"
  local required_states=(
    "id: 'connected'"
    "id: 'connecting'"
    "id: 'fallback'"
    "id: 'disconnected'"
    "id: 'cache-read-degraded'"
    "id: 'unavailable'"
    'HTTP read fallback active'
    'Cache/read degraded'
  )

  local state
  for state in "${required_states[@]}"; do
    assert_file_contains "$client" "$state"
  done

  assert_file_contains "$client" "signalRState === 'unavailable' && state.httpReadState === 'healthy'"
  assert_file_contains "$frontend_root/components/terminal/TerminalWorkspaceStatusIndicator.tsx" "const httpReadState = await checkWorkspaceHttpReadState();"
}

assert_duplicate_global_signalr_copy_removed() {
  local component_files
  mapfile -t component_files < <(find "$frontend_root/components/terminal" -type f -name '*.tsx' ! -name 'TerminalWorkspaceStatusIndicator.tsx' | sort)

  if grep -RInF -- 'SignalR' "${component_files[@]}"; then
    printf 'expected visible SignalR copy to live only in the global workspace status indicator.\n' >&2
    return 1
  fi

  assert_file_not_contains "$frontend_root/lib/terminalChartWorkspaceWorkflow.ts" 'streamLabel: `SignalR ${streamState}`'
  assert_file_not_contains "$frontend_root/lib/terminalChartWorkspaceWorkflow.ts" 'SignalR applies market-data updates'
  assert_file_contains "$frontend_root/components/terminal/TerminalBacktestWorkspace.tsx" 'Run stream {workflow.streamState}'
}

main() {
  assert_one_global_indicator_in_top_right_workspace
  assert_status_initializes_before_remote_checks
  assert_status_projection_covers_required_states
  assert_duplicate_global_signalr_copy_removed

  printf 'Frontend global SignalR/status validation passed.\n'
}

main "$@"
