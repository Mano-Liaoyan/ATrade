#!/usr/bin/env bash

atrade_load_local_port_contract() {
  local repo_root="${1:?repo root is required}"
  local preferred_path="$repo_root/.env"
  local fallback_path="$repo_root/.env.example"
  local contract_path="$fallback_path"
  local raw_line=''
  local key=''
  local value=''

  if [[ -f "$preferred_path" ]]; then
    contract_path="$preferred_path"
  fi

  if [[ ! -f "$contract_path" ]]; then
    printf 'Missing local port contract file at %s\n' "$contract_path" >&2
    return 1
  fi

  export ATRADE_REPO_ROOT="$repo_root"
  export ATRADE_PORT_CONTRACT_PATH="$contract_path"

  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    if [[ "$raw_line" =~ ^[[:space:]]*$ || "$raw_line" =~ ^[[:space:]]*# ]]; then
      continue
    fi

    key="${raw_line%%=*}"
    value="${raw_line#*=}"
    key="${key//[$'\t\r ']/}"
    value="${value%$'\r'}"
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    if [[ -z "$key" ]]; then
      continue
    fi

    if [[ -z "${!key+x}" ]]; then
      export "$key=$value"
    fi
  done <"$contract_path"
}
