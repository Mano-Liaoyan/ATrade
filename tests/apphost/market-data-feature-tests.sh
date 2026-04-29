#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$repo_root/scripts/local-env.sh"

export ATRADE_API_HTTP_PORT="$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"
atrade_load_local_port_contract "$repo_root"

api_pid=''
api_log=''
health_file=''
response_file=''
api_url="http://127.0.0.1:${ATRADE_API_HTTP_PORT}"

assert_file_contains() {
  local file_path="$1"
  local needle="$2"

  if [[ ! -f "$file_path" ]]; then
    printf 'expected file to exist: %s\n' "$file_path" >&2
    return 1
  fi

  if ! grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

cleanup() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  for temp_file in "$api_log" "$health_file" "$response_file"; do
    if [[ -n "$temp_file" && -f "$temp_file" ]]; then
      rm -f "$temp_file"
    fi
  done
}

trap cleanup EXIT

start_api() {
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"

  api_log="$(mktemp)"
  health_file="$(mktemp)"
  response_file="$(mktemp)"

  ASPNETCORE_URLS="$api_url" dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  local attempt
  local health_code=''
  for attempt in {1..40}; do
    health_code="$(curl --silent --show-error --output "$health_file" --write-out '%{http_code}' "$api_url/health" || true)"
    if [[ "$health_code" == '200' ]]; then
      break
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
      printf 'ATrade.Api exited before becoming healthy.\n' >&2
      cat "$api_log" >&2
      return 1
    fi

    sleep 0.5
  done

  if [[ "$health_code" != '200' ]]; then
    printf 'expected GET %s/health to return HTTP 200, got %s\n' "$api_url" "$health_code" >&2
    cat "$api_log" >&2
    return 1
  fi

  if [[ "$(cat "$health_file")" != 'ok' ]]; then
    printf 'expected GET %s/health to return ok, got %s\n' "$api_url" "$(cat "$health_file")" >&2
    return 1
  fi
}

assert_trending_payload() {
  local status_code
  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/market-data/trending")"
  if [[ "$status_code" != '200' ]]; then
    printf 'expected trending endpoint to return HTTP 200, got %s\n' "$status_code" >&2
    cat "$api_log" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
symbols = payload.get("symbols", [])
if len(symbols) < 6:
    raise SystemExit(f"expected at least 6 mocked trending symbols, got {len(symbols)}")
asset_classes = {item.get("assetClass") for item in symbols}
if "Stock" not in asset_classes or "ETF" not in asset_classes:
    raise SystemExit(f"expected both Stock and ETF trending symbols, got {asset_classes!r}")
for required in ("AAPL", "SPY"):
    if required not in {item.get("symbol") for item in symbols}:
        raise SystemExit(f"missing expected symbol {required}")
for item in symbols:
    factors = item.get("factors", {})
    for key in ("volumeSpike", "priceMomentum", "volatility", "newsSentimentPlaceholder"):
        if key not in factors:
            raise SystemExit(f"missing factor {key} in {item!r}")
    reasons = " ".join(item.get("reasons", []))
    if "placeholder" not in reasons.lower():
        raise SystemExit(f"expected placeholder sentiment reason in {item!r}")
PY
}

assert_candles_and_indicators() {
  local timeframe
  local status_code

  for timeframe in 1m 5m 1h 1D; do
    status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/market-data/AAPL/candles?timeframe=$timeframe")"
    if [[ "$status_code" != '200' ]]; then
      printf 'expected candles endpoint for %s to return HTTP 200, got %s\n' "$timeframe" "$status_code" >&2
      cat "$api_log" >&2
      return 1
    fi

    python3 - "$response_file" "$timeframe" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
timeframe = sys.argv[2]
if payload.get("symbol") != "AAPL":
    raise SystemExit(f"unexpected candle symbol: {payload!r}")
if payload.get("timeframe") != timeframe:
    raise SystemExit(f"unexpected candle timeframe: {payload!r}")
candles = payload.get("candles", [])
if len(candles) < 100:
    raise SystemExit(f"expected stable chart history for {timeframe}, got {len(candles)} candles")
for key in ("time", "open", "high", "low", "close", "volume"):
    if key not in candles[-1]:
        raise SystemExit(f"missing candle key {key}: {candles[-1]!r}")
PY

    status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/market-data/AAPL/indicators?timeframe=$timeframe")"
    if [[ "$status_code" != '200' ]]; then
      printf 'expected indicators endpoint for %s to return HTTP 200, got %s\n' "$timeframe" "$status_code" >&2
      cat "$api_log" >&2
      return 1
    fi

    python3 - "$response_file" "$timeframe" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
timeframe = sys.argv[2]
if payload.get("symbol") != "AAPL" or payload.get("timeframe") != timeframe:
    raise SystemExit(f"unexpected indicator identity: {payload!r}")
for key in ("movingAverages", "rsi", "macd"):
    values = payload.get(key, [])
    if len(values) < 100:
        raise SystemExit(f"expected indicator series {key} for {timeframe}, got {len(values)}")
PY
  done

  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/market-data/AAPL/candles?timeframe=10m")"
  if [[ "$status_code" != '400' ]]; then
    printf 'expected invalid timeframe to return HTTP 400, got %s\n' "$status_code" >&2
    return 1
  fi

  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/market-data/NOPE/candles?timeframe=1m")"
  if [[ "$status_code" != '404' ]]; then
    printf 'expected invalid symbol to return HTTP 404, got %s\n' "$status_code" >&2
    return 1
  fi
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for market-data-feature-tests.sh\n' >&2
    return 1
  fi

  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
  local api_program="$repo_root/src/ATrade.Api/Program.cs"
  local market_data_project="$repo_root/src/ATrade.MarketData/ATrade.MarketData.csproj"

  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.MarketData'
  assert_file_contains "$api_project" 'ATrade.MarketData.csproj'
  assert_file_contains "$market_data_project" 'Microsoft.AspNetCore.App'
  assert_file_contains "$api_program" 'builder.Services.AddMarketDataModule();'
  assert_file_contains "$api_program" 'builder.Services.AddSignalR();'
  assert_file_contains "$api_program" 'app.MapGet("/api/market-data/trending"'
  assert_file_contains "$api_program" 'app.MapHub<MarketDataHub>("/hubs/market-data");'

  dotnet build "$repo_root/ATrade.sln" --nologo --verbosity minimal >/dev/null

  start_api
  assert_trending_payload
  assert_candles_and_indicators
}

main "$@"
