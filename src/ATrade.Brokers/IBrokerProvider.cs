namespace ATrade.Brokers;

public interface IBrokerProvider
{
    BrokerProviderIdentity Identity { get; }

    BrokerProviderCapabilities Capabilities { get; }

    Task<BrokerProviderStatus> GetStatusAsync(CancellationToken cancellationToken = default);
}
