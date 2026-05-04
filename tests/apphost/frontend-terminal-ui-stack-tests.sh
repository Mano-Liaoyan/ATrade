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

assert_clean_room_stack_sources() {
  assert_file_not_contains "$frontend_root/package.json" 'Fincept'
  assert_file_not_contains "$frontend_root/package.json" 'Bloomberg'
  assert_file_not_contains "$frontend_root/tailwind.config.ts" 'Fincept'
  assert_file_not_contains "$frontend_root/tailwind.config.ts" 'Bloomberg'
  assert_file_not_contains "$frontend_root/components.json" 'Fincept'
  assert_file_not_contains "$frontend_root/components.json" 'Bloomberg'
}

main() {
  assert_terminal_stack_packages
  assert_terminal_stack_configuration
  assert_clean_room_stack_sources
  (cd "$frontend_root" && npm ci --no-fund --no-audit >/dev/null && npm run build)
  printf 'ATrade Terminal UI stack validation passed.\n'
}

main "$@"
