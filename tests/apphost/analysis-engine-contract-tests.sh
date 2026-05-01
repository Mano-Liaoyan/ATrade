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
# This contract test verifies the no-engine fallback. Keep it deterministic even
# when an ignored local .env opts into LEAN for manual runtime testing.
export ATRADE_ANALYSIS_ENGINE=none

api_pid=''
api_log=''
health_file=''
response_file=''
request_file=''
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

assert_provider_neutral_contract_boundaries() {
  if grep -RIn --exclude-dir=bin --exclude-dir=obj --exclude-dir=.git -E 'QuantConnect|LEAN|Lean' "$repo_root/src/ATrade.Analysis"; then
    printf 'core analysis contracts must remain provider-neutral and must not reference LEAN.\n' >&2
    return 1
  fi

  if grep -RIn --exclude-dir=bin --exclude-dir=obj --exclude-dir=.git -E 'QuantConnect|LeanAnalysisResult|LeanAnalysisRequest|QuantConnect' "$repo_root/src/ATrade.Api"; then
    printf 'API contracts must not expose LEAN-specific DTOs or QuantConnect types.\n' >&2
    return 1
  fi

  assert_file_contains "$repo_root/src/ATrade.Api/Program.cs" 'AddLeanAnalysisEngine(builder.Configuration)'
}

cleanup() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi

  for temp_file in "$api_log" "$health_file" "$response_file" "$request_file"; do
    if [[ -n "$temp_file" && -f "$temp_file" ]]; then
      rm -f "$temp_file"
    fi
  done
}

trap cleanup EXIT

assert_contract_sources() {
  local solution_path="$repo_root/ATrade.slnx"
  local analysis_project="$repo_root/src/ATrade.Analysis/ATrade.Analysis.csproj"
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
  local api_program="$repo_root/src/ATrade.Api/Program.cs"
  local contracts="$repo_root/src/ATrade.Analysis/AnalysisContracts.cs"
  local engine_contract="$repo_root/src/ATrade.Analysis/IAnalysisEngine.cs"
  local no_engine="$repo_root/src/ATrade.Analysis/NoConfiguredAnalysisEngine.cs"

  assert_file_contains "$solution_path" 'ATrade.Analysis'
  assert_file_contains "$analysis_project" 'ATrade.MarketData.csproj'
  assert_file_contains "$api_project" 'ATrade.Analysis.csproj'
  assert_file_contains "$api_program" 'builder.Services.AddAnalysisModule();'
  assert_file_contains "$api_program" '/api/analysis/engines'
  assert_file_contains "$api_program" '/api/analysis/run'
  assert_file_contains "$api_program" 'AnalysisEngineErrorCodes.EngineNotConfigured'
  assert_file_contains "$contracts" 'public sealed record AnalysisRequest'
  assert_file_contains "$contracts" 'MarketDataSymbolIdentity Symbol'
  assert_file_contains "$contracts" 'IReadOnlyList<OhlcvCandle> Bars'
  assert_file_contains "$contracts" 'public sealed record AnalysisResult'
  assert_file_contains "$contracts" 'AnalysisEngineMetadata Engine'
  assert_file_contains "$contracts" 'AnalysisDataSource Source'
  assert_file_contains "$engine_contract" 'public interface IAnalysisEngine'
  assert_file_contains "$engine_contract" 'ValueTask<AnalysisResult> AnalyzeAsync'
  assert_file_contains "$no_engine" 'analysis-engine-not-configured'
}

start_api_without_analysis_engine() {
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"

  api_log="$(mktemp)"
  health_file="$(mktemp)"
  response_file="$(mktemp)"
  request_file="$(mktemp)"

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
}

assert_analysis_discovery_response() {
  local status_code
  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/analysis/engines")"
  if [[ "$status_code" != '200' ]]; then
    printf 'expected GET /api/analysis/engines to return HTTP 200, got %s\n' "$status_code" >&2
    cat "$response_file" >&2
    cat "$api_log" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
if len(payload) != 1:
    raise SystemExit(f"expected one default analysis engine descriptor, got {payload!r}")
descriptor = payload[0]
metadata = descriptor.get("metadata", {})
capabilities = descriptor.get("capabilities", {})
if metadata.get("engineId") != "not-configured" or metadata.get("state") != "not-configured":
    raise SystemExit(f"expected not-configured metadata, got {metadata!r}")
if capabilities.get("supportsSignals") is not False or capabilities.get("supportsBacktests") is not False:
    raise SystemExit(f"not-configured engine must not claim production capabilities: {capabilities!r}")
PY
}

assert_analysis_run_not_configured_response() {
  cat >"$request_file" <<'JSON'
{
  "symbol": {
    "symbol": "AAPL",
    "provider": "ibkr",
    "providerSymbolId": "265598",
    "assetClass": "STK",
    "exchange": "NASDAQ",
    "currency": "USD"
  },
  "timeframe": "1D",
  "requestedAtUtc": "2026-04-29T00:00:00+00:00",
  "bars": [
    {
      "time": "2026-04-29T14:30:00+00:00",
      "open": 190.10,
      "high": 191.25,
      "low": 189.75,
      "close": 190.95,
      "volume": 1250000
    }
  ]
}
JSON

  local status_code
  status_code="$(curl --silent --show-error --request POST --header 'Content-Type: application/json' --data @"$request_file" --output "$response_file" --write-out '%{http_code}' "$api_url/api/analysis/run")"
  if [[ "$status_code" != '503' ]]; then
    printf 'expected POST /api/analysis/run to return HTTP 503 when no analysis engine is configured, got %s\n' "$status_code" >&2
    cat "$response_file" >&2
    cat "$api_log" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
if payload.get("status") != "not-configured":
    raise SystemExit(f"expected not-configured analysis status, got {payload!r}")
engine = payload.get("engine", {})
if engine.get("engineId") != "not-configured" or engine.get("provider") != "none":
    raise SystemExit(f"expected no-engine metadata, got {engine!r}")
error = payload.get("error", {})
if error.get("code") != "analysis-engine-not-configured":
    raise SystemExit(f"expected analysis-engine-not-configured error, got {payload!r}")
source = payload.get("source", {})
if source.get("source") != "analysis-engine-not-configured":
    raise SystemExit(f"expected not-configured result source, got {source!r}")
if payload.get("signals") != [] or payload.get("metrics") != [] or payload.get("backtest") is not None:
    raise SystemExit(f"not-configured analysis must not include fake signals, metrics, or backtest output: {payload!r}")
PY
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for analysis-engine-contract-tests.sh\n' >&2
    return 1
  fi

  assert_contract_sources
  assert_provider_neutral_contract_boundaries
  dotnet build "$repo_root/ATrade.slnx" --nologo --verbosity minimal >/dev/null
  start_api_without_analysis_engine
  assert_analysis_discovery_response
  assert_analysis_run_not_configured_response
}

main "$@"
