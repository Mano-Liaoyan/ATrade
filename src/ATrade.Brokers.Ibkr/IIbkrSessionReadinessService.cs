namespace ATrade.Brokers.Ibkr;

public interface IIbkrSessionReadinessService
{
    Task<IbkrSessionReadinessResult> CheckReadinessAsync(CancellationToken cancellationToken = default);
}
