Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SuccessMarker = 'Distributed application started. Press Ctrl+C to shut down.'
$StartupTimeoutSeconds = 120
$PollIntervalMilliseconds = 1000
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..' '..')).Path
$ArtifactRoot = Join-Path ([System.IO.Path]::GetTempPath()) 'atrade-start-contract'

New-Item -ItemType Directory -Force -Path $ArtifactRoot | Out-Null

function Get-LogText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return ''
    }

    return [System.IO.File]::ReadAllText($Path)
}

function Get-CombinedOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StandardOutputPath,

        [Parameter(Mandatory = $true)]
        [string]$StandardErrorPath
    )

    $stdout = Get-LogText -Path $StandardOutputPath
    $stderr = Get-LogText -Path $StandardErrorPath

    return @($stdout, $stderr) -join [Environment]::NewLine
}

function Assert-FileContains {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Needle
    )

    if (-not (Test-Path $Path)) {
        throw "Expected file to exist: $Path"
    }

    $text = [System.IO.File]::ReadAllText($Path)
    if (-not $text.Contains($Needle)) {
        throw "Expected $Path to contain $Needle"
    }
}

function Assert-WrapperContractFiles {
    $runScriptPath = Join-Path $RepoRoot 'scripts/start.run.ps1'
    $envLoaderPath = Join-Path $RepoRoot 'scripts/local-env.ps1'
    $templatePath = Join-Path $RepoRoot '.env.template'

    Assert-FileContains -Path $runScriptPath -Needle 'Import-ATradeLocalPortContract -RepoRoot $RepoRoot'
    Assert-FileContains -Path $runScriptPath -Needle '$env:ASPNETCORE_URLS = "http://127.0.0.1:$AspireDashboardHttpPort"'
    Assert-FileContains -Path $runScriptPath -Needle '--no-launch-profile -- @args'
    Assert-FileContains -Path $envLoaderPath -Needle 'ATRADE_PORT_CONTRACT_PATH'
    Assert-FileContains -Path $templatePath -Needle 'ATRADE_ASPIRE_DASHBOARD_HTTP_PORT=0'
}

function Stop-ProcessTree {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId,

        [Parameter(Mandatory = $true)]
        [string]$CommandText
    )

    Write-Host "==> Stopping $CommandText (PID $ProcessId)"

    $taskKill = Start-Process -FilePath 'taskkill.exe' -ArgumentList @('/PID', $ProcessId, '/T', '/F') -NoNewWindow -PassThru -Wait
    if ($taskKill.ExitCode -ne 0 -and $taskKill.ExitCode -ne 128) {
        throw "taskkill failed for $CommandText with exit code $($taskKill.ExitCode)."
    }
}

function Invoke-WrapperSmoke {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$CommandText
    )

    $scenarioRoot = Join-Path $ArtifactRoot $Name
    if (Test-Path $scenarioRoot) {
        Remove-Item -Recurse -Force $scenarioRoot
    }

    New-Item -ItemType Directory -Force -Path $scenarioRoot | Out-Null

    $standardOutputPath = Join-Path $scenarioRoot 'stdout.log'
    $standardErrorPath = Join-Path $scenarioRoot 'stderr.log'
    $process = $null

    try {
        Write-Host "==> Starting $CommandText"

        $process = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', "& { $CommandText }") -WorkingDirectory $RepoRoot -RedirectStandardOutput $standardOutputPath -RedirectStandardError $standardErrorPath -PassThru

        $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)

        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds $PollIntervalMilliseconds
            $process.Refresh()

            $combinedOutput = Get-CombinedOutput -StandardOutputPath $standardOutputPath -StandardErrorPath $standardErrorPath
            if ($combinedOutput.Contains($SuccessMarker)) {
                Write-Host "==> Startup marker observed for $CommandText"
                return
            }

            if ($process.HasExited) {
                throw "$CommandText exited with code $($process.ExitCode) before reaching the startup marker.`n$combinedOutput"
            }
        }

        $timeoutOutput = Get-CombinedOutput -StandardOutputPath $standardOutputPath -StandardErrorPath $standardErrorPath
        throw "$CommandText did not reach the startup marker within $StartupTimeoutSeconds seconds.`n$timeoutOutput"
    }
    finally {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-ProcessTree -ProcessId $process.Id -CommandText $CommandText
            Start-Sleep -Seconds 2
        }
    }
}

Push-Location $RepoRoot
try {
    Assert-WrapperContractFiles
    Invoke-WrapperSmoke -Name 'start-ps1' -CommandText './start.ps1 run'
    Invoke-WrapperSmoke -Name 'start-cmd' -CommandText './start.cmd run'

    Write-Host 'Windows wrapper smoke verification completed successfully.'
}
finally {
    Pop-Location
}
