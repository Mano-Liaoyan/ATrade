#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_backup=''
restore_original_env=0
probe_dir=''

temporary_api_port='5197'
temporary_frontend_direct_port='3117'
temporary_apphost_frontend_port='3017'
temporary_dashboard_port='5017'

cleanup() {
  if [[ -n "$env_backup" && -f "$env_backup" ]]; then
    mv "$env_backup" "$repo_root/.env"
    env_backup=''
    restore_original_env=0
  elif [[ "$restore_original_env" == '0' ]]; then
    rm -f "$repo_root/.env"
  fi

  if [[ -n "$probe_dir" && -d "$probe_dir" ]]; then
    rm -rf "$probe_dir"
  fi
}

trap cleanup EXIT

assert_contains() {
  local haystack="$1"
  local needle="$2"

  if [[ "$haystack" != *"$needle"* ]]; then
    printf 'expected to find %s in output:\n%s\n' "$needle" "$haystack" >&2
    return 1
  fi
}

capture_original_env() {
  if [[ -n "$env_backup" || "$restore_original_env" == '1' ]]; then
    return
  fi

  if [[ -f "$repo_root/.env" ]]; then
    env_backup="$(mktemp)"
    cp "$repo_root/.env" "$env_backup"
    restore_original_env=1
  fi
}

write_override_contract() {
  local dashboard_port="${1-}"

  capture_original_env

  cat >"$repo_root/.env" <<EOF
ATRADE_API_HTTP_PORT=$temporary_api_port
ATRADE_FRONTEND_DIRECT_HTTP_PORT=$temporary_frontend_direct_port
ATRADE_APPHOST_FRONTEND_HTTP_PORT=$temporary_apphost_frontend_port
EOF

  if [[ -n "$dashboard_port" ]]; then
    printf 'ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=%s\n' "$dashboard_port" >>"$repo_root/.env"
  fi
}

create_probe_project() {
  probe_dir="$(mktemp -d)"

  cat >"$probe_dir/PortContractProbe.csproj" <<EOF
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="$repo_root/src/ATrade.ServiceDefaults/ATrade.ServiceDefaults.csproj" />
  </ItemGroup>
</Project>
EOF

  cat >"$probe_dir/Program.cs" <<'EOF'
using ATrade.ServiceDefaults;

var contract = LocalDevelopmentPortContractLoader.Load();
Console.WriteLine($"api={contract.ApiHttpPort}");
Console.WriteLine($"frontendDirect={contract.FrontendDirectHttpPort}");
Console.WriteLine($"apphostFrontend={contract.AppHostFrontendHttpPort}");
Console.WriteLine($"dashboard={contract.AspireDashboardHttpPort}");
EOF
}

run_probe_and_capture() {
  local output

  set +e
  output="$(
    cd "$repo_root"
    env \
      -u ATRADE_API_HTTP_PORT \
      -u ATRADE_FRONTEND_DIRECT_HTTP_PORT \
      -u ATRADE_APPHOST_FRONTEND_HTTP_PORT \
      -u ATRADE_ASPIRE_DASHBOARD_HTTP_PORT \
      dotnet run --project "$probe_dir/PortContractProbe.csproj" 2>&1
  )"
  local status=$?
  set -e

  printf '%s\n__STATUS__=%s\n' "$output" "$status"
}

assert_dashboard_port_contract_parsing() {
  create_probe_project

  local probe_output

  write_override_contract
  probe_output="$(run_probe_and_capture)"
  assert_contains "$probe_output" 'api=5197'
  assert_contains "$probe_output" 'frontendDirect=3117'
  assert_contains "$probe_output" 'apphostFrontend=3017'
  assert_contains "$probe_output" 'dashboard=0'
  assert_contains "$probe_output" '__STATUS__=0'

  write_override_contract "$temporary_dashboard_port"
  probe_output="$(run_probe_and_capture)"
  assert_contains "$probe_output" "dashboard=$temporary_dashboard_port"
  assert_contains "$probe_output" '__STATUS__=0'

  write_override_contract 'not-a-port'
  probe_output="$(run_probe_and_capture)"
  assert_contains "$probe_output" 'ATRADE_ASPIRE_DASHBOARD_HTTP_PORT'
  assert_contains "$probe_output" 'not-a-port'
  assert_contains "$probe_output" '__STATUS__=1'

  write_override_contract '70000'
  probe_output="$(run_probe_and_capture)"
  assert_contains "$probe_output" 'ATRADE_ASPIRE_DASHBOARD_HTTP_PORT'
  assert_contains "$probe_output" '70000'
  assert_contains "$probe_output" '__STATUS__=1'

  write_override_contract "$temporary_dashboard_port"
}

main() {
  assert_dashboard_port_contract_parsing

  bash "$repo_root/tests/apphost/api-bootstrap-tests.sh"
  rm -rf /tmp/aspire-dcp*
  bash "$repo_root/tests/apphost/frontend-nextjs-bootstrap-tests.sh"
  bash "$repo_root/tests/apphost/apphost-infrastructure-manifest-tests.sh"
}

main "$@"
