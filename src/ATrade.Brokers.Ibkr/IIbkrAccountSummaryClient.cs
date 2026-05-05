namespace ATrade.Brokers.Ibkr;

public interface IIbkrAccountSummaryClient
{
    Task<IbkrAccountSummaryBalance> GetConfiguredPaperAccountBalanceAsync(CancellationToken cancellationToken = default);
}
