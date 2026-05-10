param(
    [Parameter(Position = 0)]
    [string]$Action,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ComposeArgs
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ComposeFile = Join-Path $RepoRoot 'compose.yaml'

. (Join-Path $RepoRoot 'scripts/local-env.ps1')
Import-ATradeLocalPortContract -RepoRoot $RepoRoot

function Write-ATradeUsage {
    [Console]::Error.WriteLine('Usage: scripts/compose-infra.ps1 <up|down|config|ps|logs|pull|restart> [compose args...]')
    [Console]::Error.WriteLine('')
    [Console]::Error.WriteLine('Loads .env.template, overlays ignored .env, preserves process environment values,')
    [Console]::Error.WriteLine('selects Podman Compose by default with Docker Compose fallback, and runs against')
    [Console]::Error.WriteLine('the repo-owned compose.yaml. Set ATRADE_COMPOSE_DRY_RUN=true to print the')
    [Console]::Error.WriteLine('selected command without executing it.')
}

function Test-ATradeTruthy {
    param([string]$Value)

    $NormalizedValue = if ($null -eq $Value) { '' } else { $Value.Trim().ToLowerInvariant() }

    switch ($NormalizedValue) {
        '1' { return $true }
        'true' { return $true }
        'yes' { return $true }
        'y' { return $true }
        'on' { return $true }
        default { return $false }
    }
}

function Test-ATradeRealIbkrCredentials {
    if ([string]::IsNullOrWhiteSpace($env:ATRADE_IBKR_USERNAME)) { return $false }
    if ([string]::IsNullOrWhiteSpace($env:ATRADE_IBKR_PASSWORD)) { return $false }
    if ($env:ATRADE_IBKR_USERNAME -eq 'IBKR_USERNAME') { return $false }
    if ($env:ATRADE_IBKR_PASSWORD -eq 'IBKR_PASSWORD') { return $false }
    return $true
}

function Split-ATradeCommandLine {
    param([string]$CommandLine)

    return @($CommandLine.Trim() -split '\s+' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

function Select-ATradeComposeCommand {
    if (-not [string]::IsNullOrWhiteSpace($env:ATRADE_COMPOSE_COMMAND)) {
        return Split-ATradeCommandLine -CommandLine $env:ATRADE_COMPOSE_COMMAND
    }

    if (Get-Command podman -ErrorAction SilentlyContinue) {
        return @('podman', 'compose')
    }

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        return @('docker', 'compose')
    }

    throw 'ATrade Compose infrastructure requires Podman Compose or Docker Compose. Install Podman or Docker, or set ATRADE_COMPOSE_COMMAND to an exact Compose command.'
}

if (-not (Test-Path $ComposeFile)) {
    [Console]::Error.WriteLine("Missing Compose file at $ComposeFile")
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Action) -or $Action -in @('-h', '--help', 'help')) {
    Write-ATradeUsage
    exit 1
}

$SelectedComposeCommand = @(Select-ATradeComposeCommand)
$ComposeProjectName = if ([string]::IsNullOrWhiteSpace($env:ATRADE_COMPOSE_PROJECT_NAME)) { 'atrade' } else { $env:ATRADE_COMPOSE_PROJECT_NAME }
$BaseArgs = @('-f', $ComposeFile, '--project-name', $ComposeProjectName)
$ProfileArgs = @()

if ($Action -eq 'up') {
    if ((Test-ATradeTruthy $env:ATRADE_BROKER_INTEGRATION_ENABLED) -and (Test-ATradeRealIbkrCredentials)) {
        $ProfileArgs += @('--profile', 'ibkr')
    }

    $AnalysisEngine = if ([string]::IsNullOrWhiteSpace($env:ATRADE_ANALYSIS_ENGINE)) { 'none' } else { $env:ATRADE_ANALYSIS_ENGINE }
    $LeanRuntimeMode = if ([string]::IsNullOrWhiteSpace($env:ATRADE_LEAN_RUNTIME_MODE)) { 'cli' } else { $env:ATRADE_LEAN_RUNTIME_MODE }

    if ($AnalysisEngine -ieq 'Lean' -and $LeanRuntimeMode -ieq 'docker') {
        $ProfileArgs += @('--profile', 'lean')
    }

    $Subcommand = @('up', '-d')
}
else {
    $Subcommand = @($Action)
}

$CommandParts = @($SelectedComposeCommand + $BaseArgs + $ProfileArgs + $Subcommand + $ComposeArgs)

if (Test-ATradeTruthy $env:ATRADE_COMPOSE_DRY_RUN) {
    [Console]::Out.WriteLine(($CommandParts -join ' '))
    exit 0
}

$Executable = $SelectedComposeCommand[0]
$Arguments = @($CommandParts | Select-Object -Skip 1)
& $Executable @Arguments
exit $LASTEXITCODE
