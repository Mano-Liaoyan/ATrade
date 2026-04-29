namespace ATrade.MarketData;

public sealed class MarketDataProviderUnavailableException : InvalidOperationException
{
    public MarketDataProviderUnavailableException(MarketDataProviderStatus status)
        : base(status.ToError().Message)
    {
        Status = status;
    }

    public MarketDataProviderStatus Status { get; }

    public MarketDataError Error => Status.ToError();
}
