#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$repo_root/scripts/local-env.sh"

free_port() {
  python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
}

export ATRADE_API_HTTP_PORT="$(free_port)"
atrade_load_local_port_contract "$repo_root"

api_pid=''
api_log=''
health_file=''
response_file=''
fake_gateway_pid=''
fake_gateway_port=''
fake_gateway_dir=''
fake_gateway_log=''
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

assert_file_not_contains() {
  local file_path="$1"
  local needle="$2"

  if [[ -f "$file_path" ]] && grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

stop_api() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  for temp_file in "$api_log" "$health_file" "$response_file"; do
    if [[ -n "$temp_file" && -f "$temp_file" ]]; then
      rm -f "$temp_file"
    fi
  done

  api_pid=''
  api_log=''
  health_file=''
  response_file=''
}

stop_fake_gateway() {
  if [[ -n "$fake_gateway_pid" ]] && kill -0 "$fake_gateway_pid" 2>/dev/null; then
    kill "$fake_gateway_pid" 2>/dev/null || true
    wait "$fake_gateway_pid" 2>/dev/null || true
  fi

  if [[ -n "$fake_gateway_dir" && -d "$fake_gateway_dir" ]]; then
    rm -rf "$fake_gateway_dir"
  fi

  fake_gateway_pid=''
  fake_gateway_port=''
  fake_gateway_dir=''
  fake_gateway_log=''
}

cleanup() {
  stop_api
  stop_fake_gateway
}

trap cleanup EXIT

start_api_with_ibkr_env() {
  local integration_enabled="$1"
  local gateway_url="$2"
  local gateway_port="$3"
  local username="$4"
  local password="$5"
  local account_id="$6"
  local timeout_seconds="${7:-1}"
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"

  stop_api
  api_log="$(mktemp)"
  health_file="$(mktemp)"
  response_file="$(mktemp)"

  ATRADE_BROKER_INTEGRATION_ENABLED="$integration_enabled" \
  ATRADE_BROKER_ACCOUNT_MODE=Paper \
  ATRADE_IBKR_GATEWAY_URL="$gateway_url" \
  ATRADE_IBKR_GATEWAY_PORT="$gateway_port" \
  ATRADE_IBKR_GATEWAY_IMAGE=voyz/ibeam:latest \
  ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS="$timeout_seconds" \
  ATRADE_IBKR_USERNAME="$username" \
  ATRADE_IBKR_PASSWORD="$password" \
  ATRADE_IBKR_PAPER_ACCOUNT_ID="$account_id" \
  ASPNETCORE_URLS="$api_url" dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  local attempt
  local health_code=''
  for attempt in {1..60}; do
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
    printf 'expected GET /health to return HTTP 200, got %s\n' "$health_code" >&2
    cat "$api_log" >&2
    return 1
  fi

  if [[ "$(cat "$health_file")" != 'ok' ]]; then
    printf 'expected GET /health to return ok, got %s\n' "$(cat "$health_file")" >&2
    return 1
  fi
}

start_api_without_real_credentials() {
  start_api_with_ibkr_env \
    true \
    'https://127.0.0.1:5000' \
    '5000' \
    'IBKR_USERNAME' \
    'IBKR_PASSWORD' \
    'IBKR_ACCOUNT_ID' \
    1
}

