using ATrade.Brokers.Ibkr;

namespace ATrade.Ibkr.Worker;

public sealed class IbkrWorkerShell(
    IIbkrBrokerStatusService brokerStatusService,
    ILogger<IbkrWorkerShell> logger) : BackgroundService
{
    private static readonly TimeSpan StatusPollInterval = TimeSpan.FromSeconds(30);

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var previousState = string.Empty;

        while (!stoppingToken.IsCancellationRequested)
        {
            var status = await brokerStatusService.GetStatusAsync(stoppingToken);

            if (!string.Equals(previousState, status.State, StringComparison.OrdinalIgnoreCase))
            {
                LogStatus(status);
                previousState = status.State;
            }

            if (string.Equals(status.State, "rejected-live-mode", StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException(status.Message ?? "ATrade.Ibkr.Worker rejects non-paper IBKR modes.");
            }

            if (string.Equals(status.State, "disabled", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(status.State, "not-configured", StringComparison.OrdinalIgnoreCase))
            {
                await WaitUntilStoppedAsync(stoppingToken);
                return;
            }

            await Task.Delay(StatusPollInterval, stoppingToken);
        }
    }

    private void LogStatus(IbkrBrokerStatus status)
    {
        switch (status.State)
        {
            case "disabled":
                logger.LogInformation("ATrade.Ibkr.Worker is disabled and will remain idle until local configuration enables paper mode.");
                break;
            case "not-configured":
                logger.LogWarning("ATrade.Ibkr.Worker is enabled for paper mode but not fully configured yet: {Message}", status.Message);
                break;
            case "rejected-live-mode":
                logger.LogCritical("ATrade.Ibkr.Worker rejected an unsafe IBKR configuration: {Message}", status.Message);
                break;
            case "authenticated":
                logger.LogInformation("ATrade.Ibkr.Worker confirmed an authenticated paper IBKR Gateway session.");
                break;
            case "connecting":
                logger.LogInformation("ATrade.Ibkr.Worker is attempting to reach the paper IBKR Gateway session endpoint.");
                break;
            case "degraded":
                logger.LogWarning("ATrade.Ibkr.Worker reached the paper IBKR Gateway but the session is degraded: {Message}", status.Message);
                break;
            case "error":
                logger.LogWarning("ATrade.Ibkr.Worker could not read the paper IBKR Gateway status safely: {Message}", status.Message);
                break;
            default:
                logger.LogInformation("ATrade.Ibkr.Worker observed IBKR state {State}.", status.State);
                break;
        }
    }

    private static async Task WaitUntilStoppedAsync(CancellationToken stoppingToken)
    {
        try
        {
            await Task.Delay(Timeout.InfiniteTimeSpan, stoppingToken);
        }
        catch (OperationCanceledException)
        {
        }
    }
}
