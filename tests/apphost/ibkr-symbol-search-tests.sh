#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

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

main() {
  local contracts="$repo_root/src/ATrade.MarketData/MarketDataProviderContracts.cs"
  local models="$repo_root/src/ATrade.MarketData/MarketDataProviderModels.cs"
  local client="$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataClient.cs"
  local provider="$repo_root/src/ATrade.MarketData.Ibkr/IbkrMarketDataProvider.cs"
  local provider_tests="$repo_root/tests/ATrade.MarketData.Ibkr.Tests/IbkrMarketDataProviderTests.cs"

  assert_file_contains "$contracts" 'bool TrySearchSymbols(string query, out MarketDataSymbolSearchResponse? response, out MarketDataError? error);'
  assert_file_contains "$models" 'public sealed record MarketDataSymbolIdentity'
  assert_file_contains "$models" 'public sealed record MarketDataSymbolSearchResult'
  assert_file_contains "$models" 'public sealed record MarketDataSymbolSearchResponse'
  assert_file_contains "$models" 'SupportsSymbolSearch'
  assert_file_contains "$client" '/v1/api/iserver/secdef/search'
  assert_file_contains "$client" 'secType=STK'
  assert_file_contains "$provider" 'SupportsSymbolSearch: true'
  assert_file_contains "$provider" 'TrySearchSymbols'
  assert_file_contains "$provider" 'new MarketDataSymbolIdentity(contract.Symbol, contract.Conid, contract.AssetClass, contract.Exchange)'
  assert_file_contains "$provider_tests" 'TrySearchSymbols("AAPL"'
  assert_file_contains "$provider_tests" 'Assert.Equal("265598", searchMatch.Identity.ProviderSymbolId);'

  assert_file_not_contains "$repo_root/src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs" 'MockMarketData'
  assert_file_not_contains "$provider" 'new[] { "AAPL"'
  assert_file_not_contains "$provider" 'new[] {"AAPL"'

  dotnet test "$repo_root/tests/ATrade.MarketData.Ibkr.Tests/ATrade.MarketData.Ibkr.Tests.csproj" --nologo --verbosity minimal >/dev/null
}

main "$@"