start_fake_ibeam_gateway() {
  local mode="$1"

  stop_fake_gateway
  fake_gateway_port="$(free_port)"
  fake_gateway_dir="$(mktemp -d)"
  fake_gateway_log="$fake_gateway_dir/fake-ibeam.log"

  openssl req \
    -x509 \
    -newkey rsa:2048 \
    -nodes \
    -keyout "$fake_gateway_dir/key.pem" \
    -out "$fake_gateway_dir/cert.pem" \
    -days 1 \
    -subj '/CN=localhost' >/dev/null 2>&1

  python3 - "$fake_gateway_port" "$fake_gateway_dir/cert.pem" "$fake_gateway_dir/key.pem" "$mode" >"$fake_gateway_log" 2>&1 <<'PY' &
import json
import ssl
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

port = int(sys.argv[1])
cert_path = sys.argv[2]
key_path = sys.argv[3]
mode = sys.argv[4]

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return

    def send_json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_html(self, status, reason, html):
        data = html.encode("utf-8")
        self.send_response(status, reason)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/v1/api/iserver/auth/status":
            self.send_json(200, {
                "authenticated": mode == "auth",
                "connected": True,
                "competing": False,
                "message": "ready" if mode == "auth" else "login required",
            })
            return

        if path == "/v1/api/iserver/marketdata/snapshot":
            self.send_json(200, [{
                "conid": "265598",
                "55": "AAPL",
                "31": "196.44",
                "83": "1.18%",
                "87": "58000000",
            }])
            return

        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/v1/api/iserver/scanner/run":
            self.send_json(404, {"error": "not found"})
            return

        length_header = self.headers.get("Content-Length")
        if not length_header or int(length_header) <= 0 or self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            self.send_html(411, "Length Required", "<html><body>Length Required</body></html>")
            return

        self.rfile.read(int(length_header))
        if mode != "auth":
            self.send_json(403, {"error": "not authenticated"})
            return

        self.send_json(200, [{
            "rank": 1,
            "conid": "265598",
            "symbol": "AAPL",
            "companyName": "Apple Inc.",
            "secType": "STK",
            "exchange": "NASDAQ",
            "currency": "USD",
            "sector": "Technology",
            "score": 99.4,
            "changePercent": 1.18,
            "volume": 58000000,
        }])

server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(cert_path, key_path)
server.socket = context.wrap_socket(server.socket, server_side=True)
server.serve_forever()
PY
  fake_gateway_pid=$!

  local attempt
  local auth_code=''
  for attempt in {1..40}; do
    auth_code="$(curl --insecure --silent --output /dev/null --write-out '%{http_code}' "https://127.0.0.1:${fake_gateway_port}/v1/api/iserver/auth/status" || true)"
    if [[ "$auth_code" == '200' ]]; then
      return 0
    fi

    if ! kill -0 "$fake_gateway_pid" 2>/dev/null; then
      printf 'fake iBeam gateway exited before becoming healthy.\n' >&2
      cat "$fake_gateway_log" >&2
      return 1
    fi

    sleep 0.25
  done

  printf 'expected fake iBeam auth status endpoint to return HTTP 200, got %s\n' "$auth_code" >&2
  cat "$fake_gateway_log" >&2
  return 1
}

assert_provider_error_response() {
  local path="$1"
  local expected_code="$2"
  local status_code

  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url$path")"
  if [[ "$status_code" != '503' ]]; then
    printf 'expected %s to return HTTP 503 provider error, got %s\n' "$path" "$status_code" >&2
    cat "$response_file" >&2
    cat "$api_log" >&2
    return 1
  fi

  python3 - "$response_file" "$expected_code" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
expected_code = sys.argv[2]
if payload.get("code") != expected_code:
    raise SystemExit(f"expected {expected_code} response, got {payload!r}")
message = payload.get("message", "")
if "IBKR" not in message or "iBeam" not in message:
    raise SystemExit(f"provider error response must explain IBKR/iBeam state: {payload!r}")
serialized = json.dumps(payload)
for forbidden in ("mock", "IBKR_USERNAME", "IBKR_PASSWORD", "IBKR_ACCOUNT_ID", "paper-user", "paper-password", "DU1234567", "AAPL", "MSFT", "NVDA"):
    if forbidden in serialized:
        raise SystemExit(f"provider error response contained forbidden fake/catalog/credential value: {forbidden}")
if "symbols" in payload or "results" in payload:
    raise SystemExit(f"provider error must not include fake success payload data: {payload!r}")
PY
}

assert_fake_authenticated_trending_response() {
  local status_code

  start_fake_ibeam_gateway auth
  start_api_with_ibkr_env \
    true \
    "https://127.0.0.1:${fake_gateway_port}" \
    "$fake_gateway_port" \
    'paper-user' \
    'paper-password' \
    'DU1234567' \
    5

  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/market-data/trending")"
  if [[ "$status_code" != '200' ]]; then
    printf 'expected fake authenticated scanner trending endpoint to return HTTP 200, got %s\n' "$status_code" >&2
    cat "$response_file" >&2
    cat "$api_log" >&2
    cat "$fake_gateway_log" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
if payload.get("source") != "ibkr-ibeam-scanner:STK.US.MAJOR:TOP_PERC_GAIN":
    raise SystemExit(f"expected IBKR scanner source, got {payload!r}")
symbols = payload.get("symbols")
if not isinstance(symbols, list) or len(symbols) != 1:
    raise SystemExit(f"expected one trending symbol, got {payload!r}")
symbol = symbols[0]
if symbol.get("symbol") != "AAPL" or symbol.get("name") != "Apple Inc.":
    raise SystemExit(f"expected fake IBKR scanner AAPL payload, got {payload!r}")
if symbol.get("lastPrice") != 196.44 or symbol.get("changePercent") != 1.18:
    raise SystemExit(f"expected snapshot-enriched price/change, got {payload!r}")
if "IBKR scanner" not in json.dumps(symbol.get("reasons", [])):
    raise SystemExit(f"expected IBKR scanner reason metadata, got {payload!r}")
serialized = json.dumps(payload)
for forbidden in ("Mocked factors", "paper-user", "paper-password", "DU1234567"):
    if forbidden in serialized:
        raise SystemExit(f"trending success payload leaked forbidden value: {forbidden}")
PY

  stop_api
  stop_fake_gateway
}

