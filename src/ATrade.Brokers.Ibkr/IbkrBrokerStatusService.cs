using ATrade.Brokers;
using Microsoft.Extensions.Logging;

namespace ATrade.Brokers.Ibkr;

public sealed class IbkrBrokerStatusService(
    IbkrGatewayOptions gatewayOptions,
    IIbkrPaperTradingGuard paperTradingGuard,
    IIbkrGatewayClient gatewayClient,
    BrokerProviderCapabilities capabilities,
    ILogger<IbkrBrokerStatusService> logger) : IIbkrBrokerStatusService
{
    public BrokerProviderIdentity Identity => IbkrBrokerStatus.Identity;

    public BrokerProviderCapabilities Capabilities => capabilities;

    public async Task<BrokerProviderStatus> GetStatusAsync(CancellationToken cancellationToken = default)
    {
        var guardResult = paperTradingGuard.Evaluate();
        if (!guardResult.IsAllowed)
        {
            return IbkrBrokerStatus.Rejected(gatewayOptions, capabilities, guardResult.Message);
        }

        if (!gatewayOptions.IntegrationEnabled)
        {
            return IbkrBrokerStatus.Disabled(gatewayOptions, capabilities);
        }

        if (gatewayOptions.GatewayBaseUrl is null)
        {
            return IbkrBrokerStatus.NotConfigured(
                gatewayOptions,
                capabilities,
                $"{IbkrGatewayEnvironmentVariables.GatewayUrl} must be configured with an absolute URL before enabling IBKR integration.");
        }

        try
        {
            var sessionStatus = await gatewayClient.GetSessionStatusAsync(cancellationToken).ConfigureAwait(false);
            return IbkrBrokerStatus.FromSession(gatewayOptions, capabilities, sessionStatus);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception exception)
        {
            logger.LogWarning(exception, "Failed to reach the paper IBKR Gateway status endpoint safely.");
            return IbkrBrokerStatus.Error(gatewayOptions, capabilities, exception.Message);
        }
    }
}
