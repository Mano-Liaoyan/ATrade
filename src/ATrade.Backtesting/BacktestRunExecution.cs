using System.Text.Json;

namespace ATrade.Backtesting;

public interface IBacktestRunExecutionPipeline
{
    Task<BacktestRunExecutionResult> ExecuteAsync(BacktestRunRecord run, CancellationToken cancellationToken = default);
}

public sealed record BacktestRunExecutionResult(string Status, BacktestError? Error, JsonElement? Result)
{
    public static BacktestRunExecutionResult Completed(JsonElement? result = null) =>
        new(BacktestRunStatuses.Completed, null, result);

    public static BacktestRunExecutionResult Failed(string code, string message) =>
        new(BacktestRunStatuses.Failed, new BacktestError(code, message), null);
}

public sealed class UnavailableBacktestRunExecutionPipeline : IBacktestRunExecutionPipeline
{
    public Task<BacktestRunExecutionResult> ExecuteAsync(
        BacktestRunRecord run,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(run);
        cancellationToken.ThrowIfCancellationRequested();

        return Task.FromResult(BacktestRunExecutionResult.Failed(
            BacktestErrorCodes.RunnerUnavailable,
            BacktestSafeMessages.RunnerUnavailable));
    }
}
