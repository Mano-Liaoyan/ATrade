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
