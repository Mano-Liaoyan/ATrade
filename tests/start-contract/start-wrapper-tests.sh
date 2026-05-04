#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
bash_exe="${BASH:-}"
if [[ -z "$bash_exe" ]]; then
  bash_exe="$(command -v bash)"
fi

. "$repo_root/scripts/local-env.sh"
atrade_load_local_port_contract "$repo_root"

run_script_backup=''
env_backup=''
restore_original_env=0
env_state_captured=0
dashboard_smoke_pid=''
dashboard_smoke_log=''

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

assert_file_not_exists() {
  local file_path="$1"

  if [[ -e "$file_path" ]]; then
    printf 'expected file to not exist: %s\n' "$file_path" >&2
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

restore_local_env() {
  if [[ -n "$env_backup" && -f "$env_backup" ]]; then
    mv "$env_backup" "$repo_root/.env"
    env_backup=''
    restore_original_env=0
    env_state_captured=0
  elif [[ "$restore_original_env" == '0' ]]; then
    rm -f "$repo_root/.env"
    env_state_captured=0
  fi
}

cleanup() {
  if [[ -n "$dashboard_smoke_pid" ]] && kill -0 "$dashboard_smoke_pid" 2>/dev/null; then
    kill "$dashboard_smoke_pid" 2>/dev/null || true
    wait "$dashboard_smoke_pid" 2>/dev/null || true
  fi

  restore_run_script
  restore_local_env

  if [[ -n "$dashboard_smoke_log" && -f "$dashboard_smoke_log" ]]; then
    rm -f "$dashboard_smoke_log"
  fi
}

trap cleanup EXIT

capture_original_env() {
  if [[ "$env_state_captured" == '1' ]]; then
    return
  fi

  env_state_captured=1

  if [[ -f "$repo_root/.env" ]]; then
    env_backup="$(mktemp)"
    cp "$repo_root/.env" "$env_backup"
    restore_original_env=1
  fi
}

write_local_port_contract() {
  local api_port="$1"
  local frontend_direct_port="$2"
  local apphost_frontend_port="$3"
  local dashboard_port="$4"

  capture_original_env

  cat >"$repo_root/.env" <<EOF
ATRADE_API_HTTP_PORT=$api_port
ATRADE_FRONTEND_DIRECT_HTTP_PORT=$frontend_direct_port
ATRADE_APPHOST_FRONTEND_HTTP_PORT=$apphost_frontend_port
ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=$dashboard_port
EOF
}

free_port() {
  python3 - <<'PY'
import socket

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

run_with_local_contract_environment() {
  env \
    -u ATRADE_API_HTTP_PORT \
    -u ATRADE_FRONTEND_DIRECT_HTTP_PORT \
    -u ATRADE_APPHOST_FRONTEND_HTTP_PORT \
    -u ATRADE_ASPIRE_DASHBOARD_HTTP_PORT \
    -u ASPNETCORE_URLS \
    -u ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL \
    -u ASPIRE_ALLOW_UNSECURED_TRANSPORT \
    "$@"
}

assert_local_env_loader_overlays_template_and_preserves_process_environment() {
  capture_original_env

  cat >"$repo_root/.env" <<'EOF'
ATRADE_API_HTTP_PORT=6198
ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=6098
EOF

  local loader_output
  loader_output="$(
    env \
      -u ATRADE_FRONTEND_DIRECT_HTTP_PORT \
      -u ATRADE_APPHOST_FRONTEND_HTTP_PORT \
      -u ATRADE_ASPIRE_DASHBOARD_HTTP_PORT \
      ATRADE_API_HTTP_PORT=7198 \
      "$bash_exe" -c '
        set -euo pipefail
        repo_root="$1"
        . "$repo_root/scripts/local-env.sh"
        atrade_load_local_port_contract "$repo_root"
        printf "__ATRADE_PORT_CONTRACT_PATH__=%s\n" "${ATRADE_PORT_CONTRACT_PATH-}"
        printf "__ATRADE_API_HTTP_PORT__=%s\n" "${ATRADE_API_HTTP_PORT-}"
        printf "__ATRADE_FRONTEND_DIRECT_HTTP_PORT__=%s\n" "${ATRADE_FRONTEND_DIRECT_HTTP_PORT-}"
        printf "__ATRADE_APPHOST_FRONTEND_HTTP_PORT__=%s\n" "${ATRADE_APPHOST_FRONTEND_HTTP_PORT-}"
        printf "__ATRADE_ASPIRE_DASHBOARD_HTTP_PORT__=%s\n" "${ATRADE_ASPIRE_DASHBOARD_HTTP_PORT-}"
        printf "__ATRADE_BROKER_INTEGRATION_ENABLED__=%s\n" "${ATRADE_BROKER_INTEGRATION_ENABLED-}"
      ' _ "$repo_root"
  )"

  assert_contains "$loader_output" "__ATRADE_PORT_CONTRACT_PATH__=$repo_root/.env"
  assert_contains "$loader_output" '__ATRADE_API_HTTP_PORT__=7198'
  assert_contains "$loader_output" '__ATRADE_FRONTEND_DIRECT_HTTP_PORT__=3111'
  assert_contains "$loader_output" '__ATRADE_APPHOST_FRONTEND_HTTP_PORT__=3000'
  assert_contains "$loader_output" '__ATRADE_ASPIRE_DASHBOARD_HTTP_PORT__=6098'
  assert_contains "$loader_output" '__ATRADE_BROKER_INTEGRATION_ENABLED__=false'

  if [[ -z "$env_backup" && "$restore_original_env" == '0' ]]; then
    rm -f "$repo_root/.env"
  fi
}

install_run_stub() {
  local run_script_path="$repo_root/scripts/start.run.sh"

  assert_executable_exists "$run_script_path"

  run_script_backup="$(mktemp)"
  cp "$run_script_path" "$run_script_backup"

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
  missing_dotnet_output="$(PATH="$fake_bin" run_and_capture "$bash_exe" "$repo_root/scripts/start.run.sh")"
  rm -rf "$fake_bin"

  assert_contains "$missing_dotnet_output" 'dotnet is required to run the ATrade AppHost.'
  assert_contains "$missing_dotnet_output" '__STATUS__=1'

  local project_path="$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj"
  local backup_path
  backup_path="$(mktemp)"
  mv "$project_path" "$backup_path"

  local missing_project_output
  missing_project_output="$(run_and_capture "$bash_exe" "$repo_root/scripts/start.run.sh")"

  mv "$backup_path" "$project_path"

  assert_contains "$missing_project_output" "Missing AppHost project at $project_path"
  assert_contains "$missing_project_output" '__STATUS__=1'
}

assert_start_run_script_loads_dashboard_port_contract() {
  local fake_bin
  fake_bin="$(mktemp -d)"

  cat >"$fake_bin/dotnet" <<'EOF'
#!/usr/bin/env bash
printf '__FAKE_DOTNET__\n'
printf '__ASPNETCORE_URLS__=%s\n' "${ASPNETCORE_URLS-}"
printf '__ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL__=%s\n' "${ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL-}"
printf '__ASPIRE_ALLOW_UNSECURED_TRANSPORT__=%s\n' "${ASPIRE_ALLOW_UNSECURED_TRANSPORT-}"
for arg in "$@"; do
  printf '__DOTNET_ARG__=%s\n' "$arg"
done
EOF
  chmod +x "$fake_bin/dotnet"

  write_local_port_contract 5198 3118 3018 5018

  local run_output
  run_output="$(PATH="$fake_bin:$PATH" run_and_capture run_with_local_contract_environment "$bash_exe" "$repo_root/scripts/start.run.sh" alpha beta)"

  rm -rf "$fake_bin"

  assert_contains "$run_output" '__FAKE_DOTNET__'
  assert_contains "$run_output" '__ASPNETCORE_URLS__=http://127.0.0.1:5018'
  assert_contains "$run_output" '__ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL__=http://127.0.0.1:0'
  assert_contains "$run_output" '__ASPIRE_ALLOW_UNSECURED_TRANSPORT__=true'
  assert_contains "$run_output" '__DOTNET_ARG__=run'
  assert_contains "$run_output" '__DOTNET_ARG__=--project'
  assert_contains "$run_output" "__DOTNET_ARG__=$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj"
  assert_contains "$run_output" '__DOTNET_ARG__=--no-launch-profile'
  assert_contains "$run_output" '__DOTNET_ARG__=--'
  assert_contains "$run_output" '__DOTNET_ARG__=alpha'
  assert_contains "$run_output" '__DOTNET_ARG__=beta'
  assert_contains "$run_output" '__STATUS__=0'
}

dashboard_port_is_open() {
  local dashboard_port="$1"

  python3 - "$dashboard_port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket() as sock:
    sock.settimeout(0.25)
    raise SystemExit(0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1)
PY
}

assert_start_run_dashboard_port_smoke() {
  local ports
  ports="$(python3 - <<'PY'
import socket

sockets = [socket.socket() for _ in range(4)]
try:
    for sock in sockets:
        sock.bind(("127.0.0.1", 0))
    print(" ".join(str(sock.getsockname()[1]) for sock in sockets))
finally:
    for sock in sockets:
        sock.close()
PY
)"

  local api_port frontend_direct_port apphost_frontend_port dashboard_port
  read -r api_port frontend_direct_port apphost_frontend_port dashboard_port <<<"$ports"
  write_local_port_contract "$api_port" "$frontend_direct_port" "$apphost_frontend_port" "$dashboard_port"

  dashboard_smoke_log="$(mktemp)"
  (
    cd "$repo_root"
    run_with_local_contract_environment "$repo_root/scripts/start.run.sh"
  ) >"$dashboard_smoke_log" 2>&1 &
  dashboard_smoke_pid=$!

  local attempt
  for attempt in {1..90}; do
    if dashboard_port_is_open "$dashboard_port"; then
      kill "$dashboard_smoke_pid" 2>/dev/null || true
      wait "$dashboard_smoke_pid" 2>/dev/null || true
      dashboard_smoke_pid=''
      return
    fi

    if ! kill -0 "$dashboard_smoke_pid" 2>/dev/null; then
      printf 'AppHost exited before dashboard port %s opened.\n' "$dashboard_port" >&2
      cat "$dashboard_smoke_log" >&2
      return 1
    fi

    sleep 0.5
  done

  printf 'expected Aspire dashboard port %s to accept loopback connections.\n' "$dashboard_port" >&2
  cat "$dashboard_smoke_log" >&2
  return 1
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

assert_apphost_manifest_preserves_nextjs_frontend() {
  local manifest_path
  manifest_path="$(mktemp --suffix=.json)"

  dotnet run --project "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" -- --publisher manifest --output-path "$manifest_path" >/dev/null

  assert_file_contains "$manifest_path" '"api"'
  assert_file_contains "$manifest_path" '"frontend"'
  assert_file_contains "$manifest_path" "\"targetPort\": $ATRADE_APPHOST_FRONTEND_HTTP_PORT"
  assert_file_contains "$manifest_path" '"external": true'
  assert_file_contains "$manifest_path" '"PORT": "{frontend.bindings.http.targetPort}"'

  rm -f "$manifest_path"
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
  assert_file_contains "$repo_root/scripts/start.run.sh" 'atrade_load_local_port_contract'
  assert_file_contains "$repo_root/scripts/start.run.sh" 'ASPNETCORE_URLS="http://127.0.0.1:$aspire_dashboard_http_port"'
  assert_file_contains "$repo_root/scripts/start.run.sh" 'ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL:-http://127.0.0.1:0'
  assert_file_contains "$repo_root/scripts/start.run.sh" '--no-launch-profile -- "$@"'
  assert_file_contains "$repo_root/scripts/local-env.sh" 'ATRADE_PORT_CONTRACT_PATH'
  assert_file_not_contains "$repo_root/scripts/local-env.sh" 'local -A'
  assert_file_not_contains "$repo_root/scripts/local-env.sh" 'declare -A'
  assert_file_not_contains "$repo_root/scripts/local-env.sh" 'typeset -A'
  assert_file_contains "$repo_root/scripts/local-env.ps1" 'Import-ATradeLocalPortContract'
  assert_file_contains "$repo_root/scripts/local-env.ps1" 'ATRADE_PORT_CONTRACT_PATH'
  assert_file_not_contains "$repo_root/scripts/local-env.ps1" 'Write-Host'
  assert_file_not_contains "$repo_root/scripts/local-env.ps1" 'Write-Output'
  assert_file_contains "$repo_root/.env.template" 'ATRADE_APPHOST_FRONTEND_HTTP_PORT=3000'
  assert_file_contains "$repo_root/.env.template" 'ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=0'
  assert_file_contains "$repo_root/scripts/start.run.ps1" 'src/ATrade.AppHost/ATrade.AppHost.csproj'
  assert_file_contains "$repo_root/scripts/start.run.ps1" 'Import-ATradeLocalPortContract -RepoRoot $RepoRoot'
  assert_file_contains "$repo_root/scripts/start.run.ps1" '$env:ASPNETCORE_URLS = "http://127.0.0.1:$AspireDashboardHttpPort"'
  assert_file_contains "$repo_root/scripts/start.run.ps1" '$env:ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL = '\''http://127.0.0.1:0'\'''
  assert_file_contains "$repo_root/scripts/start.run.ps1" '--no-launch-profile -- @args'
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
  assert_file_contains "$repo_root/src/ATrade.Api/Program.cs" 'LocalDevelopmentPortContractLoader.ApplyApiHttpPortDefault(builder);'
  assert_file_contains "$repo_root/src/ATrade.Api/Program.cs" 'builder.AddServiceDefaults()'
  assert_file_contains "$repo_root/src/ATrade.Api/Program.cs" 'app.MapGet("/health", () => Results.Text("ok", "text/plain"));'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" 'Sdk="Microsoft.NET.Sdk"'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" '<Sdk Name="Aspire.AppHost.Sdk" Version="13.2.3" />'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" '<IsAspireHost>true</IsAspireHost>'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" 'Aspire.Hosting.JavaScript'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" 'ATrade.Api.csproj'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" 'ATrade.ServiceDefaults.csproj'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'LocalRuntimeContractLoader.Load()'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'LocalDevelopmentPortContractLoader.FromRuntimeContract(localRuntimeContract)'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'DistributedApplication.CreateBuilder(args)'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'AddProject<Projects.ATrade_Api>("api")'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'AddJavaScriptApp("frontend", localPortContract.FrontendDirectory, "dev")'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'WithHttpEndpoint(targetPort: localPortContract.AppHostFrontendHttpPort, env: "PORT")'
  assert_file_contains "$repo_root/frontend/package.json" '"dev": "next dev --hostname 0.0.0.0"'
  assert_file_contains "$repo_root/frontend/package.json" '"build": "next build"'
  assert_file_contains "$repo_root/frontend/package.json" '"start": "next start"'
  assert_file_contains "$repo_root/frontend/app/layout.tsx" "import './globals.css';"
  assert_file_contains "$repo_root/frontend/app/page.tsx" 'ATrade Frontend Home'
  assert_file_contains "$repo_root/frontend/app/page.tsx" 'Next.js Bootstrap Slice'
  assert_file_contains "$repo_root/frontend/app/page.tsx" 'Aspire AppHost Frontend Contract'
  assert_file_contains "$repo_root/frontend/next-env.d.ts" '/// <reference types="next" />'
  assert_file_contains "$repo_root/frontend/tsconfig.json" '"name": "next"'
  assert_file_not_exists "$repo_root/frontend/server.js"
  assert_file_contains "$repo_root/scripts/README.md" 'The `run` contract is now bootstrapped in the repository.'
  assert_file_contains "$repo_root/scripts/README.md" 'The Unix loader must stay compatible with Bash 3.2'
  assert_file_contains "$repo_root/scripts/README.md" './start run'
  assert_file_contains "$repo_root/scripts/README.md" 'are verified by GitHub Actions on `windows-latest` via `tests/start-contract/start-wrapper-windows.ps1`'
  assert_file_contains "$repo_root/README.md" 'Windows PowerShell: `./start.ps1 run`'
  assert_file_contains "$repo_root/README.md" 'Windows Command Prompt: `./start.cmd run`'
  assert_file_contains "$repo_root/PLAN.md" 'Keep the repo-local startup contract as `start run`'
  assert_file_not_exists "$repo_root/plans"

  assert_start_run_dispatches
  assert_start_run_script_failure_paths
  assert_local_env_loader_overlays_template_and_preserves_process_environment
  assert_start_run_script_loads_dashboard_port_contract
  assert_apphost_launch_profile_bootstraps_runtime
  assert_start_run_dashboard_port_smoke
  assert_apphost_manifest_preserves_nextjs_frontend
}

main "$@"
