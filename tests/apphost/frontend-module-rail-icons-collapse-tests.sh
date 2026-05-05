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

assert_no_grep_matches() {
  local description="$1"
  local pattern="$2"
  shift 2

  if grep -RInE --exclude-dir=.next --exclude-dir=node_modules --exclude='package-lock.json' "$pattern" "$@"; then
    printf 'unexpected %s found.\n' "$description" >&2
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

assert_icon_mapping() {
  local registry="$frontend_root/lib/terminalModuleRegistry.ts"
  local types="$frontend_root/types/terminal.ts"
  local rail="$frontend_root/components/terminal/TerminalModuleRail.tsx"

  python3 - "$registry" <<'PY'
import sys
from pathlib import Path

registry = Path(sys.argv[1]).read_text(encoding='utf-8')
expected = {
    'HOME': 'home',
    'SEARCH': 'search',
    'WATCHLIST': 'bookmark',
    'CHART': 'chart-candlestick',
    'ANALYSIS': 'flask-conical',
    'STATUS': 'activity',
    'HELP': 'circle-question',
    'NEWS': 'newspaper',
    'PORTFOLIO': 'briefcase-business',
    'RESEARCH': 'file-search',
    'SCREENER': 'sliders-horizontal',
    'ECON': 'landmark',
    'AI': 'bot',
    'NODE': 'workflow',
    'ORDERS': 'ban',
}
for module_id, icon_id in expected.items():
    marker = f'id: "{module_id}"'
    if marker not in registry:
        print(f'missing module definition for {module_id}', file=sys.stderr)
        sys.exit(1)
    block = registry[registry.index(marker):registry.index(marker) + 900]
    if f'icon: "{icon_id}"' not in block:
        print(f'expected {module_id} to map to icon {icon_id}', file=sys.stderr)
        sys.exit(1)
    for preserved in ['label:', 'shortLabel:', 'description:', 'availability:', 'placement:']:
        if preserved not in block:
            print(f'expected {module_id} definition to preserve {preserved}', file=sys.stderr)
            sys.exit(1)
print('module icon registry mapping verified')
PY

  assert_file_contains "$types" 'export type TerminalModuleIconId ='
  assert_file_contains "$types" 'icon: TerminalModuleIconId;'
  assert_file_contains "$rail" 'from "lucide-react"'
  assert_file_contains "$rail" 'const TERMINAL_MODULE_ICON_COMPONENTS: Record<TerminalModuleIconId, LucideIcon>'
  assert_file_contains "$rail" 'data-module-icon={module.icon}'
  assert_file_contains "$rail" 'data-module-short-label={module.shortLabel}'
  assert_file_contains "$rail" 'className="terminal-module-rail__short terminal-module-rail__icon" aria-hidden="true"'
  assert_file_contains "$rail" '<span className="terminal-module-rail__label">{module.label}</span>'
}

assert_collapse_contract() {
  local rail="$frontend_root/components/terminal/TerminalModuleRail.tsx"
  local css="$frontend_root/app/globals.css"

  assert_file_contains "$rail" 'const [isCollapsed, setIsCollapsed] = useState(false);'
  assert_file_contains "$rail" 'className={cn("terminal-module-rail", isCollapsed && "terminal-module-rail--collapsed")}'
  assert_file_contains "$rail" 'data-collapsed={isCollapsed ? "true" : "false"}'
  assert_file_contains "$rail" 'data-rail-state={isCollapsed ? "collapsed" : "expanded"}'
  assert_file_contains "$rail" 'className="terminal-module-rail__toggle"'
  assert_file_contains "$rail" 'aria-expanded={!isCollapsed}'
  assert_file_contains "$rail" 'aria-label={isCollapsed ? "Expand module rail" : "Collapse module rail"}'
  assert_file_contains "$rail" 'title={isCollapsed ? "Expand module rail" : "Collapse module rail"}'
  assert_file_contains "$rail" 'onClick={() => setIsCollapsed((current) => !current)}'
  assert_file_contains "$rail" 'title={isCollapsed ? module.label : undefined}'
  assert_file_contains "$rail" 'aria-current={activeModuleId === module.id && !disabledModuleId ? "page" : undefined}'
  assert_file_contains "$rail" 'aria-disabled="true"'
  assert_file_contains "$rail" 'tabIndex={-1}'
  assert_file_contains "$rail" 'terminal-module-rail__item--selected-disabled'

  assert_css_rule_contains '.atrade-terminal-app__body' 'grid-template-columns: auto minmax(0, 1fr);'
  assert_css_rule_contains '.terminal-module-rail' 'inline-size: min(11rem, 24vw);'
  assert_css_rule_contains '.terminal-module-rail--collapsed' 'inline-size: 4.35rem;'
  assert_css_rule_contains '.terminal-module-rail--collapsed' 'min-inline-size: 4.35rem;'
  assert_file_contains "$css" '.terminal-module-rail--collapsed .terminal-module-rail__label,'
  assert_file_contains "$css" '.terminal-module-rail--collapsed .terminal-module-rail__toggle-label'
  assert_file_contains "$css" 'clip: rect(0, 0, 0, 0);'
  assert_file_not_contains "$css" '.terminal-module-rail--collapsed .terminal-module-rail__label { display: none; }'
}

assert_no_retired_surfaces() {
  assert_no_grep_matches \
    'command input, layout persistence, top app chrome, safety strip, unsafe rail persistence, or positive order-entry affordance in active rail/workspace frame source' \
    'TerminalCommandInput|terminalCommandRegistry|handleCommand|commandFeedback|terminal-safety-strip|TerminalStatusStrip|terminalLayoutPersistence|localStorage|Paper Trading Workspace|ATrade Terminal Shell|OrderTicket|PlaceOrder|placeOrder|submitOrder|buy-button|sell-button' \
    "$frontend_root/app" \
    "$frontend_root/components/terminal/ATradeTerminalApp.tsx" \
    "$frontend_root/components/terminal/TerminalModuleRail.tsx" \
    "$frontend_root/app/globals.css"
}

main() {
  assert_icon_mapping
  assert_collapse_contract
  assert_no_retired_surfaces

  printf 'Module rail icon and collapse validation passed.\n'
}

main "$@"
