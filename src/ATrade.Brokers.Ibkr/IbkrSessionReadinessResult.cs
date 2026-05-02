namespace ATrade.Brokers.Ibkr;

public sealed record IbkrSessionReadinessResult(
    string State,
    IbkrAccountMode AccountMode,
    bool IntegrationEnabled,
    bool HasConfiguredCredentials,
    bool HasPaperAccountId,
    bool HasConfiguredIbeamContainer,
    bool HasGatewayBaseUrl,
    bool Authenticated,
    bool Connected,
    bool Competing,
    string? Message,
    string? Diagnostic,
    DateTimeOffset ObservedAtUtc)
{
    public bool IsReady => string.Equals(State, IbkrSessionReadinessStates.Authenticated, StringComparison.Ordinal) && Authenticated && Connected;

    public bool CanAttemptLocalGatewayRead => IntegrationEnabled &&
        AccountMode == IbkrAccountMode.Paper &&
        HasConfiguredCredentials &&
        HasPaperAccountId &&
        HasConfiguredIbeamContainer &&
        HasGatewayBaseUrl;

    public static IbkrSessionReadinessResult Create(
        IbkrGatewayOptions options,
        string state,
        string? message,
        bool authenticated = false,
        bool connected = false,
        bool competing = false,
        string? diagnostic = null,
        DateTimeOffset? observedAtUtc = null)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentException.ThrowIfNullOrWhiteSpace(state);

        return new IbkrSessionReadinessResult(
            State: state.Trim(),
            AccountMode: options.AccountMode,
            IntegrationEnabled: options.IntegrationEnabled,
            HasConfiguredCredentials: options.HasConfiguredCredentials,
            HasPaperAccountId: options.HasConfiguredPaperAccountId,
            HasConfiguredIbeamContainer: options.HasConfiguredIbeamContainer,
            HasGatewayBaseUrl: options.GatewayBaseUrl is not null,
            Authenticated: authenticated,
            Connected: connected,
            Competing: competing,
            Message: message,
            Diagnostic: diagnostic,
            ObservedAtUtc: observedAtUtc ?? DateTimeOffset.UtcNow);
    }

    public static IbkrSessionReadinessResult FromSession(
        IbkrGatewayOptions options,
        IbkrGatewaySessionStatus sessionStatus,
        string? message,
        DateTimeOffset? observedAtUtc = null)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentNullException.ThrowIfNull(sessionStatus);

        var state = sessionStatus.Authenticated
            ? IbkrSessionReadinessStates.Authenticated
            : sessionStatus.Connected
                ? IbkrSessionReadinessStates.Connecting
                : IbkrSessionReadinessStates.Degraded;

        return Create(
            options,
            state,
            message,
            sessionStatus.Authenticated,
            sessionStatus.Connected,
            sessionStatus.Competing,
            observedAtUtc: observedAtUtc);
    }
}
