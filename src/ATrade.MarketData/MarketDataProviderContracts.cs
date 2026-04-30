namespace ATrade.MarketData;

public interface IMarketDataProvider
{
    MarketDataProviderIdentity Identity { get; }

    MarketDataProviderCapabilities Capabilities { get; }

    MarketDataProviderStatus GetStatus();

    TrendingSymbolsResponse GetTrendingSymbols();

    bool TrySearchSymbols(string query, out MarketDataSymbolSearchResponse? response, out MarketDataError? error);

    bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol);

    bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error);

    bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error);

    bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error);
}

public interface IMarketDataStreamingProvider
{
    MarketDataProviderIdentity Identity { get; }

    bool TryCreateSnapshot(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error);

    string GetGroupName(string symbol, string timeframe);
}
