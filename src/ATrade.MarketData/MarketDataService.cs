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

    public bool TrySearchSymbols(string? query, string? assetClass, int? limit, out MarketDataSymbolSearchResponse? response, out MarketDataError? error)
    {
        response = null;
        if (!TryNormalizeSearchRequest(query, assetClass, limit, out var normalizedQuery, out var normalizedAssetClass, out var normalizedLimit, out error))
        {
            return false;
        }

        if (!TryEnsureProviderAvailable(out error))
        {
            return false;
        }

        if (!provider.Capabilities.SupportsSymbolSearch)
        {
            error = new MarketDataError(MarketDataProviderErrorCodes.SearchNotSupported, $"Market-data provider '{provider.Identity.Provider}' does not support symbol search.");
            return false;
        }

        if (!provider.TrySearchSymbols(normalizedQuery, out var providerResponse, out error) || providerResponse is null)
        {
            return false;
        }

        response = providerResponse with
        {
            Results = providerResponse.Results
                .Where(result => string.Equals(NormalizeSearchAssetClass(result.Identity.AssetClass), normalizedAssetClass, StringComparison.OrdinalIgnoreCase))
                .Take(normalizedLimit)
                .ToArray(),
        };
        return true;
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

    private static bool TryNormalizeSearchRequest(
        string? query,
        string? assetClass,
        int? limit,
        out string normalizedQuery,
        out string normalizedAssetClass,
        out int normalizedLimit,
        out MarketDataError? error)
    {
        normalizedQuery = query?.Trim() ?? string.Empty;
        normalizedAssetClass = NormalizeSearchAssetClass(assetClass);
        normalizedLimit = limit ?? MarketDataSymbolSearchLimits.DefaultLimit;

        if (normalizedQuery.Length < MarketDataSymbolSearchLimits.MinimumQueryLength)
        {
            error = new MarketDataError(
                MarketDataProviderErrorCodes.InvalidSearchQuery,
                $"A symbol search query must be at least {MarketDataSymbolSearchLimits.MinimumQueryLength} characters.");
            return false;
        }

        if (!string.Equals(normalizedAssetClass, MarketDataAssetClasses.Stock, StringComparison.OrdinalIgnoreCase))
        {
            error = new MarketDataError(
                MarketDataProviderErrorCodes.UnsupportedAssetClass,
                "Only stock symbol search is currently supported.");
            return false;
        }

        if (normalizedLimit < 1)
        {
            error = new MarketDataError(
                MarketDataProviderErrorCodes.InvalidSearchLimit,
                "A symbol search limit must be greater than zero.");
            return false;
        }

        normalizedLimit = Math.Min(normalizedLimit, MarketDataSymbolSearchLimits.MaximumLimit);
        error = null;
        return true;
    }

    private static string NormalizeSearchAssetClass(string? assetClass)
    {
        if (string.IsNullOrWhiteSpace(assetClass))
        {
            return MarketDataAssetClasses.Stock;
        }

        return assetClass.Trim().ToUpperInvariant() switch
        {
            "STOCK" or "STOCKS" => MarketDataAssetClasses.Stock,
            var normalized => normalized,
        };
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
