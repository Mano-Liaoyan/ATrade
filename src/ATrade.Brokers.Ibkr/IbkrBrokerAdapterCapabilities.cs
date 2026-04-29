namespace ATrade.Brokers.Ibkr;

public sealed record IbkrBrokerAdapterCapabilities(
    bool SupportsSessionStatus,
    bool SupportsBrokerOrderPlacement,
    bool SupportsCredentialPersistence,
    bool SupportsExecutionPersistence,
    bool UsesOfficialApisOnly)
{
    public static IbkrBrokerAdapterCapabilities PaperSafeReadOnly { get; } = new(
        SupportsSessionStatus: true,
        SupportsBrokerOrderPlacement: false,
        SupportsCredentialPersistence: false,
        SupportsExecutionPersistence: false,
        UsesOfficialApisOnly: true);
}
