using ATrade.Brokers.Ibkr;

namespace ATrade.Ibkr.Worker;

public sealed class IbkrWorkerShell(
    IIbkrSessionReadinessService readinessService,
    ILogger<IbkrWorkerShell> logger) : BackgroundService
{
    private static readonly TimeSpan StatusPollInterval = TimeSpan.FromSeconds(30);

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var previousState = string.Empty;

        while (!stoppingToken.IsCancellationRequested)
        {
            var readiness = await readinessService.CheckReadinessAsync(stoppingToken);

            if (!string.Equals(previousState, readiness.State, StringComparison.OrdinalIgnoreCase))
            {
                LogStatus(readiness);
                previousState = readiness.State;
            }

            if (string.Equals(readiness.State, IbkrSessionReadinessStates.RejectedLiveMode, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException(readiness.Message ?? "ATrade.Ibkr.Worker rejects non-paper IBKR modes.");
            }

            if (string.Equals(readiness.State, IbkrSessionReadinessStates.Disabled, StringComparison.OrdinalIgnoreCase) ||
                string.Equals(readiness.State, IbkrSessionReadinessStates.NotConfigured, StringComparison.OrdinalIgnoreCase) ||
                string.Equals(readiness.State, IbkrSessionReadinessStates.CredentialsMissing, StringComparison.OrdinalIgnoreCase))
            {
                await WaitUntilStoppedAsync(stoppingToken);
                return;
            }

            await Task.Delay(StatusPollInterval, stoppingToken);
        }
    }

    private void LogStatus(IbkrSessionReadinessResult readiness)
    {
        switch (readiness.State)
        {
            case IbkrSessionReadinessStates.Disabled:
                logger.LogInformation("ATrade.Ibkr.Worker is disabled and will remain idle until local configuration enables paper mode.");
                break;
            case IbkrSessionReadinessStates.NotConfigured:
                logger.LogWarning("ATrade.Ibkr.Worker is enabled for paper mode but not fully configured yet: {Message}", readiness.Message);
                break;
            case IbkrSessionReadinessStates.CredentialsMissing:
                logger.LogWarning("ATrade.Ibkr.Worker is enabled for paper iBeam but credentials are missing from the ignored local .env: {Message}", readiness.Message);
                break;
            case IbkrSessionReadinessStates.RejectedLiveMode:
                logger.LogCritical("ATrade.Ibkr.Worker rejected an unsafe IBKR configuration: {Message}", readiness.Message);
                break;
            case IbkrSessionReadinessStates.IbeamContainerConfigured:
                logger.LogInformation("ATrade.Ibkr.Worker found local iBeam configuration and is waiting for the auth status endpoint.");
                break;
            case IbkrSessionReadinessStates.Authenticated:
                logger.LogInformation("ATrade.Ibkr.Worker confirmed an authenticated paper iBeam session.");
                break;
            case IbkrSessionReadinessStates.Connecting:
                logger.LogInformation("ATrade.Ibkr.Worker reached iBeam and is waiting for paper IBKR authentication.");
                break;
            case IbkrSessionReadinessStates.Degraded:
                logger.LogWarning("ATrade.Ibkr.Worker reached iBeam but the session is degraded: {Message}", readiness.Message);
                break;
            case IbkrSessionReadinessStates.Error:
                logger.LogWarning("ATrade.Ibkr.Worker could not read the paper iBeam status safely: {Message}", readiness.Message);
                break;
            default:
                logger.LogInformation("ATrade.Ibkr.Worker observed IBKR state {State}.", readiness.State);
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
