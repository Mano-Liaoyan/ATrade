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

  if [[ -f "$file_path" ]] && grep -Fqi -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_terminal_stack_packages() {
  assert_file_contains "$frontend_root/package.json" '"tailwindcss"'
  assert_file_contains "$frontend_root/package.json" '"@tailwindcss/postcss"'
  assert_file_contains "$frontend_root/package.json" '"postcss"'
  assert_file_contains "$frontend_root/package.json" '"autoprefixer"'
  assert_file_contains "$frontend_root/package.json" '"@radix-ui/react-slot"'
  assert_file_contains "$frontend_root/package.json" '"@radix-ui/react-dialog"'
  assert_file_contains "$frontend_root/package.json" '"@radix-ui/react-popover"'
  assert_file_contains "$frontend_root/package.json" '"@radix-ui/react-scroll-area"'
  assert_file_contains "$frontend_root/package.json" '"@radix-ui/react-separator"'
  assert_file_contains "$frontend_root/package.json" '"@radix-ui/react-tabs"'
  assert_file_contains "$frontend_root/package.json" '"@radix-ui/react-tooltip"'
  assert_file_contains "$frontend_root/package.json" '"class-variance-authority"'
  assert_file_contains "$frontend_root/package.json" '"clsx"'
  assert_file_contains "$frontend_root/package.json" '"tailwind-merge"'
  assert_file_contains "$frontend_root/package.json" '"lucide-react"'

  assert_file_contains "$frontend_root/package-lock.json" '"node_modules/tailwindcss"'
  assert_file_contains "$frontend_root/package-lock.json" '"node_modules/@tailwindcss/postcss"'
  assert_file_contains "$frontend_root/package-lock.json" '"node_modules/@radix-ui/react-slot"'
  assert_file_contains "$frontend_root/package-lock.json" '"node_modules/class-variance-authority"'
}

assert_terminal_stack_configuration() {
  assert_file_contains "$frontend_root/tailwind.config.ts" 'content: ['
  assert_file_contains "$frontend_root/tailwind.config.ts" './app/**/*.{ts,tsx,mdx}'
  assert_file_contains "$frontend_root/tailwind.config.ts" './components/**/*.{ts,tsx,mdx}'
  assert_file_contains "$frontend_root/tailwind.config.ts" 'terminal: {'
  assert_file_contains "$frontend_root/tailwind.config.ts" 'status: {'
  assert_file_contains "$frontend_root/tailwind.config.ts" 'satisfies Config'

  assert_file_contains "$frontend_root/postcss.config.mjs" '"@tailwindcss/postcss"'
  assert_file_contains "$frontend_root/postcss.config.mjs" 'autoprefixer'

  assert_file_contains "$frontend_root/components.json" '"style": "new-york"'
  assert_file_contains "$frontend_root/components.json" '"components": "@/components"'
  assert_file_contains "$frontend_root/components.json" '"ui": "@/components/ui"'
  assert_file_contains "$frontend_root/components.json" '"utils": "@/lib/utils"'

  assert_file_contains "$frontend_root/tsconfig.json" '"baseUrl": "."'
  assert_file_contains "$frontend_root/tsconfig.json" '"@/*"'
  assert_file_contains "$frontend_root/lib/utils.ts" 'export function cn'
  assert_file_contains "$frontend_root/lib/utils.ts" 'clsx'
  assert_file_contains "$frontend_root/lib/utils.ts" 'twMerge'
}

assert_terminal_theme_tokens() {
  assert_file_contains "$frontend_root/app/globals.css" '@import "tailwindcss";'
  assert_file_contains "$frontend_root/app/globals.css" '--terminal-canvas'
  assert_file_contains "$frontend_root/app/globals.css" '--terminal-surface-elevated'
  assert_file_contains "$frontend_root/app/globals.css" '--terminal-splitter-active'
  assert_file_contains "$frontend_root/app/globals.css" '--terminal-table-row-selected'
  assert_file_contains "$frontend_root/app/globals.css" '--status-success-surface'
  assert_file_contains "$frontend_root/app/globals.css" '@media (prefers-reduced-motion: reduce)'
  assert_file_contains "$frontend_root/app/globals.css" '@media (forced-colors: active)'
}

