using ATrade.Brokers;

namespace ATrade.Brokers.Ibkr;

public sealed class IbkrBrokerStatusService(
    IbkrGatewayOptions gatewayOptions,
    IIbkrSessionReadinessService readinessService,
    BrokerProviderCapabilities capabilities) : IIbkrBrokerStatusService
{
    public BrokerProviderIdentity Identity => IbkrBrokerStatus.Identity;

    public BrokerProviderCapabilities Capabilities => capabilities;

    public async Task<BrokerProviderStatus> GetStatusAsync(CancellationToken cancellationToken = default)
    {
        var readiness = await readinessService.CheckReadinessAsync(cancellationToken).ConfigureAwait(false);
        return IbkrBrokerStatus.FromReadiness(gatewayOptions, capabilities, readiness);
    }
}
