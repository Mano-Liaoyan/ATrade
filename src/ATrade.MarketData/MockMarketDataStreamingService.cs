namespace ATrade.MarketData;

public sealed class MockMarketDataStreamingService(IMarketDataProvider marketDataProvider) : IMarketDataStreamingProvider
{
    public MarketDataProviderIdentity Identity => marketDataProvider.Identity;

    public bool TryCreateSnapshot(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error)
    {
        return marketDataProvider.TryGetLatestUpdate(symbol, timeframe, out update, out error);
    }

    public string GetGroupName(string symbol, string timeframe) => $"market-data:{symbol.ToUpperInvariant()}:{timeframe}";
}
