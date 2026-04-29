#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if ! grep -R "PostgresWatchlist\|WatchlistRepository\|watchlists" "$repo_root/src" >/dev/null 2>&1; then
  printf 'SKIP: Postgres watchlist persistence slice is not present in this worktree yet.\n'
  exit 0
fi

printf 'Postgres watchlist persistence implementation detected, but no contract assertions are defined in this lane.\n' >&2
exit 1
