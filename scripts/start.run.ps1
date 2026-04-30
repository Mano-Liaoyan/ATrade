$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ProjectPath = Join-Path $RepoRoot 'src/ATrade.AppHost/ATrade.AppHost.csproj'

. (Join-Path $RepoRoot 'scripts/local-env.ps1')
Import-ATradeLocalPortContract -RepoRoot $RepoRoot

$AspireDashboardHttpPort = if ([string]::IsNullOrWhiteSpace($env:ATRADE_ASPIRE_DASHBOARD_HTTP_PORT)) { '0' } else { $env:ATRADE_ASPIRE_DASHBOARD_HTTP_PORT }
$env:ASPNETCORE_URLS = "http://127.0.0.1:$AspireDashboardHttpPort"
if ([string]::IsNullOrWhiteSpace($env:ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL)) {
    $env:ASPIRE_DASHBOARD_OTLP_ENDPOINT_URL = 'http://127.0.0.1:0'
}
if ([string]::IsNullOrWhiteSpace($env:ASPIRE_ALLOW_UNSECURED_TRANSPORT)) {
    $env:ASPIRE_ALLOW_UNSECURED_TRANSPORT = 'true'
}

if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    [Console]::Error.WriteLine('dotnet is required to run the ATrade AppHost.')
    exit 1
}

if (-not (Test-Path $ProjectPath)) {
    [Console]::Error.WriteLine("Missing AppHost project at $ProjectPath")
    exit 1
}

& dotnet run --project $ProjectPath --no-launch-profile -- @args
exit $LASTEXITCODE
