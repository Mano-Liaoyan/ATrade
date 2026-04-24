#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_path="$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj"

# shellcheck source=local-env.sh
. "$repo_root/scripts/local-env.sh"
atrade_load_local_port_contract "$repo_root"

if ! command -v dotnet >/dev/null 2>&1; then
  printf 'dotnet is required to run the ATrade AppHost.\n' >&2
  exit 1
fi

if [[ ! -f "$project_path" ]]; then
  printf 'Missing AppHost project at %s\n' "$project_path" >&2
  exit 1
fi

exec dotnet run --project "$project_path" -- "$@"
