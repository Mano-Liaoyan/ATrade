---
status: active
owner: devops
updated: 2026-04-22
summary: Implementation plan for the first `start run` bootstrap slice with thin wrappers, minimal Aspire AppHost, and a placeholder JavaScript frontend.
see_also:
  - docs/superpowers/specs/2026-04-22-start-run-bootstrap-design.md
  - scripts/README.md
  - plans/devops/CURRENT.md
---

# Start Run Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first real `start run` contract so Unix and Windows wrappers delegate to a minimal Aspire AppHost that manages a placeholder JavaScript frontend.

**Architecture:** Keep the startup surface thin and platform-specific only at the wrapper layer. Put orchestration in a hand-authored Aspire AppHost that uses `Aspire.Hosting.JavaScript` to run a minimal frontend process, with solution structure ready for later .NET services.

**Tech Stack:** Bash, Windows batch, PowerShell, .NET 10, xUnit, Aspire 13.2.3, Node.js, npm

---

## File Structure

- Create: `start`
  Responsibility: POSIX entrypoint that dispatches subcommands to `scripts/`.
- Create: `start.cmd`
  Responsibility: Windows Command Prompt entrypoint that dispatches subcommands to `scripts\`.
- Create: `start.ps1`
  Responsibility: PowerShell entrypoint that dispatches subcommands to `scripts/`.
- Create: `scripts/start.run.sh`
  Responsibility: POSIX `run` implementation that launches the AppHost project.
- Create: `scripts/start.run.ps1`
  Responsibility: PowerShell `run` implementation that launches the AppHost project.
- Create: `ATrade.sln`
  Responsibility: solution container for bootstrap .NET projects.
- Create: `src/ATrade.AppHost/ATrade.AppHost.csproj`
  Responsibility: Aspire AppHost project using `Aspire.AppHost.Sdk` and hosting packages.
- Create: `src/ATrade.AppHost/Program.cs`
  Responsibility: define the minimal distributed application graph.
- Create: `src/ATrade.AppHost/Properties/launchSettings.json`
  Responsibility: bootstrap the Aspire dashboard environment so direct `dotnet run` works without manual shell exports.
- Create: `src/ATrade.ServiceDefaults/ATrade.ServiceDefaults.csproj`
  Responsibility: placeholder shared .NET defaults project for future service scaffolding.
- Create: `src/ATrade.ServiceDefaults/Extensions.cs`
  Responsibility: minimal compile-safe placeholder extensions surface.
- Create: `frontend/package.json`
  Responsibility: placeholder frontend scripts for Aspire JavaScript hosting.
- Create: `frontend/server.js`
  Responsibility: simple HTTP server process for the frontend resource.
- Create: `tests/start-contract/start-wrapper-tests.sh`
  Responsibility: POSIX test harness for wrapper behavior and script paths.
- Modify: `scripts/README.md`
  Responsibility: update contract doc from design-only to bootstrap implementation status.
- Modify: `plans/devops/CURRENT.md`
  Responsibility: record progress and resume state after implementation.

### Task 1: Create Red-State Wrapper Harness

**Files:**
- Create: `tests/start-contract/start-wrapper-tests.sh`
- Test: `tests/start-contract/start-wrapper-tests.sh`

- [ ] **Step 1: Write the failing structural test**

```bash
#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

assert_file_exists() {
  local file_path="$1"

  if [[ ! -f "$file_path" ]]; then
    printf 'expected file to exist: %s\n' "$file_path" >&2
    return 1
  fi
}

assert_executable_exists() {
  local file_path="$1"

  assert_file_exists "$file_path"

  if [[ ! -x "$file_path" ]]; then
    printf 'expected file to be executable: %s\n' "$file_path" >&2
    return 1
  fi
}

main() {
  assert_executable_exists "$repo_root/start"
  assert_file_exists "$repo_root/start.ps1"
  assert_file_exists "$repo_root/start.cmd"
}

