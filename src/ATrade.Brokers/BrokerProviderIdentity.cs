namespace ATrade.Brokers;

public sealed record BrokerProviderIdentity(string Provider, string DisplayName)
{
    public static BrokerProviderIdentity Create(string provider, string displayName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(provider);
        ArgumentException.ThrowIfNullOrWhiteSpace(displayName);

        return new BrokerProviderIdentity(provider.Trim().ToLowerInvariant(), displayName.Trim());
    }
}
