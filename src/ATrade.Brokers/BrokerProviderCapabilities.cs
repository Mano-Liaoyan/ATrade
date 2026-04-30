namespace ATrade.Brokers;

public sealed record BrokerProviderCapabilities(
    bool SupportsSessionStatus,
    bool SupportsReadOnlyMarketData,
    bool SupportsBrokerOrderPlacement,
    bool SupportsCredentialPersistence,
    bool SupportsExecutionPersistence,
    bool UsesOfficialApisOnly)
{
    public static BrokerProviderCapabilities PaperSafeStatusOnly { get; } = new(
        SupportsSessionStatus: true,
        SupportsReadOnlyMarketData: false,
        SupportsBrokerOrderPlacement: false,
        SupportsCredentialPersistence: false,
        SupportsExecutionPersistence: false,
        UsesOfficialApisOnly: true);
}
