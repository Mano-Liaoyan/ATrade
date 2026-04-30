namespace ATrade.MarketData;

public sealed class MarketDataProviderUnavailableException : InvalidOperationException
{
    private readonly MarketDataError? error;

    public MarketDataProviderUnavailableException(MarketDataProviderStatus status)
        : this(status, null)
    {
    }

    public MarketDataProviderUnavailableException(MarketDataProviderStatus status, MarketDataError? error)
        : base((error ?? status.ToError()).Message)
    {
        Status = status;
        this.error = error;
    }

    public MarketDataProviderStatus Status { get; }

    public MarketDataError Error => error ?? Status.ToError();
}
