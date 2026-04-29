namespace ATrade.MarketData;

public interface IMarketDataStreamingService
{
    bool TryCreateSnapshot(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error);

    string GetGroupName(string symbol, string timeframe);
}

public sealed class MockMarketDataStreamingService(IMarketDataService marketDataService) : IMarketDataStreamingService
{
    public bool TryCreateSnapshot(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error)
    {
        return marketDataService.TryGetLatestUpdate(symbol, timeframe, out update, out error);
    }

    public string GetGroupName(string symbol, string timeframe) => $"market-data:{symbol.ToUpperInvariant()}:{timeframe}";
}
