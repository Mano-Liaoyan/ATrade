#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

assert_path_exists() {
  local path="$1"

  if [[ ! -e "$path" ]]; then
    printf 'expected path to exist: %s\n' "$path" >&2
    return 1
  fi
}

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

  if [[ ! -f "$file_path" ]]; then
    printf 'expected file to exist: %s\n' "$file_path" >&2
    return 1
  fi

  if grep -Fq -- "$needle" "$file_path"; then
    printf 'expected %s not to contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

main() {
  local broker_project="$repo_root/src/ATrade.Brokers/ATrade.Brokers.csproj"
  local ibkr_project="$repo_root/src/ATrade.Brokers.Ibkr/ATrade.Brokers.Ibkr.csproj"
  local market_data_project="$repo_root/src/ATrade.MarketData/ATrade.MarketData.csproj"
  local api_project="$repo_root/src/ATrade.Api/ATrade.Api.csproj"
  local api_program="$repo_root/src/ATrade.Api/Program.cs"
  local provider_tests_project="$repo_root/tests/ATrade.ProviderAbstractions.Tests/ATrade.ProviderAbstractions.Tests.csproj"
  local market_module="$repo_root/src/ATrade.MarketData/MarketDataModuleServiceCollectionExtensions.cs"

  assert_path_exists "$broker_project"
  assert_path_exists "$repo_root/src/ATrade.Brokers/IBrokerProvider.cs"
  assert_path_exists "$repo_root/src/ATrade.Brokers/BrokerProviderStatus.cs"
  assert_path_exists "$repo_root/src/ATrade.MarketData/MarketDataProviderContracts.cs"
  assert_path_exists "$repo_root/src/ATrade.MarketData/MarketDataProviderModels.cs"
  assert_path_exists "$provider_tests_project"

  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.Brokers'
  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.ProviderAbstractions.Tests'
  assert_file_contains "$ibkr_project" 'ATrade.Brokers.csproj'
  assert_file_contains "$api_project" 'ATrade.Brokers.csproj'
  assert_file_contains "$market_data_project" 'Microsoft.AspNetCore.App'

  assert_file_contains "$api_program" 'IBrokerProvider brokerProvider'
  assert_file_contains "$api_program" 'IMarketDataService marketDataService'
  assert_file_not_contains "$api_program" 'IIbkrBrokerStatusService brokerStatusService'
  assert_file_not_contains "$api_program" 'new IbkrBrokerStatusService'
  assert_file_not_contains "$api_program" 'new IbkrGatewayClient'
  assert_file_not_contains "$api_program" 'new MockMarketDataService'
  assert_file_not_contains "$api_program" 'new MockMarketDataStreamingService'

  assert_file_contains "$market_module" 'AddSingleton<IMarketDataProvider>'
  assert_file_contains "$market_module" 'AddSingleton<IMarketDataService, MarketDataService>()'
  assert_file_contains "$market_module" 'AddSingleton<IMarketDataStreamingProvider>'
  assert_file_contains "$market_module" 'AddSingleton<IMarketDataStreamingService, MarketDataStreamingService>()'
  assert_file_not_contains "$market_module" 'AddSingleton<IMarketDataService, MockMarketDataService>()'

  assert_file_contains "$repo_root/src/ATrade.MarketData/MarketDataProviderModels.cs" 'ProviderNotConfigured'
  assert_file_contains "$repo_root/src/ATrade.MarketData/MarketDataProviderModels.cs" 'ProviderUnavailable'
  assert_file_contains "$repo_root/src/ATrade.MarketData/MockMarketDataService.cs" ': IMarketDataProvider'
  assert_file_contains "$repo_root/src/ATrade.MarketData/MockMarketDataStreamingService.cs" ': IMarketDataStreamingProvider'
}

main "$@"
