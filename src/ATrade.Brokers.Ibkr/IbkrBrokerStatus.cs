using ATrade.Brokers;

namespace ATrade.Brokers.Ibkr;

public static class IbkrBrokerStatus
{
    public static BrokerProviderIdentity Identity { get; } = BrokerProviderIdentity.Create("ibkr", "Interactive Brokers");

    public static BrokerProviderStatus Disabled(IbkrGatewayOptions options, BrokerProviderCapabilities capabilities) => Create(
        options,
        capabilities,
        state: BrokerProviderStates.Disabled,
        message: "IBKR integration is disabled.");

    public static BrokerProviderStatus Rejected(IbkrGatewayOptions options, BrokerProviderCapabilities capabilities, string message) => Create(
        options,
        capabilities,
        state: BrokerProviderStates.RejectedLiveMode,
        message: message);

    public static BrokerProviderStatus NotConfigured(IbkrGatewayOptions options, BrokerProviderCapabilities capabilities, string message) => Create(
        options,
        capabilities,
        state: BrokerProviderStates.NotConfigured,
        message: message);

    public static BrokerProviderStatus CredentialsMissing(IbkrGatewayOptions options, BrokerProviderCapabilities capabilities, string message) => Create(
        options,
        capabilities,
        state: BrokerProviderStates.CredentialsMissing,
        message: message);

    public static BrokerProviderStatus IbeamContainerConfigured(IbkrGatewayOptions options, BrokerProviderCapabilities capabilities, string message) => Create(
        options,
        capabilities,
        state: BrokerProviderStates.IbeamContainerConfigured,
        message: message);

    public static BrokerProviderStatus Error(IbkrGatewayOptions options, BrokerProviderCapabilities capabilities, string message) => Create(
        options,
        capabilities,
        state: BrokerProviderStates.Error,
        message: message);

    public static BrokerProviderStatus FromSession(
        IbkrGatewayOptions options,
        BrokerProviderCapabilities capabilities,
        IbkrGatewaySessionStatus sessionStatus)
    {
        var state = sessionStatus.Authenticated
            ? BrokerProviderStates.Authenticated
            : sessionStatus.Connected
                ? BrokerProviderStates.Connecting
                : BrokerProviderStates.Degraded;

        return Create(
            options,
            capabilities,
            state,
            sessionStatus.Message,
            sessionStatus.Authenticated,
            sessionStatus.Connected,
            sessionStatus.Competing);
    }

    public static BrokerProviderStatus FromReadiness(
        IbkrGatewayOptions options,
        BrokerProviderCapabilities capabilities,
        IbkrSessionReadinessResult readiness)
    {
        ArgumentNullException.ThrowIfNull(readiness);

        return Create(
            options,
            capabilities,
            readiness.State,
            readiness.Message,
            readiness.Authenticated,
            readiness.Connected,
            readiness.Competing);
    }

    private static BrokerProviderStatus Create(
        IbkrGatewayOptions options,
        BrokerProviderCapabilities capabilities,
        string state,
        string? message,
        bool authenticated = false,
        bool connected = false,
        bool competing = false)
    {
        return new BrokerProviderStatus(
            Provider: Identity.Provider,
            State: state,
            Mode: ToBrokerAccountMode(options.AccountMode),
            IntegrationEnabled: options.IntegrationEnabled,
            HasPaperAccountId: options.HasConfiguredPaperAccountId,
            Authenticated: authenticated,
            Connected: connected,
            Competing: competing,
            Message: message,
            ObservedAtUtc: DateTimeOffset.UtcNow,
            Capabilities: capabilities);
    }

    private static string ToBrokerAccountMode(IbkrAccountMode accountMode) => accountMode switch
    {
        IbkrAccountMode.Paper => BrokerAccountModes.Paper,
        IbkrAccountMode.Live => BrokerAccountModes.Live,
        _ => BrokerAccountModes.Unknown,
    };
}
