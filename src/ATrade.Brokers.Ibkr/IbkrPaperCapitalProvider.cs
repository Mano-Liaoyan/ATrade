using ATrade.Accounts;
using Microsoft.Extensions.Logging;

namespace ATrade.Brokers.Ibkr;

public sealed class IbkrPaperCapitalProvider(
    IbkrGatewayOptions gatewayOptions,
    IIbkrSessionReadinessService readinessService,
    IIbkrAccountSummaryClient accountSummaryClient,
    ILogger<IbkrPaperCapitalProvider> logger) : IIbkrPaperCapitalProvider
{
    public async Task<IbkrPaperCapitalAvailability> GetAvailabilityAsync(CancellationToken cancellationToken = default)
    {
        var readiness = await readinessService.CheckReadinessAsync(cancellationToken).ConfigureAwait(false);
        if (!readiness.IsReady)
        {
            return MapReadinessUnavailable(readiness);
        }

        try
        {
            var balance = await accountSummaryClient.GetConfiguredPaperAccountBalanceAsync(cancellationToken).ConfigureAwait(false);
            if (balance.Amount <= 0)
            {
                return Unavailable(
                    PaperCapitalAvailabilityStates.ProviderUnavailable,
                    PaperCapitalErrorCodes.IbkrUnavailable,
                    PaperCapitalSafeMessages.IbkrSourceUnavailable);
            }

            return new IbkrPaperCapitalAvailability(
                Available: true,
                State: PaperCapitalAvailabilityStates.Available,
                Capital: decimal.Round(balance.Amount, 2, MidpointRounding.AwayFromZero),
                Currency: string.IsNullOrWhiteSpace(balance.Currency) ? LocalPaperCapitalValidator.DefaultCurrency : balance.Currency.Trim().ToUpperInvariant(),
                Messages: [new PaperCapitalMessage(
                    "ibkr-paper-balance-ready",
                    "IBKR paper balance is available from an authenticated paper session.",
                    PaperCapitalMessageSeverity.Info)]);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (TaskCanceledException exception)
        {
            LogSafeWarning(exception, "Configured paper iBeam balance endpoint timed out safely.");
            return Unavailable(
                PaperCapitalAvailabilityStates.Timeout,
                PaperCapitalErrorCodes.IbkrTimeout,
                PaperCapitalSafeMessages.IbkrTimeout);
        }
        catch (HttpRequestException exception)
        {
            LogSafeWarning(exception, "Configured paper iBeam balance endpoint is unavailable safely.");
            return Unavailable(
                PaperCapitalAvailabilityStates.ProviderUnavailable,
                PaperCapitalErrorCodes.IbkrUnavailable,
                PaperCapitalSafeMessages.IbkrSourceUnavailable);
        }
        catch (Exception exception)
        {
            LogSafeWarning(exception, "Configured paper iBeam balance endpoint failed safely.");
            return Unavailable(
                PaperCapitalAvailabilityStates.Error,
                PaperCapitalErrorCodes.IbkrUnavailable,
                PaperCapitalSafeMessages.IbkrSourceUnavailable);
        }
    }

    private IbkrPaperCapitalAvailability MapReadinessUnavailable(IbkrSessionReadinessResult readiness)
    {
        if (readiness.AccountMode != IbkrAccountMode.Paper || string.Equals(readiness.State, IbkrSessionReadinessStates.RejectedLiveMode, StringComparison.Ordinal))
        {
            return Unavailable(
                PaperCapitalAvailabilityStates.RejectedLive,
                PaperCapitalErrorCodes.IbkrRejectedLive,
                PaperCapitalSafeMessages.IbkrRejectedLive);
        }

        if (!readiness.IntegrationEnabled || string.Equals(readiness.State, IbkrSessionReadinessStates.Disabled, StringComparison.Ordinal))
        {
            return Unavailable(
                PaperCapitalAvailabilityStates.Disabled,
                PaperCapitalErrorCodes.IbkrDisabled,
                PaperCapitalSafeMessages.IbkrSourceUnavailable,
                PaperCapitalMessageSeverity.Info);
        }

        if (!readiness.HasConfiguredCredentials ||
            !readiness.HasPaperAccountId ||
            string.Equals(readiness.State, IbkrSessionReadinessStates.CredentialsMissing, StringComparison.Ordinal))
        {
            return Unavailable(
                PaperCapitalAvailabilityStates.CredentialsMissing,
                PaperCapitalErrorCodes.IbkrCredentialsMissing,
                PaperCapitalSafeMessages.IbkrCredentialsMissing);
        }

        if (string.Equals(readiness.State, IbkrSessionReadinessStates.Connecting, StringComparison.Ordinal) ||
            string.Equals(readiness.State, IbkrSessionReadinessStates.Degraded, StringComparison.Ordinal))
        {
            return Unavailable(
                PaperCapitalAvailabilityStates.Unauthenticated,
                PaperCapitalErrorCodes.IbkrUnauthenticated,
                PaperCapitalSafeMessages.IbkrUnauthenticated);
        }

        return Unavailable(
            PaperCapitalAvailabilityStates.ProviderUnavailable,
            PaperCapitalErrorCodes.IbkrUnavailable,
            PaperCapitalSafeMessages.IbkrSourceUnavailable);
    }

    private static IbkrPaperCapitalAvailability Unavailable(
        string state,
        string code,
        string message,
        string severity = PaperCapitalMessageSeverity.Warning) =>
        IbkrPaperCapitalAvailability.Unavailable(
            state,
            code,
            message,
            currency: LocalPaperCapitalValidator.DefaultCurrency,
            severity: severity);

    private void LogSafeWarning(Exception exception, string message)
    {
        var diagnostic = PaperCapitalRedaction.RedactText(IbkrGatewayDiagnostics.RedactConfiguredValues(exception.Message, gatewayOptions));
        logger.LogWarning("{Message} Diagnostic: {Diagnostic}", message, diagnostic);
    }
}