main "$@"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash tests/start-contract/start-wrapper-tests.sh`
Expected: FAIL because `start`, `start.ps1`, and `start.cmd` do not exist yet.

- [ ] **Step 3: Do not create production files in this task**

Leave the repository in the red state. This task only captures the missing contract before implementation exists.

- [ ] **Step 4: Confirm the failure is meaningful**

Run: `bash tests/start-contract/start-wrapper-tests.sh`
Expected: FAIL with a missing-file message for the first required wrapper path.

- [ ] **Step 5: Commit**

Do not commit after this task. The repository should still be red.

### Task 2: Implement Thin Wrapper Scripts And Runtime Contract

**Files:**
- Create: `start`
- Create: `start.ps1`
- Create: `start.cmd`
- Create: `scripts/start.run.sh`
- Create: `scripts/start.run.ps1`
- Test: `tests/start-contract/start-wrapper-tests.sh`

- [ ] **Step 1: Write the failing test for runtime behavior and dispatch**

Replace `tests/start-contract/start-wrapper-tests.sh` with this full content:

```bash
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

  if ! grep -Fq "$needle" "$file_path"; then
    printf 'expected %s to contain %s\n' "$file_path" "$needle" >&2
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
  output="$($@ 2>&1)"
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
  assert_file_contains "$repo_root/start.cmd" 'if "%COMMAND%"=="run"'
  assert_file_contains "$repo_root/start.cmd" 'powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*'
  assert_file_contains "$repo_root/scripts/start.run.sh" '#!/usr/bin/env bash'
  assert_file_contains "$repo_root/scripts/start.run.ps1" "\$ErrorActionPreference = 'Stop'"
  assert_file_contains "$repo_root/scripts/start.run.sh" 'src/ATrade.AppHost/ATrade.AppHost.csproj'
  assert_file_contains "$repo_root/scripts/start.run.ps1" 'src/ATrade.AppHost/ATrade.AppHost.csproj'

  assert_start_run_dispatches
}

main "$@"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash tests/start-contract/start-wrapper-tests.sh`
Expected: FAIL because the wrappers do not yet contain the required dispatch logic.

- [ ] **Step 3: Write minimal implementation**

Create `start` with this content:

```bash
#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command_name="${1:-}"

usage() {
  printf 'Usage: ./start run\n' >&2
}

case "$command_name" in
  run)
    shift
    exec "$repo_root/scripts/start.run.sh" "$@"
    ;;
  "")
    usage
    exit 1
    ;;
  *)
    printf 'Unsupported command: %s\n' "$command_name" >&2
    usage
    exit 1
    ;;
esac
```

Create `start.ps1` with this content:

```powershell
$ErrorActionPreference = 'Stop'

$Command = if ($args.Count -gt 0) { $args[0] } else { '' }
$Remaining = if ($args.Count -gt 1) { $args[1..($args.Count - 1)] } else { @() }

function Show-Usage {
    [Console]::Error.WriteLine('Usage: ./start.ps1 run')
}

switch ($Command) {
    'run' {
        & "$PSScriptRoot/scripts/start.run.ps1" @Remaining
        exit $LASTEXITCODE
    }
    '' {
        Show-Usage
        exit 1
    }
    default {
        [Console]::Error.WriteLine("Unsupported command: $Command")
        Show-Usage
        exit 1
    }
}
```

Create `start.cmd` with this content:

```bat
@echo off
setlocal

set "COMMAND=%~1"
if "%COMMAND%"=="" goto :usage

if "%COMMAND%"=="run" (
  shift
  powershell -ExecutionPolicy Bypass -File "%~dp0scripts\start.run.ps1" %*
  exit /b %ERRORLEVEL%
)

>&2 echo Unsupported command: %COMMAND%
goto :usage

:usage
>&2 echo Usage: ./start.cmd run
exit /b 1
```

Create `scripts/start.run.sh` with this content:

```bash
#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_path="$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj"

if ! command -v dotnet >/dev/null 2>&1; then
  printf 'dotnet is required to run the ATrade AppHost.\n' >&2
  exit 1
fi

if [[ ! -f "$project_path" ]]; then
  printf 'Missing AppHost project at %s\n' "$project_path" >&2
  exit 1
fi

exec dotnet run --project "$project_path" -- "$@"
```

Create `scripts/start.run.ps1` with this content:

```powershell
$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$ProjectPath = Join-Path $RepoRoot 'src/ATrade.AppHost/ATrade.AppHost.csproj'

if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    [Console]::Error.WriteLine('dotnet is required to run the ATrade AppHost.')
    exit 1
}

