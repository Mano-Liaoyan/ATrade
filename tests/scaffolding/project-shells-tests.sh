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

main() {
  local accounts_project="$repo_root/src/ATrade.Accounts/ATrade.Accounts.csproj"
  local broker_contracts_project="$repo_root/src/ATrade.Brokers/ATrade.Brokers.csproj"
  local broker_project="$repo_root/src/ATrade.Brokers.Ibkr/ATrade.Brokers.Ibkr.csproj"
  local orders_project="$repo_root/src/ATrade.Orders/ATrade.Orders.csproj"
  local market_data_project="$repo_root/src/ATrade.MarketData/ATrade.MarketData.csproj"
  local worker_project="$repo_root/workers/ATrade.Ibkr.Worker/ATrade.Ibkr.Worker.csproj"

  assert_path_exists "$accounts_project"
  assert_path_exists "$broker_contracts_project"
  assert_path_exists "$broker_project"
  assert_path_exists "$orders_project"
  assert_path_exists "$market_data_project"
  assert_path_exists "$worker_project"

  assert_path_exists "$repo_root/src/ATrade.Accounts/AccountsAssemblyMarker.cs"
  assert_path_exists "$repo_root/src/ATrade.Brokers/IBrokerProvider.cs"
  assert_path_exists "$repo_root/src/ATrade.Brokers.Ibkr/IbkrGatewayClient.cs"
  assert_path_exists "$repo_root/src/ATrade.Orders/OrdersAssemblyMarker.cs"
  assert_path_exists "$repo_root/src/ATrade.MarketData/MarketDataAssemblyMarker.cs"
  assert_path_exists "$repo_root/workers/ATrade.Ibkr.Worker/Program.cs"
  assert_path_exists "$repo_root/workers/ATrade.Ibkr.Worker/IbkrWorkerShell.cs"

  assert_file_contains "$repo_root/src/ATrade.Accounts/AccountsAssemblyMarker.cs" 'namespace ATrade.Accounts;'
  assert_file_contains "$repo_root/src/ATrade.Brokers/IBrokerProvider.cs" 'namespace ATrade.Brokers;'
  assert_file_contains "$repo_root/src/ATrade.Brokers.Ibkr/IbkrGatewayClient.cs" '/v1/api/iserver/auth/status'
  assert_file_contains "$repo_root/src/ATrade.Orders/OrdersAssemblyMarker.cs" 'namespace ATrade.Orders;'
  assert_file_contains "$repo_root/src/ATrade.MarketData/MarketDataAssemblyMarker.cs" 'namespace ATrade.MarketData;'
  assert_file_contains "$repo_root/workers/ATrade.Ibkr.Worker/Program.cs" 'builder.AddServiceDefaults()'
  assert_file_contains "$repo_root/workers/ATrade.Ibkr.Worker/Program.cs" 'builder.Services.AddIbkrBrokerAdapter(builder.Configuration);'
  assert_file_contains "$repo_root/workers/ATrade.Ibkr.Worker/IbkrWorkerShell.cs" 'ATrade.Ibkr.Worker is disabled and will remain idle'
  assert_file_contains "$repo_root/workers/ATrade.Ibkr.Worker/IbkrWorkerShell.cs" 'rejected-live-mode'

  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.Accounts'
  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.Brokers'
  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.Brokers.Ibkr'
  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.Orders'
  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.MarketData'
  assert_file_contains "$repo_root/ATrade.sln" 'ATrade.Ibkr.Worker'

  dotnet build "$repo_root/ATrade.sln" --nologo --verbosity minimal >/dev/null
}

main "$@"
