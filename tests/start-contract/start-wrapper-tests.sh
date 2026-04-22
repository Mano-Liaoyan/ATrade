#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
run_script_backup=''

assert_contains() {
  local haystack="$1"
  local needle="$2"

  if [[ "$haystack" != *"$needle"* ]]; then
    printf 'expected to find %s in output:\n%s\n' "$needle" "$haystack" >&2
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
    printf 'expected %s to not contain %s\n' "$file_path" "$needle" >&2
    return 1
  fi
}

assert_executable_exists() {
  local file_path="$1"

  if [[ ! -f "$file_path" ]]; then
    printf 'expected file to exist: %s\n' "$file_path" >&2
    return 1
  fi

  if [[ ! -x "$file_path" ]]; then
    printf 'expected file to be executable: %s\n' "$file_path" >&2
    return 1
  fi
}

restore_run_script() {
  local run_script_path="$repo_root/scripts/start.run.sh"

  if [[ -n "$run_script_backup" && -f "$run_script_backup" ]]; then
    mv "$run_script_backup" "$run_script_path"
    chmod +x "$run_script_path"
    run_script_backup=''
  fi
}

install_run_stub() {
  local run_script_path="$repo_root/scripts/start.run.sh"

  assert_executable_exists "$run_script_path"

  run_script_backup="$(mktemp)"
  cp "$run_script_path" "$run_script_backup"
  trap restore_run_script EXIT

  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    'printf "__RUN_STUB__\\n"' \
    'printf "__ARGC__=%s\\n" "$#"' \
    'for arg in "$@"; do' \
    '  printf "__ARG__=%s\\n" "$arg"' \
    'done' \
    'exit "${START_RUN_STUB_EXIT_CODE:-0}"' > "$run_script_path"
  chmod +x "$run_script_path"
}

run_and_capture() {
  local output

  set +e
  output="$("$@" 2>&1)"
  local status=$?
  set -e

  printf '%s\n__STATUS__=%s\n' "$output" "$status"
}

assert_start_run_dispatches() {
  install_run_stub

  local run_output
  run_output="$(START_RUN_STUB_EXIT_CODE=0 run_and_capture "$repo_root/start" run alpha beta)"
  assert_contains "$run_output" '__RUN_STUB__'
  assert_contains "$run_output" '__ARGC__=2'
  assert_contains "$run_output" '__ARG__=alpha'
  assert_contains "$run_output" '__ARG__=beta'
  assert_contains "$run_output" '__STATUS__=0'

  local failing_run_output
  failing_run_output="$(START_RUN_STUB_EXIT_CODE=23 run_and_capture "$repo_root/start" run alpha beta)"
  assert_contains "$failing_run_output" '__RUN_STUB__'
  assert_contains "$failing_run_output" '__STATUS__=23'

  restore_run_script
}

assert_start_run_script_failure_paths() {
  local fake_bin
  fake_bin="$(mktemp -d)"
  ln -s "$(command -v dirname)" "$fake_bin/dirname"

  local missing_dotnet_output
  missing_dotnet_output="$(PATH="$fake_bin" run_and_capture /usr/bin/bash "$repo_root/scripts/start.run.sh")"
  rm -rf "$fake_bin"

  assert_contains "$missing_dotnet_output" 'dotnet is required to run the ATrade AppHost.'
  assert_contains "$missing_dotnet_output" '__STATUS__=1'

  local project_path="$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj"
  local backup_path
  backup_path="$(mktemp)"
  mv "$project_path" "$backup_path"

  local missing_project_output
  missing_project_output="$(run_and_capture /usr/bin/bash "$repo_root/scripts/start.run.sh")"

  mv "$backup_path" "$project_path"

  assert_contains "$missing_project_output" "Missing AppHost project at $project_path"
  assert_contains "$missing_project_output" '__STATUS__=1'
}

assert_apphost_launch_profile_bootstraps_runtime() {
  local launch_settings_path="$repo_root/src/ATrade.AppHost/Properties/launchSettings.json"

  assert_file_contains "$launch_settings_path" '"profiles"'
  assert_file_contains "$launch_settings_path" '"ATrade.AppHost"'
  assert_file_contains "$launch_settings_path" '"commandName": "Project"'
  assert_file_contains "$launch_settings_path" '"ASPNETCORE_URLS": "http://127.0.0.1:0"'
  assert_file_contains "$launch_settings_path" '"ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL": "http://127.0.0.1:0"'
  assert_file_contains "$launch_settings_path" '"ASPIRE_ALLOW_UNSECURED_TRANSPORT": "true"'

  local apphost_output
  apphost_output="$(run_and_capture timeout 20s dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj")"
  assert_contains "$apphost_output" 'Distributed application started. Press Ctrl+C to shut down.'
  assert_contains "$apphost_output" '__STATUS__=124'
}

