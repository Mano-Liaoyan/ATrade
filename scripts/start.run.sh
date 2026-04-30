#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_path="$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj"

# shellcheck source=local-env.sh
. "$repo_root/scripts/local-env.sh"
atrade_load_local_port_contract "$repo_root"

aspire_dashboard_http_port="${ATRADE_ASPIRE_DASHBOARD_HTTP_PORT:-0}"
export ASPNETCORE_URLS="http://127.0.0.1:$aspire_dashboard_http_port"
export ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL="${ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL:-http://127.0.0.1:0}"
export ASPIRE_ALLOW_UNSECURED_TRANSPORT="${ASPIRE_ALLOW_UNSECURED_TRANSPORT:-true}"

if ! command -v dotnet >/dev/null 2>&1; then
  printf 'dotnet is required to run the ATrade AppHost.\n' >&2
  exit 1
fi

if [[ ! -f "$project_path" ]]; then
  printf 'Missing AppHost project at %s\n' "$project_path" >&2
  exit 1
fi

exec dotnet run --project "$project_path" --no-launch-profile -- "$@"
