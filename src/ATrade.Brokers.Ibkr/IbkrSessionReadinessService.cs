using Microsoft.Extensions.Logging;

namespace ATrade.Brokers.Ibkr;

public sealed class IbkrSessionReadinessService(
    IbkrGatewayOptions gatewayOptions,
    IIbkrPaperTradingGuard paperTradingGuard,
    IIbkrGatewayClient gatewayClient,
    ILogger<IbkrSessionReadinessService> logger) : IIbkrSessionReadinessService
{
    public async Task<IbkrSessionReadinessResult> CheckReadinessAsync(CancellationToken cancellationToken = default)
    {
        var observedAtUtc = DateTimeOffset.UtcNow;
        var guardResult = paperTradingGuard.Evaluate();
        if (!guardResult.IsAllowed)
        {
            return IbkrSessionReadinessResult.Create(
                gatewayOptions,
                IbkrSessionReadinessStates.RejectedLiveMode,
                guardResult.Message,
                observedAtUtc: observedAtUtc);
        }

        if (!gatewayOptions.IntegrationEnabled)
        {
            return IbkrSessionReadinessResult.Create(
                gatewayOptions,
                IbkrSessionReadinessStates.Disabled,
                "IBKR integration is disabled.",
                observedAtUtc: observedAtUtc);
        }

        if (!gatewayOptions.HasConfiguredCredentials || !gatewayOptions.HasConfiguredPaperAccountId)
        {
            return IbkrSessionReadinessResult.Create(
                gatewayOptions,
                IbkrSessionReadinessStates.CredentialsMissing,
                "Set the ATrade IBKR username, password, and paper account id variables in the ignored local .env before enabling IBKR iBeam integration.",
                observedAtUtc: observedAtUtc);
        }

        if (!gatewayOptions.HasConfiguredIbeamContainer)
        {
            return IbkrSessionReadinessResult.Create(
                gatewayOptions,
                IbkrSessionReadinessStates.NotConfigured,
                $"{IbkrGatewayEnvironmentVariables.GatewayImage} must be {IbkrGatewayContainerOptions.DefaultIbeamImage} and {IbkrGatewayEnvironmentVariables.GatewayPort} must be a valid local iBeam port before enabling IBKR integration.",
                observedAtUtc: observedAtUtc);
        }

        if (gatewayOptions.GatewayBaseUrl is null)
        {
            return IbkrSessionReadinessResult.Create(
                gatewayOptions,
                IbkrSessionReadinessStates.NotConfigured,
                $"{IbkrGatewayEnvironmentVariables.GatewayUrl} must be configured with an absolute URL before enabling IBKR integration.",
                observedAtUtc: observedAtUtc);
        }

        try
        {
            var sessionStatus = await gatewayClient.GetSessionStatusAsync(cancellationToken).ConfigureAwait(false);
            return IbkrSessionReadinessResult.FromSession(
                gatewayOptions,
                sessionStatus,
                RedactConfiguredValues(sessionStatus.Message),
                observedAtUtc);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (TaskCanceledException exception)
        {
            var diagnostic = RedactConfiguredValues(exception.Message);
            logger.LogWarning("Configured paper iBeam status endpoint timed out over local HTTPS transport: {Diagnostic}", diagnostic);
            return IbkrSessionReadinessResult.Create(
                gatewayOptions,
                IbkrSessionReadinessStates.IbeamContainerConfigured,
                IbkrGatewayTransport.CreateTransportTimeoutMessage(),
                diagnostic: diagnostic,
                observedAtUtc: observedAtUtc);
        }
        catch (HttpRequestException exception)
        {
            var diagnostic = RedactConfiguredValues(exception.Message);
            logger.LogWarning("Configured paper iBeam status endpoint is not reachable over local HTTPS transport yet: {Diagnostic}", diagnostic);
            return IbkrSessionReadinessResult.Create(
                gatewayOptions,
                IbkrSessionReadinessStates.IbeamContainerConfigured,
                IbkrGatewayTransport.CreateTransportUnavailableMessage(),
                diagnostic: diagnostic,
                observedAtUtc: observedAtUtc);
        }
        catch (Exception exception)
        {
            var diagnostic = RedactConfiguredValues(exception.Message);
            logger.LogWarning("Failed to read the paper iBeam status endpoint safely: {Diagnostic}", diagnostic);
            return IbkrSessionReadinessResult.Create(
                gatewayOptions,
                IbkrSessionReadinessStates.Error,
                string.IsNullOrWhiteSpace(diagnostic) ? "IBKR iBeam status check failed safely." : diagnostic,
                diagnostic: diagnostic,
                observedAtUtc: observedAtUtc);
        }
    }

    private string RedactConfiguredValues(string? message) => IbkrGatewayDiagnostics.RedactConfiguredValues(message, gatewayOptions);
}
