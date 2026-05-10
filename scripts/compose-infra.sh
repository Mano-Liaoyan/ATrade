#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_root/compose.yaml"

# shellcheck source=local-env.sh
. "$repo_root/scripts/local-env.sh"
atrade_load_local_port_contract "$repo_root"

atrade_usage() {
  cat >&2 <<'USAGE'
Usage: scripts/compose-infra.sh <up|down|config|ps|logs|pull|restart> [compose args...]

Loads .env.template, overlays ignored .env, preserves process environment
values, selects Podman Compose by default with Docker Compose fallback, and runs
against the repo-owned compose.yaml. Set ATRADE_COMPOSE_DRY_RUN=true to print the
selected command without executing it.
USAGE
}

atrade_lower() {
  printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]'
}

atrade_is_truthy() {
  case "$(atrade_lower "${1:-}")" in
    1|true|yes|y|on) return 0 ;;
    *) return 1 ;;
  esac
}

atrade_has_real_ibkr_credentials() {
  [[ -n "${ATRADE_IBKR_USERNAME:-}" ]] || return 1
  [[ -n "${ATRADE_IBKR_PASSWORD:-}" ]] || return 1
  [[ "${ATRADE_IBKR_USERNAME:-}" != 'IBKR_USERNAME' ]] || return 1
  [[ "${ATRADE_IBKR_PASSWORD:-}" != 'IBKR_PASSWORD' ]] || return 1
  return 0
}

atrade_select_compose_command() {
  selected_compose_command=()

  if [[ -n "${ATRADE_COMPOSE_COMMAND:-}" ]]; then
    # Developer-controlled local override. Word-splitting is intentional so
    # values such as "docker compose" and "/path/to/wrapper --flag" work.
    # shellcheck disable=SC2206
    selected_compose_command=(${ATRADE_COMPOSE_COMMAND})
    return 0
  fi

  if command -v podman >/dev/null 2>&1; then
    selected_compose_command=(podman compose)
    return 0
  fi

  if command -v docker >/dev/null 2>&1; then
    selected_compose_command=(docker compose)
    return 0
  fi

  printf 'ATrade Compose infrastructure requires Podman Compose or Docker Compose. Install Podman or Docker, or set ATRADE_COMPOSE_COMMAND to an exact Compose command.\n' >&2
  return 1
}

atrade_print_tokens() {
  local token=''
  local first=true
  for token in "$@"; do
    if [[ "$first" == true ]]; then
      first=false
    else
      printf ' '
    fi
    printf '%s' "$token"
  done
  printf '\n'
}

if [[ ! -f "$compose_file" ]]; then
  printf 'Missing Compose file at %s\n' "$compose_file" >&2
  exit 1
fi

if [[ "$#" -lt 1 || "${1:-}" == '-h' || "${1:-}" == '--help' || "${1:-}" == 'help' ]]; then
  atrade_usage
  exit 1
fi

action="$1"
shift

selected_compose_command=()
atrade_select_compose_command

compose_project_name="${ATRADE_COMPOSE_PROJECT_NAME:-atrade}"
compose_args=(-f "$compose_file" --project-name "$compose_project_name")
profile_args=()
subcommand=()

if [[ "$action" == 'up' ]]; then
  if atrade_is_truthy "${ATRADE_BROKER_INTEGRATION_ENABLED:-false}" && atrade_has_real_ibkr_credentials; then
    profile_args+=(--profile ibkr)
  fi

  if [[ "$(atrade_lower "${ATRADE_ANALYSIS_ENGINE:-none}")" == 'lean' && "$(atrade_lower "${ATRADE_LEAN_RUNTIME_MODE:-cli}")" == 'docker' ]]; then
    profile_args+=(--profile lean)
  fi

  subcommand=(up -d)
else
  subcommand=("$action")
fi

command_parts=("${selected_compose_command[@]}" "${compose_args[@]}" "${profile_args[@]}" "${subcommand[@]}" "$@")

if atrade_is_truthy "${ATRADE_COMPOSE_DRY_RUN:-false}"; then
  atrade_print_tokens "${command_parts[@]}"
  exit 0
fi

exec "${command_parts[@]}"
