namespace ATrade.Ibkr.Worker;

public sealed class IbkrWorkerShell(ILogger<IbkrWorkerShell> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        logger.LogInformation("ATrade.Ibkr.Worker shell is running without broker integrations.");

        try
        {
            await Task.Delay(Timeout.InfiniteTimeSpan, stoppingToken);
        }
        catch (OperationCanceledException)
        {
        }
    }
}
