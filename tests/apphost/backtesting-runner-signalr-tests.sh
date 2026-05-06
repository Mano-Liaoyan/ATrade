#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

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

assert_file_not_contains_regex() {
  local file_path="$1"
  local pattern="$2"

  if grep -Eiq -- "$pattern" "$file_path"; then
    printf 'expected %s not to match sensitive pattern %s\n' "$file_path" "$pattern" >&2
    grep -Ein -- "$pattern" "$file_path" >&2 || true
    return 1
  fi
}

main() {
  local api_program="$repo_root/src/ATrade.Api/Program.cs"
  local backtesting_project="$repo_root/src/ATrade.Backtesting/ATrade.Backtesting.csproj"
  local module_extensions="$repo_root/src/ATrade.Backtesting/BacktestingModuleServiceCollectionExtensions.cs"
  local coordinator="$repo_root/src/ATrade.Backtesting/BacktestRunCoordinator.cs"
  local cancellation="$repo_root/src/ATrade.Backtesting/BacktestRunCancellation.cs"
  local hub="$repo_root/src/ATrade.Backtesting/BacktestRunsHub.cs"
  local pipeline="$repo_root/src/ATrade.Backtesting/BacktestRunAnalysisExecutionPipeline.cs"
  local tests="$repo_root/tests/ATrade.Backtesting.Tests/BacktestRunSignalRTests.cs"

  assert_file_contains "$api_program" 'builder.Services.AddSignalR();'
  assert_file_contains "$api_program" 'app.MapHub<BacktestRunsHub>("/hubs/backtests");'
  assert_file_contains "$api_program" 'IBacktestRunCancellationRegistry cancellationRegistry'
  assert_file_contains "$api_program" 'cancellationRegistry.RequestCancellation(id);'
  assert_file_contains "$api_program" 'IBacktestRunUpdatePublisher runUpdatePublisher'
  assert_file_contains "$api_program" 'BacktestRunUpdateEvents.RunCreated'
  assert_file_contains "$api_program" 'BacktestRunUpdateEvents.RunCancelled'
  assert_file_contains "$api_program" 'SignalR updates are best-effort; persisted HTTP state remains authoritative.'

  assert_file_contains "$backtesting_project" 'ATrade.Analysis.csproj'
  assert_file_contains "$backtesting_project" 'ATrade.MarketData.csproj'
  assert_file_contains "$module_extensions" 'AddHostedService<BacktestRunHostedService>()'
  assert_file_contains "$module_extensions" 'IBacktestRunCancellationRegistry, BacktestRunCancellationRegistry'
  assert_file_contains "$module_extensions" 'IBacktestRunUpdatePublisher, SignalRBacktestRunUpdatePublisher'
  assert_file_contains "$module_extensions" 'IBacktestRunExecutionPipeline, BacktestRunAnalysisExecutionPipeline'

  assert_file_contains "$coordinator" 'RegisterRunningRun(claimed.Run.Id, cancellationToken)'
  assert_file_contains "$coordinator" 'BacktestRunExecutionResult.Cancelled()'
  assert_file_contains "$coordinator" 'BacktestRunUpdateEvents.StatusChanged'
  assert_file_contains "$coordinator" 'BacktestRunUpdateEvents.ForRunStatus(updated.Run.Status)'
  assert_file_contains "$cancellation" 'ConcurrentDictionary<string, CancellationTokenSource>'
  assert_file_contains "$cancellation" 'RequestCancellation(string runId)'
  assert_file_contains "$pipeline" 'GetCandlesAsync(request.Symbol.Symbol, request.ChartRange, request.Symbol, cancellationToken)'
  assert_file_contains "$pipeline" 'analysisEngines.AnalyzeAsync(analysisRequest, cancellationToken)'

  assert_file_contains "$hub" 'public sealed class BacktestRunsHub : Hub'
  assert_file_contains "$hub" 'BacktestRunUpdatePayload'
  assert_file_contains "$hub" 'RunCreated = "backtestRunCreated"'
  assert_file_contains "$hub" 'RunCompleted = "backtestRunCompleted"'
  assert_file_contains "$hub" 'RunFailed = "backtestRunFailed"'
  assert_file_contains "$hub" 'RunCancelled = "backtestRunCancelled"'
  assert_file_contains "$hub" 'hubContext.Clients.All.SendAsync(eventName, payload, cancellationToken)'
  assert_file_contains "$hub" 'BacktestPersistenceSafety.NormalizeSafeError'
  assert_file_contains "$hub" 'BacktestPersistenceSafety.SerializeResult'
  assert_file_not_contains_regex "$hub" 'account|credential|password|secret|(^|[^[:alnum:]_])token([^[:alnum:]_]|$)|cookie|session|gateway|https?://|workspace|command line|docker exec|capital'

  assert_file_contains "$tests" 'BacktestRunUpdatePayload_ContainsSafeStatusResultAndErrorShapeOnly'
  assert_file_contains "$tests" 'DoesNotContain("capital"'
  assert_file_contains "$repo_root/tests/ATrade.Backtesting.Tests/BacktestRunCoordinatorTests.cs" 'ProcessNextQueuedRunAsync_CancelsRunningPipelineThroughRunnerOwnedToken'

  dotnet build "$repo_root/src/ATrade.Api/ATrade.Api.csproj" --nologo --verbosity minimal >/dev/null
  printf 'Backtesting runner/SignalR source and apphost build validation passed.\n'
}

main "$@"
