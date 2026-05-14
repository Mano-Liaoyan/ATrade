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

  node - "$css_file" "$selector" "$needle" <<'NODE'
const { readFileSync } = require('node:fs');

const [, , cssPath, selector, needle] = process.argv;
const css = readFileSync(cssPath, 'utf8');
const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const matches = [...css.matchAll(new RegExp(`${escapedSelector}\\s*\\{(?<body>[^}]*)\\}`, 'gm'))];
if (matches.length === 0) {
  console.error(`expected CSS selector ${JSON.stringify(selector)} to exist in ${cssPath}`);
  process.exit(1);
}
if (!matches.some((match) => match.groups.body.includes(needle))) {
  console.error(`expected CSS selector ${JSON.stringify(selector)} to contain ${JSON.stringify(needle)}`);
  process.exit(1);
}
NODE
}

assert_icon_mapping() {
  local registry="$frontend_root/lib/terminalModuleRegistry.ts"
  local types="$frontend_root/types/terminal.ts"
  local rail="$frontend_root/components/terminal/TerminalModuleRail.tsx"

  node - "$registry" <<'NODE'
const { readFileSync } = require('node:fs');

const registry = readFileSync(process.argv[2], 'utf8');
const expected = {
  HOME: 'home',
  SEARCH: 'search',
  WATCHLIST: 'bookmark',
  CHART: 'chart-candlestick',
  ANALYSIS: 'flask-conical',
  STATUS: 'activity',
  HELP: 'circle-question',
  NEWS: 'newspaper',
  PORTFOLIO: 'briefcase-business',
  RESEARCH: 'file-search',
  SCREENER: 'sliders-horizontal',
  ECON: 'landmark',
  AI: 'bot',
  NODE: 'workflow',
  ORDERS: 'ban',
};
for (const [moduleId, iconId] of Object.entries(expected)) {
  const marker = `id: "${moduleId}"`;
  if (!registry.includes(marker)) {
    console.error(`missing module definition for ${moduleId}`);
    process.exit(1);
  }
  const block = registry.slice(registry.indexOf(marker), registry.indexOf(marker) + 900);
  if (!block.includes(`icon: "${iconId}"`)) {
    console.error(`expected ${moduleId} to map to icon ${iconId}`);
    process.exit(1);
  }
  for (const preserved of ['label:', 'shortLabel:', 'description:', 'availability:', 'placement:']) {
    if (!block.includes(preserved)) {
      console.error(`expected ${moduleId} definition to preserve ${preserved}`);
      process.exit(1);
    }
  }
}
console.log('module icon registry mapping verified');
NODE

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
  assert_file_contains "$rail" 'terminal-module-rail__item--selected-disabled'
  assert_file_contains "$rail" 'className="terminal-module-rail__navigation terminal-scroll-owned terminal-rail-scroll-owned"'
  assert_file_contains "$rail" 'data-scroll-owner="module-rail"'

  assert_css_rule_contains '.atrade-terminal-app__body' 'grid-template-columns: auto minmax(0, 1fr);'
  assert_css_rule_contains '.terminal-module-rail' 'inline-size: min(11rem, 24vw);'
  assert_css_rule_contains '.terminal-module-rail' 'grid-template-rows: auto minmax(0, 1fr);'
  assert_css_rule_contains '.terminal-module-rail' 'max-block-size: 100%;'
  assert_css_rule_contains '.terminal-module-rail' 'overflow: hidden;'
  assert_css_rule_contains '.terminal-module-rail__navigation' 'overflow: auto;'
  assert_css_rule_contains '.terminal-scroll-owned' 'scrollbar-width: thin;'
  assert_file_contains "$css" '.terminal-scroll-owned::-webkit-scrollbar-thumb'
  assert_css_rule_contains '.terminal-module-rail' '--terminal-rail-collapsed-target: 2.75rem;'
  assert_css_rule_contains '.terminal-module-rail' '--terminal-rail-scrollbar-reserve: 0.85rem;'
  assert_css_rule_contains '.terminal-module-rail--collapsed' 'inline-size: var(--terminal-rail-collapsed-inline-size);'
  assert_css_rule_contains '.terminal-module-rail--collapsed' 'min-inline-size: var(--terminal-rail-collapsed-inline-size);'
  assert_css_rule_contains '.terminal-module-rail--collapsed .terminal-module-rail__navigation' 'justify-items: center;'
  assert_css_rule_contains '.terminal-module-rail--collapsed .terminal-module-rail__navigation' 'overflow-y: auto;'
  assert_css_rule_contains '.terminal-module-rail--collapsed .terminal-module-rail__item' 'inline-size: var(--terminal-rail-collapsed-target);'
  assert_css_rule_contains '.terminal-module-rail--collapsed .terminal-module-rail__item' 'min-block-size: var(--terminal-rail-collapsed-target);'
  assert_css_rule_contains '.terminal-module-rail--collapsed .terminal-module-rail__item' 'place-items: center;'
  assert_css_rule_contains '.terminal-module-rail--collapsed .terminal-module-rail__short' 'inline-size: 2rem;'
  assert_css_rule_contains '.terminal-module-rail--collapsed .terminal-module-rail__toggle' 'inline-size: var(--terminal-rail-collapsed-target);'
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
