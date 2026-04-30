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

assert_file_not_contains() {
  local file_path="$1"
  local needle="$2"

  if [[ -f "$file_path" ]] && grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
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

wait_for_api() {
  local code=''
  for _ in {1..80}; do
    code="$(curl --silent --show-error --output "$health_file" --write-out '%{http_code}' "$api_url/health" || true)"
    if [[ "$code" == '200' ]]; then
      return 0
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
      printf 'ATrade.Api exited before becoming healthy.\n' >&2
      cat "$api_log" >&2
      return 1
    fi

    sleep 0.5
  done

  printf 'expected /health to return HTTP 200, got %s\n' "$code" >&2
  cat "$api_log" >&2
  return 1
}

start_api_without_credentials() {
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
  api_log="$(mktemp)"
  health_file="$(mktemp)"
  response_file="$(mktemp)"

  ASPNETCORE_URLS="$api_url" dotnet run --project "$api_project" >"$api_log" 2>&1 &
  api_pid=$!

  wait_for_api
  if [[ "$(cat "$health_file")" != 'ok' ]]; then
    printf 'expected API health body to be ok, got %s\n' "$(cat "$health_file")" >&2
    return 1
  fi
}

assert_no_production_search_allowlist() {
  assert_file_not_contains "$repo_root/src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs" 'MockMarketData'
  assert_file_not_contains "$repo_root/src/ATrade.Api/Program.cs" 'new MockMarketData'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs" '/v1/api/iserver/secdef/search'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs" '/v1/api/iserver/secdef/info'

  if grep -RIn --include='*.cs' -E '"(AAPL|MSFT|NVDA|TSLA|GOOGL|AMZN|META|SPY|QQQ)"' \
      "$repo_root/src/ATrade.MarketData" \
      "$repo_root/src/ATrade.MarketData.Ibkr" \
      "$repo_root/src/ATrade.Api"; then
    printf 'production market-data/API source must not contain a hard-coded stock search allowlist.\n' >&2
    return 1
  fi
}

assert_search_contract_source() {
  assert_file_contains "$repo_root/src/ATrade.Api/Program.cs" '/api/market-data/search'
  assert_file_contains "$repo_root/src/ATrade.Api/Program.cs" 'CancellationToken cancellationToken'
  assert_file_contains "$repo_root/src/ATrade.MarketData/MarketDataService.cs" 'MarketDataSymbolSearchLimits.MaximumLimit'
  assert_file_contains "$repo_root/src/ATrade.MarketData/MarketDataProviderModels.cs" 'string Provider'
  assert_file_contains "$repo_root/src/ATrade.MarketData/MarketDataProviderModels.cs" 'string Currency'
  assert_file_contains "$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs" 'new MarketDataSymbolIdentity'
  assert_file_contains "$repo_root/tests/ATrade.MarketData.Ibkr.Tests/IbkrMarketDataProviderTests.cs" 'Assert.Equal("NASDAQ", searchMatch.Identity.Exchange)'
  assert_file_contains "$repo_root/tests/ATrade.MarketData.Ibkr.Tests/IbkrMarketDataProviderTests.cs" 'Assert.Equal("USD", searchMatch.Identity.Currency)'
  assert_file_contains "$repo_root/tests/ATrade.MarketData.Ibkr.Tests/IbkrMarketDataProviderTests.cs" 'Assert.Equal("265598", searchMatch.Identity.ProviderSymbolId)'
}

assert_api_search_errors_without_credentials() {
  local status_code

  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/market-data/search?query=Z&assetClass=stock&limit=2")"
  if [[ "$status_code" != '400' ]]; then
    printf 'expected short search query to return HTTP 400, got %s\n' "$status_code" >&2
    cat "$response_file" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
if payload.get("code") != "invalid-search-query":
    raise SystemExit(f"expected invalid-search-query payload, got {payload!r}")
PY

  status_code="$(curl --silent --show-error --output "$response_file" --write-out '%{http_code}' "$api_url/api/market-data/search?query=ZZ&assetClass=stock&limit=3")"
  if [[ "$status_code" == '200' ]]; then
    printf 'expected no-credential symbol search to return a non-200 provider error.\n' >&2
    cat "$response_file" >&2
    return 1
  fi

  python3 - "$response_file" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
if payload.get("code") not in {"provider-not-configured", "provider-unavailable", "authentication-required"}:
    raise SystemExit(f"expected stable provider error code, got {payload!r}")
if "results" in payload or "symbols" in payload:
    raise SystemExit(f"provider error must not include fake search results: {payload!r}")
for forbidden in ("IBKR_USERNAME", "IBKR_PASSWORD", "IBKR_ACCOUNT_ID", "AAPL", "MSFT", "NVDA"):
    if forbidden in json.dumps(payload):
        raise SystemExit(f"search error leaked placeholder credentials or fake catalog symbol: {forbidden}")
PY
}

assert_frontend_search_controls() {
  assert_file_contains "$repo_root/frontend/components/SymbolSearch.tsx" 'data-testid="symbol-search"'
  assert_file_contains "$repo_root/frontend/components/SymbolSearch.tsx" 'Search IBKR stocks'
  assert_file_contains "$repo_root/frontend/components/SymbolSearch.tsx" 'Pin result'
  assert_file_contains "$repo_root/frontend/components/SymbolSearch.tsx" 'No local fallback catalog is used.'
  assert_file_contains "$repo_root/frontend/components/SymbolSearch.tsx" '<MarketLogo'
  assert_file_contains "$repo_root/frontend/components/SymbolSearch.tsx" 'Provider {provider.toUpperCase()}'
  assert_file_contains "$repo_root/frontend/components/SymbolSearch.tsx" 'Market {exchange}'
  assert_file_contains "$repo_root/frontend/components/SymbolSearch.tsx" 'IBKR conid'
  assert_file_contains "$repo_root/frontend/components/SymbolSearch.tsx" 'key={pinKey}'
  assert_file_contains "$repo_root/frontend/components/SymbolSearch.tsx" 'pinnedSet.has(pinKey)'
  assert_file_not_contains "$repo_root/frontend/components/SymbolSearch.tsx" 'pinnedSet.has(symbol'
  assert_file_contains "$repo_root/frontend/components/MarketLogo.tsx" 'NASDAQ Stock Market'
  assert_file_contains "$repo_root/frontend/components/MarketLogo.tsx" 'Toronto Stock Exchange'
  assert_file_contains "$repo_root/frontend/components/MarketLogo.tsx" 'Hong Kong Exchange'
  assert_file_contains "$repo_root/frontend/lib/marketDataClient.ts" '/api/market-data/search'
  assert_file_contains "$repo_root/frontend/lib/watchlistClient.ts" 'createWatchlistInstrumentKey'
  assert_file_contains "$repo_root/frontend/lib/watchlistClient.ts" 'instrumentKey: string'
  assert_file_contains "$repo_root/frontend/components/TradingWorkspace.tsx" 'createSearchResultWatchlistInput(result)'
  assert_file_contains "$repo_root/frontend/components/TradingWorkspace.tsx" 'pinnedInstrumentKeys'
  assert_file_not_contains "$repo_root/frontend/components/TradingWorkspace.tsx" 'pinnedSymbolNames'
  assert_file_not_contains "$repo_root/frontend/components/TradingWorkspace.tsx" 'savingSymbol'
  assert_file_contains "$repo_root/frontend/components/TradingWorkspace.tsx" 'onTogglePin={handleToggleSearchPin}'
  assert_file_contains "$repo_root/frontend/components/Watchlist.tsx" 'Use IBKR stock search'
  assert_file_contains "$repo_root/frontend/components/SymbolChartView.tsx" 'Search another IBKR stock'
  assert_file_not_contains "$repo_root/frontend/components/TradingWorkspace.tsx" 'TRENDING_SYMBOLS'
}

main() {
  if ! command -v curl >/dev/null 2>&1; then
    printf 'curl is required for ibkr-symbol-search-tests.sh\n' >&2
    return 1
  fi

  assert_no_production_search_allowlist
  assert_search_contract_source
  dotnet test "$repo_root/tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj" --nologo --verbosity minimal
  dotnet test "$repo_root/tests/ATrade.ProviderAbstractions.Tests/ATrade.ProviderAbstractions.Tests.csproj" --nologo --verbosity minimal
  assert_frontend_search_controls
  start_api_without_credentials
  assert_api_search_errors_without_credentials
  printf 'IBKR symbol search contract, error behavior, and frontend controls verified.\n'
}

main "$@"
