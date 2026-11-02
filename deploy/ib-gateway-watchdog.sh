#!/usr/bin/env bash
# The health check of the ib-gateway service (docs/architecture/ibkr.md section 7.4).
#
# IB Gateway can stay logged out after a failed login ("Unrecognized Username or Password"), and IBC does not try
# again. This script finds 2 such states:
#   1. The paper API port does not listen (the login at the start failed).
#   2. The Web process reports "no_ibkr_connection": the API port listens, but IB Gateway has no connection to IBKR.
# When a state stays for the restart wait, the script stops the container (SIGTERM to run.sh, which is PID 1).
# The restart policy of the service then starts it again, with a new login. The restart wait doubles after each
# restart without a recovery, so a long IBKR outage does not cause a login each 10 minutes.
set -u

# The paper API port of IB Gateway inside the container. socat forwards 4004 to it.
readonly API_PORT=4002
readonly WEB_STATUS_ADDRESS=/dev/tcp/web/8000
readonly FIRST_RESTART_WAIT_SECONDS=600
readonly LAST_RESTART_WAIT_SECONDS=7200
# The container file system stays after a restart of the container, so these files count across restarts.
readonly PROBLEM_SINCE_FILE=/tmp/atrade-watchdog-problem-since
readonly RESTART_COUNT_FILE=/tmp/atrade-watchdog-restart-count

api_port_listens() {
  local hex_port
  hex_port=$(printf '%04X' "$API_PORT")
  # Columns: local address, remote address, state. 0A is LISTEN.
  grep -qE ":${hex_port} [0-9A-F]+:0000 0A" /proc/net/tcp /proc/net/tcp6 2>/dev/null
}

web_reports_no_ibkr_connection() {
  local status_response
  # The Web process can be stopped. Then the script knows nothing about the IBKR link, and that is no problem.
  status_response=$(timeout 5 bash -c "exec 3<>${WEB_STATUS_ADDRESS} \
    && printf 'GET /api/ibkr/gateway HTTP/1.0\r\nHost: web\r\n\r\n' >&3 && cat <&3" 2>/dev/null) || return 1
  [[ $status_response == *'"no_ibkr_connection"'* ]]
}

log_to_container() {
  # The output of a health check goes to `docker inspect` only. PID 1 writes to the container log.
  echo "ATrade watchdog: $1" >/proc/1/fd/1 2>/dev/null || true
}

problem=""
if ! api_port_listens; then
  problem="the IB Gateway API port ${API_PORT} does not listen"
elif web_reports_no_ibkr_connection; then
  problem="the Web process reports that IB Gateway has no connection to IBKR"
fi

if [[ -z $problem ]]; then
  if [[ -f $RESTART_COUNT_FILE ]]; then
    log_to_container "IB Gateway is healthy again."
  fi
  rm -f "$PROBLEM_SINCE_FILE" "$RESTART_COUNT_FILE"
  exit 0
fi

now=$(date +%s)
[[ -f $PROBLEM_SINCE_FILE ]] || echo "$now" >"$PROBLEM_SINCE_FILE"
problem_since=$(<"$PROBLEM_SINCE_FILE")
restart_count=0
[[ -f $RESTART_COUNT_FILE ]] && restart_count=$(<"$RESTART_COUNT_FILE")
restart_wait=$((FIRST_RESTART_WAIT_SECONDS << restart_count))
if ((restart_wait > LAST_RESTART_WAIT_SECONDS || restart_wait <= 0)); then
  restart_wait=$LAST_RESTART_WAIT_SECONDS
fi

problem_seconds=$((now - problem_since))
if ((problem_seconds >= restart_wait)); then
  # The next check after the restart counts the problem time again from zero.
  rm -f "$PROBLEM_SINCE_FILE"
  echo $((restart_count + 1)) >"$RESTART_COUNT_FILE"
  log_to_container "${problem} for ${problem_seconds} seconds. Restarting IB Gateway."
  kill -TERM 1
fi
echo "${problem} for ${problem_seconds} seconds. Restart after ${restart_wait} seconds."
exit 1