assert_market_data_source_contract() {
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
  local api_program="$repo_root/src/ATrade.Api/Program.cs"
  local market_data_project="$repo_root/src/ATrade.MarketData/ATrade.MarketData.csproj"
  local ibkr_project="$repo_root/src/ATrade.MarketData.Ibkr/ATrade.MarketData.Ibkr.csproj"

  assert_file_contains "$repo_root/ATrade.slnx" 'ATrade.MarketData.Ibkr'
  assert_file_contains "$api_project" 'ATrade.MarketData.Ibkr.csproj'
  assert_file_contains "$api_project" 'ATrade.MarketData.csproj'
  assert_file_contains "$market_data_project" 'Microsoft.AspNetCore.App'
  assert_file_contains "$ibkr_project" 'ATrade.Brokers.Ibkr.csproj'
  assert_file_contains "$api_program" 'builder.Services.AddMarketDataModule();'
  assert_file_contains "$api_program" 'builder.Services.AddIbkrMarketDataProvider();'
  assert_file_contains "$api_program" '/api/market-data/trending'
  assert_file_contains "$api_program" 'app.MapHub<MarketDataHub>("/hubs/market-data");'
  assert_file_contains "$repo_root/src/ATrade.MarketData/MarketDataModels.cs" 'string Source = "provider"'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs" 'IbkrMarketDataSource.History'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs" 'IbkrMarketDataSource.Snapshot'
  assert_file_not_contains "$repo_root/src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs" 'MockMarketData'
  assert_file_not_contains "$repo_root/frontend/components/TrendingList.tsx" 'Mocked factors'
}

assert_safe_trending_state_responses() {
  start_api_with_ibkr_env \
    false \
    'https://127.0.0.1:5000' \
    '5000' \
    'IBKR_USERNAME' \
    'IBKR_PASSWORD' \
    'IBKR_ACCOUNT_ID' \
    1
  assert_provider_error_response '/api/market-data/trending' 'provider-not-configured'

  start_api_without_real_credentials
  assert_provider_error_response '/api/market-data/trending' 'provider-not-configured'

  local unreachable_port
  unreachable_port="$(free_port)"
  start_api_with_ibkr_env \
    true \
    "https://127.0.0.1:${unreachable_port}" \
    "$unreachable_port" \
    'paper-user' \
    'paper-password' \
    'DU1234567' \
    1
  assert_provider_error_response '/api/market-data/trending' 'provider-unavailable'

  start_fake_ibeam_gateway unauth
  start_api_with_ibkr_env \
    true \
    "https://127.0.0.1:${fake_gateway_port}" \
    "$fake_gateway_port" \
    'paper-user' \
    'paper-password' \
    'DU1234567' \
    5
  assert_provider_error_response '/api/market-data/trending' 'provider-unavailable'
  stop_api
  stop_fake_gateway
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for market-data-feature-tests.sh\n' >&2
    return 1
  fi

  if ! command -v openssl >/dev/null 2>&1; then
    printf 'openssl is required for fake HTTPS iBeam checks in market-data-feature-tests.sh\n' >&2
    return 1
  fi

  assert_market_data_source_contract
  dotnet build "$repo_root/ATrade.slnx" --nologo --verbosity minimal >/dev/null
  assert_safe_trending_state_responses
  start_api_without_real_credentials
  assert_provider_error_response '/api/market-data/UNCONFIGURED/candles?timeframe=1D' 'provider-not-configured'
  assert_provider_error_response '/api/market-data/UNCONFIGURED/indicators?timeframe=1D' 'provider-not-configured'
  stop_api
  assert_fake_authenticated_trending_response
}

main "$@"
