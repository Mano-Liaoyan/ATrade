namespace ATrade.MarketData;

public sealed class MarketDataService(IMarketDataProvider provider) : IMarketDataService
{
    public TrendingSymbolsResponse GetTrendingSymbols()
    {
        var status = provider.GetStatus();
        if (!status.IsAvailable)
        {
            throw new MarketDataProviderUnavailableException(status);
        }

        return provider.GetTrendingSymbols();
    }

    public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol)
    {
        marketSymbol = null;
        if (!provider.GetStatus().IsAvailable)
        {
            return false;
        }

        return provider.TryGetSymbol(symbol, out marketSymbol);
    }

    public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error)
    {
        response = null;
        if (!TryEnsureProviderAvailable(out error))
        {
            return false;
        }

        return provider.TryGetCandles(symbol, timeframe, out response, out error);
    }

    public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error)
    {
        response = null;
        if (!TryEnsureProviderAvailable(out error))
        {
            return false;
        }

        return provider.TryGetIndicators(symbol, timeframe, out response, out error);
    }

    public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error)
    {
        update = null;
        if (!TryEnsureProviderAvailable(out error))
        {
            return false;
        }

        return provider.TryGetLatestUpdate(symbol, timeframe, out update, out error);
    }

    private bool TryEnsureProviderAvailable(out MarketDataError? error)
    {
        var status = provider.GetStatus();
        if (status.IsAvailable)
        {
            error = null;
            return true;
        }

        error = status.ToError();
        return false;
    }
}