assert_terminal_primitives() {
  for primitive in \
    ui/button.tsx \
    ui/input.tsx \
    ui/badge.tsx \
    ui/tabs.tsx \
    ui/dialog.tsx \
    ui/popover.tsx \
    ui/scroll-area.tsx \
    ui/separator.tsx \
    ui/tooltip.tsx \
    terminal/TerminalSurface.tsx \
    terminal/TerminalPanel.tsx \
    terminal/TerminalSectionHeader.tsx \
    terminal/TerminalStatusBadge.tsx; do
    if [[ ! -f "$frontend_root/components/$primitive" ]]; then
      printf 'expected primitive to exist: %s\n' "$frontend_root/components/$primitive" >&2
      return 1
    fi
  done

  assert_file_contains "$frontend_root/components/ui/button.tsx" '@/lib/utils'
  assert_file_contains "$frontend_root/components/ui/button.tsx" '@radix-ui/react-slot'
  assert_file_contains "$frontend_root/components/ui/button.tsx" 'buttonVariants'
  assert_file_contains "$frontend_root/components/ui/input.tsx" '@/lib/utils'
  assert_file_contains "$frontend_root/components/ui/badge.tsx" 'badgeVariants'
  assert_file_contains "$frontend_root/components/ui/tabs.tsx" '@radix-ui/react-tabs'
  assert_file_contains "$frontend_root/components/ui/dialog.tsx" '@radix-ui/react-dialog'
  assert_file_contains "$frontend_root/components/ui/popover.tsx" '@radix-ui/react-popover'
  assert_file_contains "$frontend_root/components/ui/scroll-area.tsx" '@radix-ui/react-scroll-area'
  assert_file_contains "$frontend_root/components/ui/separator.tsx" '@radix-ui/react-separator'
  assert_file_contains "$frontend_root/components/ui/tooltip.tsx" '@radix-ui/react-tooltip'
  assert_file_contains "$frontend_root/components/ui/index.ts" 'export * from "./button"'

  assert_file_contains "$frontend_root/components/terminal/TerminalSurface.tsx" 'data-terminal-surface'
  assert_file_contains "$frontend_root/components/terminal/TerminalPanel.tsx" 'data-terminal-panel'
  assert_file_contains "$frontend_root/components/terminal/TerminalPanel.tsx" 'bodyClassName'
  assert_file_contains "$frontend_root/components/terminal/TerminalSectionHeader.tsx" 'data-terminal-section-header'
  assert_file_contains "$frontend_root/components/terminal/TerminalStatusBadge.tsx" 'data-terminal-status-badge'
  assert_file_contains "$frontend_root/components/terminal/index.ts" 'export * from "./TerminalPanel"'

  if grep -RIn -E 'workspace-shell|terminal-workspace-shell|TradingWorkspace|<(SymbolSearch|Watchlist)([[:space:]>])|from ["'"'"'][^"'"'"']*/(SymbolSearch|Watchlist)["'"'"']' \
    "$frontend_root/components/ui" "$frontend_root/components/terminal"; then
    printf 'terminal primitives must not depend on legacy workspace rendering or shell classes.\n' >&2
    return 1
  fi
}

assert_clean_room_stack_sources() {
  assert_file_not_contains "$frontend_root/package.json" 'Fincept'
  assert_file_not_contains "$frontend_root/package.json" 'Bloomberg'
  assert_file_not_contains "$frontend_root/tailwind.config.ts" 'Fincept'
  assert_file_not_contains "$frontend_root/tailwind.config.ts" 'Bloomberg'
  assert_file_not_contains "$frontend_root/components.json" 'Fincept'
  assert_file_not_contains "$frontend_root/components.json" 'Bloomberg'

  if grep -RIn -E 'Fincept|Bloomberg|BLOOMBERG|bbg-terminal|bloomberg-terminal|BLP' \
    "$frontend_root/components/ui" "$frontend_root/components/terminal"; then
    printf 'terminal primitives must not reference copied/proprietary terminal brands or assets.\n' >&2
    return 1
  fi
}

main() {
  assert_terminal_stack_packages
  assert_terminal_stack_configuration
  assert_terminal_theme_tokens
  assert_terminal_primitives
  assert_clean_room_stack_sources
  (cd "$frontend_root" && npm ci --no-fund --no-audit >/dev/null && npm run build)
  printf 'ATrade Terminal UI stack validation passed.\n'
}

main "$@"
