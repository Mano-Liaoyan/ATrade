using ATrade.Brokers;
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

            if (string.Equals(status.State, BrokerProviderStates.RejectedLiveMode, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException(status.Message ?? "ATrade.Ibkr.Worker rejects non-paper IBKR modes.");
            }

            if (string.Equals(status.State, BrokerProviderStates.Disabled, StringComparison.OrdinalIgnoreCase) ||
                string.Equals(status.State, BrokerProviderStates.NotConfigured, StringComparison.OrdinalIgnoreCase) ||
                string.Equals(status.State, BrokerProviderStates.CredentialsMissing, StringComparison.OrdinalIgnoreCase))
            {
                await WaitUntilStoppedAsync(stoppingToken);
                return;
            }

            await Task.Delay(StatusPollInterval, stoppingToken);
        }
    }

    private void LogStatus(BrokerProviderStatus status)
    {
        switch (status.State)
        {
            case BrokerProviderStates.Disabled:
                logger.LogInformation("ATrade.Ibkr.Worker is disabled and will remain idle until local configuration enables paper mode.");
                break;
            case BrokerProviderStates.NotConfigured:
                logger.LogWarning("ATrade.Ibkr.Worker is enabled for paper mode but not fully configured yet: {Message}", status.Message);
                break;
            case BrokerProviderStates.CredentialsMissing:
                logger.LogWarning("ATrade.Ibkr.Worker is enabled for paper iBeam but credentials are missing from the ignored local .env: {Message}", status.Message);
                break;
            case BrokerProviderStates.RejectedLiveMode:
                logger.LogCritical("ATrade.Ibkr.Worker rejected an unsafe IBKR configuration: {Message}", status.Message);
                break;
            case BrokerProviderStates.IbeamContainerConfigured:
                logger.LogInformation("ATrade.Ibkr.Worker found local iBeam configuration and is waiting for the auth status endpoint.");
                break;
            case BrokerProviderStates.Authenticated:
                logger.LogInformation("ATrade.Ibkr.Worker confirmed an authenticated paper iBeam session.");
                break;
            case BrokerProviderStates.Connecting:
                logger.LogInformation("ATrade.Ibkr.Worker reached iBeam and is waiting for paper IBKR authentication.");
                break;
            case BrokerProviderStates.Degraded:
                logger.LogWarning("ATrade.Ibkr.Worker reached iBeam but the session is degraded: {Message}", status.Message);
                break;
            case BrokerProviderStates.Error:
                logger.LogWarning("ATrade.Ibkr.Worker could not read the paper iBeam status safely: {Message}", status.Message);
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
