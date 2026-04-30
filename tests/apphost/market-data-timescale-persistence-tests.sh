#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="timescale/timescaledb:latest-pg17"
CONTAINER_NAME="atrade-timescale-market-data-test-$RANDOM-$$"
DB_USER="atrade"
DB_PASSWORD="atrade"
DB_NAME="atrade"
RUNTIME=""

if command -v docker >/dev/null 2>&1; then
  RUNTIME="docker"
elif command -v podman >/dev/null 2>&1; then
  RUNTIME="podman"
else
  echo "SKIP: Docker/Podman-compatible container runtime is not available."
  exit 0
fi

if ! "$RUNTIME" info >/dev/null 2>&1; then
  echo "SKIP: $RUNTIME is installed but not reachable in this environment."
  exit 0
fi

choose_port() {
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(("127.0.0.1", 0))
    print(s.getsockname()[1])
PY
  else
    echo $((20000 + RANDOM % 20000))
  fi
}

HOST_PORT="$(choose_port)"
cleanup() {
  "$RUNTIME" rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

"$RUNTIME" run --rm -d \
  --name "$CONTAINER_NAME" \
  --pids-limit 2048 \
  -p "127.0.0.1:${HOST_PORT}:5432" \
  -e POSTGRES_USER="$DB_USER" \
  -e POSTGRES_PASSWORD="$DB_PASSWORD" \
  -e POSTGRES_DB="$DB_NAME" \
  -e TS_TUNE_MEMORY="512MB" \
  -e TS_TUNE_NUM_CPUS="2" \
  "$IMAGE" >/dev/null

ready="false"
for _ in {1..60}; do
  if "$RUNTIME" exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    ready="true"
    break
  fi
  sleep 2
done

if [[ "$ready" != "true" ]]; then
  echo "TimescaleDB test container did not become ready."
  "$RUNTIME" logs "$CONTAINER_NAME" || true
  exit 1
fi

export ATRADE_MARKET_DATA_TIMESCALE_TEST_CONNECTION_STRING="Host=127.0.0.1;Port=${HOST_PORT};Database=${DB_NAME};Username=${DB_USER};Password=${DB_PASSWORD};Include Error Detail=true"

cd "$ROOT_DIR"
dotnet test tests/ATrade.MarketData.Timescale.Tests/ATrade.MarketData.Timescale.Tests.csproj \
  --nologo \
  --verbosity minimal
