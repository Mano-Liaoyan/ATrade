namespace ATrade.MarketData.Timescale;

public sealed class TimescaleMarketDataStorageUnavailableException : InvalidOperationException
{
    public TimescaleMarketDataStorageUnavailableException(string message)
        : base(message)
    {
    }

    public TimescaleMarketDataStorageUnavailableException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}
