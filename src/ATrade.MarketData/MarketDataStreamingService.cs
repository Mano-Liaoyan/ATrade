namespace ATrade.MarketData;

public interface IMarketDataStreamingService
{
    bool TryCreateSnapshot(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error);

    string GetGroupName(string symbol, string timeframe);
}

public sealed class MarketDataStreamingService(
    IMarketDataProvider marketDataProvider,
    IMarketDataStreamingProvider streamingProvider) : IMarketDataStreamingService
{
    public bool TryCreateSnapshot(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error)
    {
        update = null;
        var status = marketDataProvider.GetStatus();
        if (!status.IsAvailable)
        {
            error = status.ToError();
            return false;
        }

        return streamingProvider.TryCreateSnapshot(symbol, timeframe, out update, out error);
    }

    public string GetGroupName(string symbol, string timeframe) => streamingProvider.GetGroupName(symbol, timeframe);
}
