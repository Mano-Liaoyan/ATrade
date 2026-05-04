namespace ATrade.MarketData;

public interface IMarketDataProvider
{
    MarketDataProviderIdentity Identity { get; }

    MarketDataProviderCapabilities Capabilities { get; }

    MarketDataProviderStatus GetStatus();

    TrendingSymbolsResponse GetTrendingSymbols();

    bool TrySearchSymbols(string query, out MarketDataSymbolSearchResponse? response, out MarketDataError? error);

    bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol);

    bool TryGetCandles(string symbol, string? chartRange, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null);

    bool TryGetIndicators(string symbol, string? chartRange, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null);

    bool TryGetLatestUpdate(string symbol, string? chartRange, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null);

    Task<MarketDataProviderStatus> GetStatusAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(GetStatus());
    }

    Task<MarketDataReadResult<TrendingSymbolsResponse>> GetTrendingSymbolsAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        try
        {
            return Task.FromResult(MarketDataReadResult<TrendingSymbolsResponse>.Success(GetTrendingSymbols()));
        }
        catch (MarketDataProviderUnavailableException exception)
        {
            return Task.FromResult(MarketDataReadResult<TrendingSymbolsResponse>.Failure(exception.Error));
        }
    }

    Task<MarketDataReadResult<MarketDataSymbolSearchResponse>> SearchSymbolsAsync(string query, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(
            TrySearchSymbols(query, out var response, out var error) && response is not null
                ? MarketDataReadResult<MarketDataSymbolSearchResponse>.Success(response)
                : MarketDataReadResult<MarketDataSymbolSearchResponse>.Failure(ToReadError(error)));
    }

    Task<MarketDataReadResult<MarketDataSymbol>> GetSymbolAsync(string symbol, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(
            TryGetSymbol(symbol, out var marketSymbol) && marketSymbol is not null
                ? MarketDataReadResult<MarketDataSymbol>.Success(marketSymbol)
                : MarketDataReadResult<MarketDataSymbol>.Failure(new MarketDataError(
                    MarketDataProviderErrorCodes.UnsupportedSymbol,
                    $"Market-data provider returned no symbol metadata for '{symbol}'.")));
    }

    Task<MarketDataReadResult<CandleSeriesResponse>> GetCandlesAsync(
        string symbol,
        string? chartRange,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!TryNormalizeChartRange(chartRange, out var normalizedChartRange, out var rangeError))
        {
            return Task.FromResult(MarketDataReadResult<CandleSeriesResponse>.Failure(rangeError!));
        }

        return Task.FromResult(
            TryGetCandles(symbol, normalizedChartRange, out var response, out var error, identity) && response is not null
                ? MarketDataReadResult<CandleSeriesResponse>.Success(response)
                : MarketDataReadResult<CandleSeriesResponse>.Failure(ToReadError(error)));
    }

    Task<MarketDataReadResult<IndicatorResponse>> GetIndicatorsAsync(
        string symbol,
        string? chartRange,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!TryNormalizeChartRange(chartRange, out var normalizedChartRange, out var rangeError))
        {
            return Task.FromResult(MarketDataReadResult<IndicatorResponse>.Failure(rangeError!));
        }

        return Task.FromResult(
            TryGetIndicators(symbol, normalizedChartRange, out var response, out var error, identity) && response is not null
                ? MarketDataReadResult<IndicatorResponse>.Success(response)
                : MarketDataReadResult<IndicatorResponse>.Failure(ToReadError(error)));
    }

    Task<MarketDataReadResult<MarketDataUpdate>> GetLatestUpdateAsync(
        string symbol,
        string? chartRange,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!TryNormalizeChartRange(chartRange, out var normalizedChartRange, out var rangeError))
        {
            return Task.FromResult(MarketDataReadResult<MarketDataUpdate>.Failure(rangeError!));
        }

        return Task.FromResult(
            TryGetLatestUpdate(symbol, normalizedChartRange, out var update, out var error, identity) && update is not null
                ? MarketDataReadResult<MarketDataUpdate>.Success(update)
                : MarketDataReadResult<MarketDataUpdate>.Failure(ToReadError(error)));
    }

    private static bool TryNormalizeChartRange(string? chartRange, out string normalizedChartRange, out MarketDataError? error)
    {
        if (ChartRangePresets.TryNormalize(chartRange, out normalizedChartRange))
        {
            error = null;
            return true;
        }

        error = ChartRangePresets.CreateUnsupportedRangeError(chartRange);
        return false;
    }

    private static MarketDataError ToReadError(MarketDataError? error) => error ?? new MarketDataError(
        MarketDataProviderErrorCodes.MarketDataRequestFailed,
        "Market-data request failed.");
}

public interface IMarketDataStreamingProvider
{
    MarketDataProviderIdentity Identity { get; }

    bool TryCreateSnapshot(string symbol, string? chartRange, out MarketDataUpdate? update, out MarketDataError? error);

    Task<MarketDataReadResult<MarketDataUpdate>> CreateSnapshotAsync(
        string symbol,
        string? chartRange,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!ChartRangePresets.TryNormalize(chartRange, out var normalizedChartRange))
        {
            return Task.FromResult(MarketDataReadResult<MarketDataUpdate>.Failure(ChartRangePresets.CreateUnsupportedRangeError(chartRange)));
        }

        return Task.FromResult(
            TryCreateSnapshot(symbol, normalizedChartRange, out var update, out var error) && update is not null
                ? MarketDataReadResult<MarketDataUpdate>.Success(update)
                : MarketDataReadResult<MarketDataUpdate>.Failure(error ?? new MarketDataError(
                    MarketDataProviderErrorCodes.MarketDataRequestFailed,
                    "Market-data snapshot request failed.")));
    }

    string GetGroupName(string symbol, string chartRange);
}
