namespace ATrade.Brokers;

public sealed record BrokerProviderStatus(
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
    BrokerProviderCapabilities Capabilities);