if (-not (Test-Path $ProjectPath)) {
    [Console]::Error.WriteLine("Missing AppHost project at $ProjectPath")
    exit 1
}

& dotnet run --project $ProjectPath -- @args
exit $LASTEXITCODE
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash tests/start-contract/start-wrapper-tests.sh`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/start-contract/start-wrapper-tests.sh start start.ps1 start.cmd scripts/start.run.sh scripts/start.run.ps1
git commit -m "feat: add start run wrapper contract"
```

### Task 3: Scaffold the Solution and Minimal AppHost

**Files:**
- Create: `ATrade.sln`
- Create: `src/ATrade.AppHost/ATrade.AppHost.csproj`
- Create: `src/ATrade.AppHost/Program.cs`
- Create: `src/ATrade.AppHost/Properties/launchSettings.json`
- Create: `src/ATrade.ServiceDefaults/ATrade.ServiceDefaults.csproj`
- Create: `src/ATrade.ServiceDefaults/Extensions.cs`

- [ ] **Step 1: Write the failing test for AppHost project presence**

Append the following lines to `tests/start-contract/start-wrapper-tests.sh` inside `main()`:

```bash
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" 'Sdk="Microsoft.NET.Sdk"'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" '<Sdk Name="Aspire.AppHost.Sdk" Version="13.2.3" />'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" '<IsAspireHost>true</IsAspireHost>'
  assert_file_contains "$repo_root/src/ATrade.AppHost/ATrade.AppHost.csproj" 'Aspire.Hosting.JavaScript'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'DistributedApplication.CreateBuilder(args)'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Program.cs" 'AddJavaScriptApp("frontend", "../../frontend", "dev")'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Properties/launchSettings.json" '"ASPNETCORE_URLS": "http://127.0.0.1:0"'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Properties/launchSettings.json" '"ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL": "http://127.0.0.1:0"'
  assert_file_contains "$repo_root/src/ATrade.AppHost/Properties/launchSettings.json" '"ASPIRE_ALLOW_UNSECURED_TRANSPORT": "true"'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash tests/start-contract/start-wrapper-tests.sh`
Expected: FAIL because the AppHost and solution files do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Run:

```bash
dotnet new sln -n ATrade
mkdir -p src/ATrade.AppHost src/ATrade.ServiceDefaults
```

Create `src/ATrade.AppHost/ATrade.AppHost.csproj` with this content:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <Sdk Name="Aspire.AppHost.Sdk" Version="13.2.3" />

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsAspireHost>true</IsAspireHost>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Aspire.Hosting.AppHost" Version="13.2.3" />
    <PackageReference Include="Aspire.Hosting.JavaScript" Version="13.2.3" />
  </ItemGroup>
</Project>
```

Create `src/ATrade.AppHost/Program.cs` with this content:

```csharp
using Aspire.Hosting;
using Aspire.Hosting.JavaScript;

var builder = DistributedApplication.CreateBuilder(args);

builder.AddJavaScriptApp("frontend", "../../frontend", "dev")
    .WithNpm()
    .WithHttpEndpoint(targetPort: 3000, env: "PORT")
    .WithExternalHttpEndpoints();

builder.Build().Run();
```

Create `src/ATrade.AppHost/Properties/launchSettings.json` with this content:

```json
{
  "$schema": "https://json.schemastore.org/launchsettings.json",
  "profiles": {
    "ATrade.AppHost": {
      "commandName": "Project",
      "environmentVariables": {
        "ASPNETCORE_URLS": "http://127.0.0.1:0",
        "ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL": "http://127.0.0.1:0",
        "ASPIRE_ALLOW_UNSECURED_TRANSPORT": "true"
      }
    }
  }
}
```

Create `src/ATrade.ServiceDefaults/ATrade.ServiceDefaults.csproj` with this content:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
</Project>
```

Create `src/ATrade.ServiceDefaults/Extensions.cs` with this content:

```csharp
namespace ATrade.ServiceDefaults;

public static class Extensions
{
}
```

Run:

