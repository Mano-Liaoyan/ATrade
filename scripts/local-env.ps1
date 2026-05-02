function Import-ATradeLocalPortContract {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $preferredPath = Join-Path $RepoRoot '.env'
    $fallbackPath = Join-Path $RepoRoot '.env.template'
    $contractPath = $fallbackPath
    $contractFiles = @()

    if (Test-Path $preferredPath) {
        $contractPath = $preferredPath
    }

    if (Test-Path $fallbackPath) {
        $contractFiles += $fallbackPath
    }

    if (Test-Path $preferredPath) {
        $contractFiles += $preferredPath
    }

    if ($contractFiles.Count -eq 0) {
        throw "Missing local port contract file at $fallbackPath"
    }

    $env:ATRADE_REPO_ROOT = $RepoRoot
    $env:ATRADE_PORT_CONTRACT_PATH = $contractPath

    $contractValues = @{}

    foreach ($filePath in $contractFiles) {
        foreach ($rawLine in [System.IO.File]::ReadLines($filePath)) {
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

            $contractValues[$key] = $value
        }
    }

    foreach ($entry in $contractValues.GetEnumerator()) {
        if ($null -eq [System.Environment]::GetEnvironmentVariable($entry.Key, [System.EnvironmentVariableTarget]::Process)) {
            [System.Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, [System.EnvironmentVariableTarget]::Process)
        }
    }
}
