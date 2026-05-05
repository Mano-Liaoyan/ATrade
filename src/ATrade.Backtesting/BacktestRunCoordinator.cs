using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace ATrade.Backtesting;

public sealed class BacktestRunCoordinatorOptions
{
    public bool Enabled { get; set; } = true;

    public TimeSpan PollInterval { get; set; } = TimeSpan.FromSeconds(5);
}

public interface IBacktestRunCoordinator
{
    Task<int> RecoverInterruptedRunsAsync(CancellationToken cancellationToken = default);

    Task<bool> ProcessNextQueuedRunAsync(CancellationToken cancellationToken = default);
}

public sealed class BacktestRunCoordinator(
    IBacktestRunSchemaInitializer schemaInitializer,
    IBacktestRunRepository runRepository,
    IBacktestRunExecutionPipeline executionPipeline,
    ILogger<BacktestRunCoordinator> logger) : IBacktestRunCoordinator
{
    public async Task<int> RecoverInterruptedRunsAsync(CancellationToken cancellationToken = default)
    {
        await schemaInitializer.InitializeAsync(cancellationToken).ConfigureAwait(false);
        var recovered = await runRepository.FailInterruptedRunningAsync(
            new BacktestError(BacktestErrorCodes.RunInterrupted, BacktestSafeMessages.RunInterrupted),
            cancellationToken).ConfigureAwait(false);

        if (recovered > 0)
        {
            logger.LogWarning("Marked {BacktestRunCount} interrupted backtest run(s) as failed during startup recovery.", recovered);
        }

        return recovered;
    }

    public async Task<bool> ProcessNextQueuedRunAsync(CancellationToken cancellationToken = default)
    {
        await schemaInitializer.InitializeAsync(cancellationToken).ConfigureAwait(false);
        var claimed = await runRepository.ClaimNextQueuedAsync(cancellationToken).ConfigureAwait(false);
        if (claimed is null)
        {
            return false;
        }

        var executionResult = await ExecuteSafelyAsync(claimed, cancellationToken).ConfigureAwait(false);
        var terminalResult = NormalizeTerminalExecutionResult(executionResult);

        await runRepository.UpdateStatusAsync(
            claimed.Scope,
            claimed.Run.Id,
            terminalResult.Status,
            terminalResult.Error,
            terminalResult.Result,
            cancellationToken).ConfigureAwait(false);

        return true;
    }

    private async Task<BacktestRunExecutionResult> ExecuteSafelyAsync(
        BacktestRunRecord claimed,
        CancellationToken cancellationToken)
    {
        try
        {
            return await executionPipeline.ExecuteAsync(claimed, cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception exception)
        {
            logger.LogError(exception, "Backtest run {BacktestRunId} failed during execution.", claimed.Run.Id);
            return BacktestRunExecutionResult.Failed(
                BacktestErrorCodes.RunnerFailed,
                BacktestSafeMessages.RunnerFailed);
        }
    }

    private static BacktestRunExecutionResult NormalizeTerminalExecutionResult(BacktestRunExecutionResult? result)
    {
        if (result is null || !BacktestRunStatuses.IsTerminal(result.Status))
        {
            return BacktestRunExecutionResult.Failed(
                BacktestErrorCodes.RunnerFailed,
                BacktestSafeMessages.RunnerFailed);
        }

        if (string.Equals(result.Status, BacktestRunStatuses.Completed, StringComparison.OrdinalIgnoreCase))
        {
            return BacktestRunExecutionResult.Completed(result.Result);
        }

        var safeError = BacktestPersistenceSafety.NormalizeSafeError(result.Error) ?? new BacktestError(
            BacktestErrorCodes.RunnerFailed,
            BacktestSafeMessages.RunnerFailed);

        return new BacktestRunExecutionResult(result.Status.Trim().ToLowerInvariant(), safeError, null);
    }
}

public sealed class BacktestRunHostedService(
    IBacktestRunCoordinator coordinator,
    IOptions<BacktestRunCoordinatorOptions> options,
    ILogger<BacktestRunHostedService> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var configuredOptions = options.Value;
        if (!configuredOptions.Enabled)
        {
            logger.LogInformation("Backtest run hosted service is disabled by configuration.");
            return;
        }

        await RecoverOnStartupAsync(stoppingToken).ConfigureAwait(false);

        while (!stoppingToken.IsCancellationRequested)
        {
            await DrainQueuedRunsAsync(stoppingToken).ConfigureAwait(false);
            await DelayAsync(configuredOptions.PollInterval, stoppingToken).ConfigureAwait(false);
        }
    }

    private async Task RecoverOnStartupAsync(CancellationToken stoppingToken)
    {
        try
        {
            await coordinator.RecoverInterruptedRunsAsync(stoppingToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
        {
        }
        catch (Exception exception)
        {
            logger.LogError(exception, "Backtest runner startup recovery failed; queued runs will be retried on the next service tick.");
        }
    }

    private async Task DrainQueuedRunsAsync(CancellationToken stoppingToken)
    {
        try
        {
            while (!stoppingToken.IsCancellationRequested && await coordinator.ProcessNextQueuedRunAsync(stoppingToken).ConfigureAwait(false))
            {
            }
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
        {
        }
        catch (Exception exception)
        {
            logger.LogError(exception, "Backtest runner tick failed; queued runs will be retried on the next service tick.");
        }
    }

    private static async Task DelayAsync(TimeSpan pollInterval, CancellationToken stoppingToken)
    {
        var safePollInterval = pollInterval <= TimeSpan.Zero ? TimeSpan.FromSeconds(5) : pollInterval;
        await Task.Delay(safePollInterval, stoppingToken).ConfigureAwait(false);
    }
}