```bash
dotnet sln ATrade.sln add src/ATrade.AppHost/ATrade.AppHost.csproj src/ATrade.ServiceDefaults/ATrade.ServiceDefaults.csproj
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash tests/start-contract/start-wrapper-tests.sh`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ATrade.sln src/ATrade.AppHost/ATrade.AppHost.csproj src/ATrade.AppHost/Program.cs src/ATrade.ServiceDefaults/ATrade.ServiceDefaults.csproj src/ATrade.ServiceDefaults/Extensions.cs tests/start-contract/start-wrapper-tests.sh
git commit -m "feat: add minimal aspire apphost bootstrap"
```

### Task 4: Add Placeholder Frontend and Verify the Graph Builds

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/server.js`

- [ ] **Step 1: Write the failing test for frontend contract files**

Append the following lines to `tests/start-contract/start-wrapper-tests.sh` inside `main()`:

```bash
  assert_file_contains "$repo_root/frontend/package.json" '"dev": "node server.js"'
  assert_file_contains "$repo_root/frontend/server.js" 'const port = Number(process.env.PORT ?? 3000);'
  assert_file_contains "$repo_root/frontend/server.js" 'ATrade frontend bootstrap'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash tests/start-contract/start-wrapper-tests.sh`
Expected: FAIL because the frontend files do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/package.json` with this content:

```json
{
  "name": "atrade-frontend",
  "private": true,
  "version": "0.0.0",
  "scripts": {
    "dev": "node server.js"
  }
}
```

Create `frontend/server.js` with this content:

```javascript
const http = require('node:http');

const port = Number(process.env.PORT ?? 3000);

const server = http.createServer((_, response) => {
  response.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
  response.end('ATrade frontend bootstrap\n');
});

server.listen(port, () => {
  process.stdout.write(`frontend listening on ${port}\n`);
});
```

- [ ] **Step 4: Run tests and build verification**

Run: `bash tests/start-contract/start-wrapper-tests.sh`
Expected: PASS

Run: `dotnet build ATrade.sln`
Expected: BUILD SUCCEEDED

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/server.js tests/start-contract/start-wrapper-tests.sh
git commit -m "feat: add frontend placeholder for start run"
```

### Task 5: Verify `start run` and Update Documentation

**Files:**
- Modify: `scripts/README.md`
- Modify: `plans/devops/CURRENT.md`

- [ ] **Step 1: Write the failing test for implementation-status docs**

Append the following lines to `tests/start-contract/start-wrapper-tests.sh` inside `main()`:

```bash
  assert_file_contains "$repo_root/scripts/README.md" 'The `run` contract is now bootstrapped in the repository.'
  assert_file_contains "$repo_root/scripts/README.md" './start run'
  assert_file_contains "$repo_root/plans/devops/CURRENT.md" 'Implement the `start run` cross-platform script contract'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash tests/start-contract/start-wrapper-tests.sh`
Expected: FAIL because `scripts/README.md` still says the scripts are not implemented.

- [ ] **Step 3: Write minimal implementation**

Update the final section of `scripts/README.md` so it reads:

```markdown
## Bootstrap Status

The `run` contract is now bootstrapped in the repository.

- `./start run` delegates to the Aspire AppHost
- `./start.ps1 run` provides the PowerShell entrypoint
- `./start.cmd run` provides the Windows command prompt entrypoint
- the current graph is intentionally minimal and hosts a placeholder JavaScript frontend

Reserved subcommands such as `test`, `build`, and `lint` remain future work.
```

Update `plans/devops/CURRENT.md` so the checklist reflects progress:

```markdown
## Active Checklist

- [x] ~~Create the first baseline commit for the repository~~
- [x] ~~Implement the `start run` cross-platform script contract~~
- [ ] Add Aspire AppHost orchestration for .NET services, Next.js, and infra containers
- [ ] Establish GitHub Actions and labels for autonomous coordination

## Resume From Here

- Extend the bootstrap AppHost from the placeholder frontend graph to real .NET services and infrastructure resources
```

- [ ] **Step 4: Run full verification**

Run: `bash tests/start-contract/start-wrapper-tests.sh`
Expected: PASS

Run: `dotnet build ATrade.sln`
Expected: BUILD SUCCEEDED

Run: `./start run`
Expected: the AppHost starts and manages the frontend resource; stop it manually after confirming startup output.

- [ ] **Step 5: Commit**

```bash
git add scripts/README.md plans/devops/CURRENT.md
git commit -m "docs: record start run bootstrap status"
```
