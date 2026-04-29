namespace ATrade.Brokers.Ibkr;

public interface IIbkrBrokerStatusService
{
    Task<IbkrBrokerStatus> GetStatusAsync(CancellationToken cancellationToken = default);
}
