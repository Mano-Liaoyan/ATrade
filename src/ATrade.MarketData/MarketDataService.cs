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

    public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
    {
        response = null;
        if (!TryEnsureProviderAvailable(out error))
        {
            return false;
        }

        return provider.TryGetCandles(symbol, timeframe, out response, out error, identity);
    }

    public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
    {
        response = null;
        if (!TryEnsureProviderAvailable(out error))
        {
            return false;
        }

        return provider.TryGetIndicators(symbol, timeframe, out response, out error, identity);
    }

    public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
    {
        update = null;
        if (!TryEnsureProviderAvailable(out error))
        {
            return false;
        }

        return provider.TryGetLatestUpdate(symbol, timeframe, out update, out error, identity);
    }

    public async Task<MarketDataReadResult<TrendingSymbolsResponse>> GetTrendingSymbolsAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var availabilityError = await GetProviderAvailabilityErrorAsync(cancellationToken).ConfigureAwait(false);
        if (availabilityError is not null)
        {
            return MarketDataReadResult<TrendingSymbolsResponse>.Failure(availabilityError);
        }

        return await provider.GetTrendingSymbolsAsync(cancellationToken).ConfigureAwait(false);
    }

    public async Task<MarketDataReadResult<MarketDataSymbolSearchResponse>> SearchSymbolsAsync(
        string? query,
        string? assetClass,
        int? limit,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!TryNormalizeSearchRequest(query, assetClass, limit, out var normalizedQuery, out var normalizedAssetClass, out var normalizedLimit, out var error))
        {
            return MarketDataReadResult<MarketDataSymbolSearchResponse>.Failure(error!);
        }

        var availabilityError = await GetProviderAvailabilityErrorAsync(cancellationToken).ConfigureAwait(false);
        if (availabilityError is not null)
        {
            return MarketDataReadResult<MarketDataSymbolSearchResponse>.Failure(availabilityError);
        }

        if (!provider.Capabilities.SupportsSymbolSearch)
        {
            return MarketDataReadResult<MarketDataSymbolSearchResponse>.Failure(new MarketDataError(
                MarketDataProviderErrorCodes.SearchNotSupported,
                $"Market-data provider '{provider.Identity.Provider}' does not support symbol search."));
        }

        var providerResult = await provider.SearchSymbolsAsync(normalizedQuery, cancellationToken).ConfigureAwait(false);
        if (providerResult.IsFailure || providerResult.Value is null)
        {
            return MarketDataReadResult<MarketDataSymbolSearchResponse>.Failure(ToReadError(providerResult.Error));
        }

        var providerResponse = providerResult.Value;
        var response = providerResponse with
        {
            Results = providerResponse.Results
                .Where(result => string.Equals(NormalizeSearchAssetClass(result.Identity.AssetClass), normalizedAssetClass, StringComparison.OrdinalIgnoreCase))
                .Take(normalizedLimit)
                .ToArray(),
        };
        return MarketDataReadResult<MarketDataSymbolSearchResponse>.Success(response);
    }

    public async Task<MarketDataReadResult<MarketDataSymbol>> GetSymbolAsync(string symbol, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var availabilityError = await GetProviderAvailabilityErrorAsync(cancellationToken).ConfigureAwait(false);
        if (availabilityError is not null)
        {
            return MarketDataReadResult<MarketDataSymbol>.Failure(availabilityError);
        }

        var providerResult = await provider.GetSymbolAsync(symbol, cancellationToken).ConfigureAwait(false);
        return providerResult.IsSuccess && providerResult.Value is not null
            ? providerResult
            : MarketDataReadResult<MarketDataSymbol>.Failure(ToReadError(providerResult.Error));
    }

    public async Task<MarketDataReadResult<CandleSeriesResponse>> GetCandlesAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var availabilityError = await GetProviderAvailabilityErrorAsync(cancellationToken).ConfigureAwait(false);
        if (availabilityError is not null)
        {
            return MarketDataReadResult<CandleSeriesResponse>.Failure(availabilityError);
        }

        var providerResult = await provider.GetCandlesAsync(symbol, timeframe, identity, cancellationToken).ConfigureAwait(false);
        return providerResult.IsSuccess && providerResult.Value is not null
            ? providerResult
            : MarketDataReadResult<CandleSeriesResponse>.Failure(ToReadError(providerResult.Error));
    }

    public async Task<MarketDataReadResult<IndicatorResponse>> GetIndicatorsAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var availabilityError = await GetProviderAvailabilityErrorAsync(cancellationToken).ConfigureAwait(false);
        if (availabilityError is not null)
        {
            return MarketDataReadResult<IndicatorResponse>.Failure(availabilityError);
        }

        var providerResult = await provider.GetIndicatorsAsync(symbol, timeframe, identity, cancellationToken).ConfigureAwait(false);
        return providerResult.IsSuccess && providerResult.Value is not null
            ? providerResult
            : MarketDataReadResult<IndicatorResponse>.Failure(ToReadError(providerResult.Error));
    }

    public async Task<MarketDataReadResult<MarketDataUpdate>> GetLatestUpdateAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var availabilityError = await GetProviderAvailabilityErrorAsync(cancellationToken).ConfigureAwait(false);
        if (availabilityError is not null)
        {
            return MarketDataReadResult<MarketDataUpdate>.Failure(availabilityError);
        }

        var providerResult = await provider.GetLatestUpdateAsync(symbol, timeframe, identity, cancellationToken).ConfigureAwait(false);
        return providerResult.IsSuccess && providerResult.Value is not null
            ? providerResult
            : MarketDataReadResult<MarketDataUpdate>.Failure(ToReadError(providerResult.Error));
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

    private async Task<MarketDataError?> GetProviderAvailabilityErrorAsync(CancellationToken cancellationToken)
    {
        var status = await provider.GetStatusAsync(cancellationToken).ConfigureAwait(false);
        return status.IsAvailable ? null : status.ToError();
    }

    private static MarketDataError ToReadError(MarketDataError? error) => error ?? new MarketDataError(
        MarketDataProviderErrorCodes.MarketDataRequestFailed,
        "Market-data request failed.");
}