main() {
  assert_executable_exists "$repo_root/start"
  assert_executable_exists "$repo_root/scripts/start.run.sh"

  local missing_output
  missing_output="$(run_and_capture "$repo_root/start")"
  assert_contains "$missing_output" 'Usage: ./start run'
  assert_contains "$missing_output" '__STATUS__=1'

  local bad_output
  bad_output="$(run_and_capture "$repo_root/start" bogus)"
  assert_contains "$bad_output" 'Unsupported command: bogus'
  assert_contains "$bad_output" 'Usage: ./start run'
  assert_contains "$bad_output" '__STATUS__=1'

  assert_file_contains "$repo_root/start" 'run)'
  assert_file_contains "$repo_root/start" 'exec "$repo_root/scripts/start.run.sh"'
  assert_file_contains "$repo_root/start.ps1" 'Usage: ./start.ps1 run'
  assert_file_contains "$repo_root/start.ps1" 'switch ($Command)'
  assert_file_contains "$repo_root/start.ps1" "'run'"
  assert_file_contains "$repo_root/start.ps1" '& "$PSScriptRoot/scripts/start.run.ps1"'
  assert_file_contains "$repo_root/start.cmd" 'Usage: ./start.cmd run'
  assert_file_contains "$repo_root/start.cmd" 'if "%COMMAND%"=="run" goto :run'
  assert_file_contains "$repo_root/start.cmd" ':run'
  assert_file_contains "$repo_root/start.cmd" 'powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*'
  assert_file_contains "$repo_root/start.cmd" 'exit /b %ERRORLEVEL%'
  assert_file_not_contains "$repo_root/start.cmd" 'if "%COMMAND%"=="run" ('
  assert_file_contains "$repo_root/scripts/start.run.sh" '#!/usr/bin/env bash'
  assert_file_contains "$repo_root/scripts/start.run.ps1" "\$ErrorActionPreference = 'Stop'"
  assert_file_contains "$repo_root/scripts/start.run.sh" 'src/ATrade.AppHost/ATrade.AppHost.csproj'
  assert_file_contains "$repo_root/scripts/start.run.ps1" 'src/ATrade.AppHost/ATrade.AppHost.csproj'
  assert_file_contains "$repo_root/scripts/start.run.sh" 'dotnet is required to run the ATrade AppHost.'
  assert_file_contains "$repo_root/scripts/start.run.sh" 'Missing AppHost project at %s'
  assert_file_contains "$repo_root/scripts/start.run.ps1" 'dotnet is required to run the ATrade AppHost.'
  assert_file_contains "$repo_root/scripts/start.run.ps1" 'Missing AppHost project at $ProjectPath'
  assert_file_contains "$repo_root/tests/start-contract/start-wrapper-windows.ps1" "Invoke-WrapperSmoke -Name 'start-ps1' -CommandText './start.ps1 run'"
  assert_file_contains "$repo_root/tests/start-contract/start-wrapper-windows.ps1" "Invoke-WrapperSmoke -Name 'start-cmd' -CommandText './start.cmd run'"
  assert_file_contains "$repo_root/tests/start-contract/start-wrapper-windows.ps1" '$SuccessMarker = '
  assert_file_contains "$repo_root/.github/workflows/windows-start-run.yml" 'runs-on: windows-latest'
  assert_file_contains "$repo_root/.github/workflows/windows-start-run.yml" 'actions/setup-dotnet@v4'
  assert_file_contains "$repo_root/.github/workflows/windows-start-run.yml" 'dotnet-version: 10.0.x'
  assert_file_contains "$repo_root/.github/workflows/windows-start-run.yml" 'actions/setup-node@v4'
  assert_file_contains "$repo_root/.github/workflows/windows-start-run.yml" './tests/start-contract/start-wrapper-windows.ps1'
  assert_file_contains "$repo_root/src/ATrade.Api/ATrade.Api.csproj" 'Sdk="Microsoft.NET.Sdk.Web"'
  assert_file_contains "$repo_root/src/ATrade.Api/ATrade.Api.csproj" 'ATrade.ServiceDefaults.csproj'
  assert_file_contains "$repo_root/src/ATrade.Api/Program.cs" 'builder.AddServiceDefaults()'
  assert_file_contains "$repo_root/src/ATrade.Api/Program.cs" 'app.MapGet("/health", () => Results.Text("ok", "text/plain"));'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" 'Sdk="Microsoft.NET.Sdk"'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" '<Sdk Name="Aspire.AppHost.Sdk" Version="13.2.3" />'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" '<IsAspireHost>true</IsAspireHost>'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" 'Aspire.Hosting.JavaScript'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" 'ATrade.Api.csproj'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'DistributedApplication.CreateBuilder(args)'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'AddProject<Projects.ATrade_Api>("api")'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'AddJavaScriptApp("frontend", "../../frontend", "dev")'
  assert_file_contains "$repo_root/frontend/package.json" '"dev": "node server.js"'
  assert_file_contains "$repo_root/frontend/server.js" 'const port = Number(process.env.PORT ?? 3000);'
  assert_file_contains "$repo_root/frontend/server.js" 'ATrade frontend bootstrap'
  assert_file_contains "$repo_root/scripts/README.md" 'The `run` contract is now bootstrapped in the repository.'
  assert_file_contains "$repo_root/scripts/README.md" './start run'
  assert_file_contains "$repo_root/scripts/README.md" 'are verified by GitHub Actions on `windows-latest` via `tests/start-contract/start-wrapper-windows.ps1`'
  assert_file_contains "$repo_root/README.md" 'Windows wrapper verification is backed by GitHub Actions on `windows-latest` through `tests/start-contract/start-wrapper-windows.ps1`.'
  assert_file_contains "$repo_root/PLAN.md" 'Verify `./start.ps1 run` and `./start.cmd run` on a Windows-hosted runtime or CI worker~~'
  assert_file_contains "$repo_root/plans/devops/CURRENT.md" 'Bootstrap the `start run` wrapper contract and Linux-hosted AppHost startup path'
  assert_file_contains "$repo_root/plans/devops/CURRENT.md" 'Verify `./start.ps1 run` and `./start.cmd run` on a Windows host or in CI~~'

  assert_start_run_dispatches
  assert_start_run_script_failure_paths
  assert_apphost_launch_profile_bootstraps_runtime
}

main "$@"
