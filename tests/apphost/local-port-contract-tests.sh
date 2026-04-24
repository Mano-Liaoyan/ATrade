#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_backup=''
restore_original_env=0

temporary_api_port='5197'
temporary_frontend_direct_port='3117'
temporary_apphost_frontend_port='3017'

cleanup() {
  if [[ -n "$env_backup" && -f "$env_backup" ]]; then
    mv "$env_backup" "$repo_root/.env"
    env_backup=''
    restore_original_env=0
    return
  fi

  if [[ "$restore_original_env" == '0' ]]; then
    rm -f "$repo_root/.env"
  fi
}

trap cleanup EXIT

write_override_contract() {
  if [[ -f "$repo_root/.env" ]]; then
    env_backup="$(mktemp)"
    cp "$repo_root/.env" "$env_backup"
    restore_original_env=1
  fi

  cat >"$repo_root/.env" <<EOF
ATRADE_API_HTTP_PORT=$temporary_api_port
ATRADE_FRONTEND_DIRECT_HTTP_PORT=$temporary_frontend_direct_port
ATRADE_APPHOST_FRONTEND_HTTP_PORT=$temporary_apphost_frontend_port
EOF
}

main() {
  write_override_contract

  bash "$repo_root/tests/apphost/api-bootstrap-tests.sh"
  rm -rf /tmp/aspire-dcp*
  bash "$repo_root/tests/apphost/frontend-nextjs-bootstrap-tests.sh"
  bash "$repo_root/tests/apphost/apphost-infrastructure-manifest-tests.sh"
}

main "$@"
