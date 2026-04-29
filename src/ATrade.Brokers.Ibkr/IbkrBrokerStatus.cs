namespace ATrade.Brokers.Ibkr;

public sealed record IbkrBrokerStatus(
    string Provider,
    string State,
    string Mode,
    bool IntegrationEnabled,
    bool HasPaperAccountId,
    bool Authenticated,
    bool Connected,
    bool Competing,
    string? Message,
    DateTimeOffset ObservedAtUtc,
    IbkrBrokerAdapterCapabilities Capabilities)
{
    public static IbkrBrokerStatus Disabled(IbkrGatewayOptions options, IbkrBrokerAdapterCapabilities capabilities) => Create(
        options,
        capabilities,
        state: "disabled",
        message: "IBKR integration is disabled.");

    public static IbkrBrokerStatus Rejected(IbkrGatewayOptions options, IbkrBrokerAdapterCapabilities capabilities, string message) => Create(
        options,
        capabilities,
        state: "rejected-live-mode",
        message: message);

    public static IbkrBrokerStatus NotConfigured(IbkrGatewayOptions options, IbkrBrokerAdapterCapabilities capabilities, string message) => Create(
        options,
        capabilities,
        state: "not-configured",
        message: message);

    public static IbkrBrokerStatus Error(IbkrGatewayOptions options, IbkrBrokerAdapterCapabilities capabilities, string message) => Create(
        options,
        capabilities,
        state: "error",
        message: message);

    public static IbkrBrokerStatus FromSession(
        IbkrGatewayOptions options,
        IbkrBrokerAdapterCapabilities capabilities,
        IbkrGatewaySessionStatus sessionStatus)
    {
        var state = sessionStatus.Authenticated
            ? "authenticated"
            : sessionStatus.Connected
                ? "connecting"
                : "degraded";

        return Create(
            options,
            capabilities,
            state,
            sessionStatus.Message,
            sessionStatus.Authenticated,
            sessionStatus.Connected,
            sessionStatus.Competing);
    }

    private static IbkrBrokerStatus Create(
        IbkrGatewayOptions options,
        IbkrBrokerAdapterCapabilities capabilities,
        string state,
        string? message,
        bool authenticated = false,
        bool connected = false,
        bool competing = false)
    {
        return new IbkrBrokerStatus(
            Provider: "ibkr",
            State: state,
            Mode: options.AccountMode.ToString().ToLowerInvariant(),
            IntegrationEnabled: options.IntegrationEnabled,
            HasPaperAccountId: !string.IsNullOrWhiteSpace(options.PaperAccountId),
            Authenticated: authenticated,
            Connected: connected,
            Competing: competing,
            Message: message,
            ObservedAtUtc: DateTimeOffset.UtcNow,
            Capabilities: capabilities);
    }
}
