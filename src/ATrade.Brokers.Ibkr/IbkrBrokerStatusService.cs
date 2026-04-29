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

        if (!gatewayOptions.HasConfiguredCredentials || !gatewayOptions.HasConfiguredPaperAccountId)
        {
            return IbkrBrokerStatus.CredentialsMissing(
                gatewayOptions,
                capabilities,
                "Set the ATrade IBKR username, password, and paper account id variables in the ignored local .env before enabling IBKR iBeam integration.");
        }

        if (!gatewayOptions.HasConfiguredIbeamContainer)
        {
            return IbkrBrokerStatus.NotConfigured(
                gatewayOptions,
                capabilities,
                $"{IbkrGatewayEnvironmentVariables.GatewayImage} must be {IbkrGatewayContainerOptions.DefaultIbeamImage} and {IbkrGatewayEnvironmentVariables.GatewayPort} must be a valid local iBeam port before enabling IBKR integration.");
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
        catch (HttpRequestException exception)
        {
            logger.LogWarning(exception, "Configured paper iBeam status endpoint is not reachable yet.");
            return IbkrBrokerStatus.IbeamContainerConfigured(
                gatewayOptions,
                capabilities,
                "iBeam container configuration is present; waiting for the local iBeam auth status endpoint to become reachable.");
        }
        catch (Exception exception)
        {
            logger.LogWarning(exception, "Failed to read the paper iBeam status endpoint safely.");
            return IbkrBrokerStatus.Error(gatewayOptions, capabilities, RedactConfiguredValues(exception.Message, gatewayOptions));
        }
    }

    private static string RedactConfiguredValues(string message, IbkrGatewayOptions options)
    {
        var redactedMessage = message;
        foreach (var value in new[] { options.Username, options.Password, options.PaperAccountId })
        {
            if (!string.IsNullOrWhiteSpace(value))
            {
                redactedMessage = redactedMessage.Replace(value, "[redacted]", StringComparison.OrdinalIgnoreCase);
            }
        }

        return redactedMessage;
    }
}
