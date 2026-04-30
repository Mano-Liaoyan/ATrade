function Import-ATradeLocalPortContract {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $preferredPath = Join-Path $RepoRoot '.env'
    $fallbackPath = Join-Path $RepoRoot '.env.template'
    $contractPath = $fallbackPath

    if (Test-Path $preferredPath) {
        $contractPath = $preferredPath
    }

    if (-not (Test-Path $contractPath)) {
        throw "Missing local port contract file at $contractPath"
    }

    $env:ATRADE_REPO_ROOT = $RepoRoot
    $env:ATRADE_PORT_CONTRACT_PATH = $contractPath

    foreach ($rawLine in [System.IO.File]::ReadLines($contractPath)) {
        $line = $rawLine.Trim()
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) {
            continue
        }

        $separatorIndex = $line.IndexOf('=')
        if ($separatorIndex -le 0) {
            continue
        }

        $key = $line.Substring(0, $separatorIndex).Trim() -replace "[\t\r ]", ''
        $value = $line.Substring($separatorIndex + 1).Trim().Trim('"', "'")

        if ([string]::IsNullOrWhiteSpace($key)) {
            continue
        }

        if ($null -eq [System.Environment]::GetEnvironmentVariable($key, [System.EnvironmentVariableTarget]::Process)) {
            [System.Environment]::SetEnvironmentVariable($key, $value, [System.EnvironmentVariableTarget]::Process)
        }
    }
}
