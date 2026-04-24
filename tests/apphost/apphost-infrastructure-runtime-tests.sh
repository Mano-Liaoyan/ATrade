#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
apphost_pid=''
apphost_log=''
declare -a created_container_ids=()

docker_label_filter='label=com.microsoft.developer.usvc-dev.group-version=usvc-dev.developer.microsoft.com/v1'

cleanup() {
  if [[ -n "$apphost_pid" ]] && kill -0 "$apphost_pid" 2>/dev/null; then
    kill "$apphost_pid" 2>/dev/null || true
    wait "$apphost_pid" 2>/dev/null || true
  fi

  if [[ ${#created_container_ids[@]} -gt 0 ]]; then
    docker rm -f "${created_container_ids[@]}" >/dev/null 2>&1 || true
  fi

  if [[ -n "$apphost_log" && -f "$apphost_log" ]]; then
    rm -f "$apphost_log"
  fi
}

trap cleanup EXIT

require_container_engine() {
  if ! command -v docker >/dev/null 2>&1; then
    printf 'SKIP: docker CLI is not available; skipping AppHost runtime infrastructure verification.\n'
    exit 0
  fi

  if ! docker version >/dev/null 2>&1; then
    printf 'SKIP: no healthy Docker-compatible engine is available; skipping AppHost runtime infrastructure verification.\n'
    exit 0
  fi
}

print_debug_state() {
  if [[ -n "$apphost_log" && -f "$apphost_log" ]]; then
    printf '\n=== AppHost log tail ===\n' >&2
    tail -n 120 "$apphost_log" >&2 || true
  fi

  if [[ ${#created_container_ids[@]} -gt 0 ]]; then
    printf '\n=== Created container state ===\n' >&2
    for id in "${created_container_ids[@]}"; do
      docker inspect "$id" --format '{{.Name}} {{.Config.Image}} PidsLimit={{.HostConfig.PidsLimit}} Status={{.State.Status}} ExitCode={{.State.ExitCode}}' >&2 || true
      printf -- '--- logs for %s ---\n' "$id" >&2
      docker logs "$id" 2>&1 | tail -n 60 >&2 || true
    done
  fi
}

fail_with_debug() {
  printf '%s\n' "$1" >&2
  print_debug_state
  exit 1
}

start_apphost() {
  apphost_log="$(mktemp)"
  (
    cd "$repo_root"
    ./start run >"$apphost_log" 2>&1
  ) &
  apphost_pid=$!
}

wait_for_new_infra_containers() {
  local before_ids
  local current_ids
  local new_ids

  before_ids="$(docker ps -aq --filter "$docker_label_filter" | sort || true)"
  start_apphost

  for _ in $(seq 1 60); do
    sleep 1

    if ! kill -0 "$apphost_pid" 2>/dev/null; then
      fail_with_debug 'AppHost exited before the runtime verification observed new infra containers.'
    fi

    current_ids="$(docker ps -aq --filter "$docker_label_filter" | sort || true)"
    new_ids="$(comm -13 <(printf '%s\n' "$before_ids") <(printf '%s\n' "$current_ids") | sed '/^$/d' || true)"

    if [[ -n "$new_ids" ]]; then
      mapfile -t created_container_ids < <(printf '%s\n' "$new_ids")
      if [[ ${#created_container_ids[@]} -ge 4 ]]; then
        return 0
      fi
    fi
  done

  fail_with_debug 'Timed out waiting for AppHost-managed infra containers to be created.'
}

find_created_container_by_image() {
  local image="$1"
  local id

  for id in "${created_container_ids[@]}"; do
    if [[ "$(docker inspect "$id" --format '{{.Config.Image}}')" == "$image" ]]; then
      printf '%s\n' "$id"
      return 0
    fi
  done

  return 1
}

wait_for_container_running() {
  local id="$1"
  local resource_name="$2"
  local status=''

  for _ in $(seq 1 60); do
    status="$(docker inspect "$id" --format '{{.State.Status}}' 2>/dev/null || true)"
    if [[ "$status" == 'running' ]]; then
      return 0
    fi

    if [[ "$status" == 'exited' || "$status" == 'dead' ]]; then
      fail_with_debug "$resource_name exited before it reached a stable running state."
    fi

    if ! kill -0 "$apphost_pid" 2>/dev/null; then
      fail_with_debug "AppHost exited while waiting for $resource_name to start."
    fi

    sleep 1
  done

  fail_with_debug "Timed out waiting for $resource_name to reach a running state."
}

assert_effective_pids_limit_gt_one() {
  local id="$1"
  local resource_name="$2"
  local configured_pids_limit
  local container_pid
  local effective_pids_max

  wait_for_container_running "$id" "$resource_name"

  configured_pids_limit="$(docker inspect "$id" --format '{{.HostConfig.PidsLimit}}')"
  if [[ ! "$configured_pids_limit" =~ ^[0-9]+$ ]] || (( configured_pids_limit <= 1 )); then
    fail_with_debug "$resource_name was expected to have a real HostConfig.PidsLimit, got '$configured_pids_limit'."
  fi

  container_pid="$(docker inspect "$id" --format '{{.State.Pid}}')"
  if [[ ! "$container_pid" =~ ^[0-9]+$ ]] || (( container_pid <= 0 )); then
    fail_with_debug "$resource_name did not expose a running container PID."
  fi

  if [[ ! -r "/proc/$container_pid/root/sys/fs/cgroup/pids.max" ]]; then
    fail_with_debug "$resource_name did not expose /proc/$container_pid/root/sys/fs/cgroup/pids.max for runtime verification."
  fi

  effective_pids_max="$(cat "/proc/$container_pid/root/sys/fs/cgroup/pids.max")"
  if [[ "$effective_pids_max" == 'max' ]]; then
    return 0
  fi

  if [[ ! "$effective_pids_max" =~ ^[0-9]+$ ]] || (( effective_pids_max <= 1 )); then
    fail_with_debug "$resource_name was expected to have an effective pids.max > 1, got '$effective_pids_max'."
  fi
}

wait_for_container_logs_contain() {
  local id="$1"
  local needle="$2"
  local resource_name="$3"
  local logs

  for _ in $(seq 1 60); do
    logs="$(docker logs "$id" 2>&1 || true)"
    if [[ "$logs" == *"$needle"* ]]; then
      return 0
    fi

    if ! kill -0 "$apphost_pid" 2>/dev/null; then
      fail_with_debug "AppHost exited while waiting for $resource_name logs to contain: $needle"
    fi

    sleep 1
  done

  fail_with_debug "$resource_name logs did not contain expected marker: $needle"
}

assert_container_logs_do_not_contain() {
  local id="$1"
  local needle="$2"
  local resource_name="$3"
  local logs

  logs="$(docker logs "$id" 2>&1 || true)"
  if [[ "$logs" == *"$needle"* ]]; then
    fail_with_debug "$resource_name logs unexpectedly contained failure marker: $needle"
  fi
}

main() {
  require_container_engine
  wait_for_new_infra_containers

  local postgres_id
  local timescaledb_id
  local redis_id
  local nats_id

  postgres_id="$(find_created_container_by_image 'docker.io/library/postgres:17.6')"
  timescaledb_id="$(find_created_container_by_image 'docker.io/timescale/timescaledb:latest-pg17')"
  redis_id="$(find_created_container_by_image 'docker.io/library/redis:8.6')"
  nats_id="$(find_created_container_by_image 'docker.io/library/nats:2.12')"

  assert_effective_pids_limit_gt_one "$postgres_id" 'postgres'
  assert_effective_pids_limit_gt_one "$timescaledb_id" 'timescaledb'
  assert_effective_pids_limit_gt_one "$redis_id" 'redis'
  assert_effective_pids_limit_gt_one "$nats_id" 'nats'

  wait_for_container_logs_contain "$postgres_id" 'database system is ready to accept connections' 'postgres'
  wait_for_container_logs_contain "$timescaledb_id" 'database system is ready to accept connections' 'timescaledb'
  assert_container_logs_do_not_contain "$postgres_id" 'Cannot fork' 'postgres'
  assert_container_logs_do_not_contain "$timescaledb_id" 'Cannot fork' 'timescaledb'
  assert_container_logs_do_not_contain "$timescaledb_id" "can't open '/sys/fs/cgroup/memory.max'" 'timescaledb'
  assert_container_logs_do_not_contain "$timescaledb_id" 'panic: bytes must be at least 1 byte' 'timescaledb'
}

main "$@"
