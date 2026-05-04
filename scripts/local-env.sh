#!/usr/bin/env bash

atrade_load_local_port_contract() {
  local repo_root="${1:?repo root is required}"
  local preferred_path="$repo_root/.env"
  local fallback_path="$repo_root/.env.template"
  local contract_path="$fallback_path"
  local raw_line=''
  local key=''
  local value=''
  local contract_file=''
  local key_index=-1
  local i=0
  local -a contract_files=()
  local -a contract_keys=()
  local -a contract_values=()

  if [[ -f "$preferred_path" ]]; then
    contract_path="$preferred_path"
  fi

  if [[ -f "$fallback_path" ]]; then
    contract_files+=("$fallback_path")
  fi

  if [[ -f "$preferred_path" ]]; then
    contract_files+=("$preferred_path")
  fi

  if [[ "${#contract_files[@]}" -eq 0 ]]; then
    printf 'Missing local port contract file at %s
' "$fallback_path" >&2
    return 1
  fi

  export ATRADE_REPO_ROOT="$repo_root"
  export ATRADE_PORT_CONTRACT_PATH="$contract_path"

  for contract_file in "${contract_files[@]}"; do
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

      if [[ -z "$key" || "$raw_line" != *'='* ]]; then
        continue
      fi

      key_index=-1
      for ((i = 0; i < ${#contract_keys[@]}; i++)); do
        if [[ "${contract_keys[$i]}" == "$key" ]]; then
          key_index="$i"
          break
        fi
      done

      if [[ "$key_index" -ge 0 ]]; then
        contract_values[$key_index]="$value"
      else
        contract_keys+=("$key")
        contract_values+=("$value")
      fi
    done <"$contract_file"
  done

  for ((i = 0; i < ${#contract_keys[@]}; i++)); do
    key="${contract_keys[$i]}"
    if [[ -z "${!key+x}" ]]; then
      export "$key=${contract_values[$i]}"
    fi
  done
}
