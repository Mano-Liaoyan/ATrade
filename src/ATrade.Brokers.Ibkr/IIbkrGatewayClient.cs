namespace ATrade.Brokers.Ibkr;

public interface IIbkrGatewayClient
{
    Task<IbkrGatewaySessionStatus> GetSessionStatusAsync(CancellationToken cancellationToken = default);
}
