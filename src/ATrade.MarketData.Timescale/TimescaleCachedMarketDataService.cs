using ATrade.MarketData;
using Microsoft.Extensions.Logging;

namespace ATrade.MarketData.Timescale;

public sealed class TimescaleCachedMarketDataService(
    MarketDataService providerBackedService,
    IMarketDataProvider provider,
    ITimescaleMarketDataSchemaInitializer schemaInitializer,
    ITimescaleMarketDataRepository repository,
    TimescaleMarketDataOptions options,
    IndicatorService indicatorService,
    TimeProvider timeProvider,
    ILogger<TimescaleCachedMarketDataService> logger) : IMarketDataService
{
    private const string CacheSourcePrefix = "timescale-cache";

    private readonly SemaphoreSlim schemaInitializationLock = new(1, 1);
    private bool schemaInitialized;

    public TrendingSymbolsResponse GetTrendingSymbols() =>
        throw new NotSupportedException("Synchronous Timescale market-data reads are no longer supported. Use GetTrendingSymbolsAsync.");

    public async Task<MarketDataReadResult<TrendingSymbolsResponse>> GetTrendingSymbolsAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var cachedResponse = await TryGetCachedTrendingSymbolsAsync(cancellationToken).ConfigureAwait(false);
        if (cachedResponse is not null)
        {
            return MarketDataReadResult<TrendingSymbolsResponse>.Success(cachedResponse);
        }

        var providerResponse = await providerBackedService.GetTrendingSymbolsAsync(cancellationToken).ConfigureAwait(false);
        if (providerResponse.IsSuccess && providerResponse.Value is not null)
        {
            await TryPersistTrendingSymbolsAsync(providerResponse.Value, cancellationToken).ConfigureAwait(false);
            return providerResponse;
        }

        cachedResponse = await TryGetCachedTrendingSymbolsAsync(cancellationToken).ConfigureAwait(false);
        return cachedResponse is not null
            ? MarketDataReadResult<TrendingSymbolsResponse>.Success(cachedResponse)
            : MarketDataReadResult<TrendingSymbolsResponse>.Failure(ToReadError(providerResponse.Error));
    }

    public bool TrySearchSymbols(string? query, string? assetClass, int? limit, out MarketDataSymbolSearchResponse? response, out MarketDataError? error) =>
        throw new NotSupportedException("Synchronous Timescale market-data search is no longer supported. Use SearchSymbolsAsync.");

    public Task<MarketDataReadResult<MarketDataSymbolSearchResponse>> SearchSymbolsAsync(
        string? query,
        string? assetClass,
        int? limit,
        CancellationToken cancellationToken = default) =>
        providerBackedService.SearchSymbolsAsync(query, assetClass, limit, cancellationToken);

    public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol) =>
        throw new NotSupportedException("Synchronous Timescale market-data symbol lookup is no longer supported. Use GetSymbolAsync.");

    public Task<MarketDataReadResult<MarketDataSymbol>> GetSymbolAsync(string symbol, CancellationToken cancellationToken = default) =>
        providerBackedService.GetSymbolAsync(symbol, cancellationToken);

    public bool TryGetCandles(string symbol, string? chartRange, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null) =>
        throw new NotSupportedException("Synchronous Timescale market-data candle reads are no longer supported. Use GetCandlesAsync.");

    public async Task<MarketDataReadResult<CandleSeriesResponse>> GetCandlesAsync(
        string symbol,
        string? chartRange,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var nowUtc = timeProvider.GetUtcNow().ToUniversalTime();
        if (!MarketDataTimeframes.TryGetDefinition(chartRange, nowUtc, out var definition))
        {
            return MarketDataReadResult<CandleSeriesResponse>.Failure(ChartRangePresets.CreateUnsupportedRangeError(chartRange));
        }

        var normalizedIdentity = NormalizeIdentityForProvider(identity);
        var normalizedSymbol = NormalizeSymbol(normalizedIdentity?.Symbol ?? symbol);
        if (normalizedSymbol is not null)
        {
            var cachedResponse = await TryGetCachedCandlesAsync(normalizedSymbol, definition, normalizedIdentity, nowUtc, cancellationToken).ConfigureAwait(false);
            if (cachedResponse is not null)
            {
                return MarketDataReadResult<CandleSeriesResponse>.Success(cachedResponse);
            }
        }

        var providerResponse = await providerBackedService.GetCandlesAsync(symbol, definition.Name, normalizedIdentity, cancellationToken).ConfigureAwait(false);
        if (providerResponse.IsFailure || providerResponse.Value is null)
        {
            return MarketDataReadResult<CandleSeriesResponse>.Failure(ToReadError(providerResponse.Error));
        }

        var response = providerResponse.Value;
        if (response.Identity is null && normalizedIdentity is not null)
        {
            response = response with { Identity = normalizedIdentity };
        }

        await TryPersistCandleSeriesAsync(response, cancellationToken).ConfigureAwait(false);
        return MarketDataReadResult<CandleSeriesResponse>.Success(response);
    }

    public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null) =>
        throw new NotSupportedException("Synchronous Timescale market-data indicator reads are no longer supported. Use GetIndicatorsAsync.");

    public async Task<MarketDataReadResult<IndicatorResponse>> GetIndicatorsAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var candles = await GetCandlesAsync(symbol, timeframe, identity, cancellationToken).ConfigureAwait(false);
        if (candles.IsFailure || candles.Value is null)
        {
            return MarketDataReadResult<IndicatorResponse>.Failure(ToReadError(candles.Error));
        }

        var response = indicatorService.Calculate(candles.Value.Symbol, candles.Value.Timeframe, candles.Value.Candles, candles.Value.Identity) with
        {
            Source = candles.Value.Source,
        };
        return MarketDataReadResult<IndicatorResponse>.Success(response);
    }

    public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null) =>
        throw new NotSupportedException("Synchronous Timescale market-data latest-update reads are no longer supported. Use GetLatestUpdateAsync.");

    public Task<MarketDataReadResult<MarketDataUpdate>> GetLatestUpdateAsync(
        string symbol,
        string? timeframe,
        MarketDataSymbolIdentity? identity = null,
        CancellationToken cancellationToken = default) =>
        providerBackedService.GetLatestUpdateAsync(symbol, timeframe, NormalizeIdentityForProvider(identity), cancellationToken);

    private async Task<TrendingSymbolsResponse?> TryGetCachedTrendingSymbolsAsync(CancellationToken cancellationToken)
    {
        var snapshot = await TryReadCacheAsync(
            "read fresh trending snapshot",
            token => repository.GetFreshTrendingSnapshotAsync(new TimescaleFreshTrendingSnapshotQuery(
                provider.Identity.Provider,
                Source: null,
                FreshnessCutoffUtc: GetFreshnessCutoffUtc()), token),
            cancellationToken).ConfigureAwait(false);
        if (snapshot is null)
        {
            return null;
        }

        return new TrendingSymbolsResponse(
            snapshot.GeneratedAtUtc,
            snapshot.Symbols.Select(ToTrendingSymbol).ToArray(),
            ToCacheSource(snapshot.Source));
    }

    private async Task<CandleSeriesResponse?> TryGetCachedCandlesAsync(
        string symbol,
        TimeframeDefinition definition,
        MarketDataSymbolIdentity? identity,
        DateTimeOffset nowUtc,
        CancellationToken cancellationToken)
    {
        var series = await TryReadCacheAsync(
            "read fresh candle series",
            token => repository.GetFreshCandleSeriesAsync(new TimescaleFreshCandleSeriesQuery(
                provider.Identity.Provider,
                Source: null,
                symbol,
                definition.Name,
                GetFreshnessCutoffUtc(),
                identity?.ProviderSymbolId,
                identity?.Exchange,
                identity?.Currency,
                identity?.AssetClass), token),
            cancellationToken).ConfigureAwait(false);
        if (series is null
            || !ChartRangePresets.TryNormalize(series.Timeframe, out var cachedChartRange)
            || !string.Equals(cachedChartRange, definition.Name, StringComparison.Ordinal)
            || !TrySelectLookbackCandles(series, definition, nowUtc, out var candles))
        {
            return null;
        }

        return new CandleSeriesResponse(
            series.Symbol.Symbol,
            definition.Name,
            series.GeneratedAtUtc,
            candles,
            ToCacheSource(series.Source),
            series.Symbol.ToMarketDataSymbolIdentity());
    }

    private Task TryPersistTrendingSymbolsAsync(TrendingSymbolsResponse response, CancellationToken cancellationToken)
    {
        var snapshot = new TimescaleTrendingSnapshot(
            provider.Identity.Provider,
            response.Source,
            response.GeneratedAt,
            response.Symbols.Select(ToTimescaleTrendingSymbol).ToArray());

        return TryWriteCacheAsync(
            "persist trending snapshot",
            token => repository.UpsertTrendingSnapshotAsync(snapshot, token),
            cancellationToken);
    }

    private Task TryPersistCandleSeriesAsync(CandleSeriesResponse response, CancellationToken cancellationToken)
    {
        var normalizedSymbol = NormalizeSymbol(response.Symbol);
        if (normalizedSymbol is null || response.Candles.Count == 0 || !ChartRangePresets.TryNormalize(response.Timeframe, out var normalizedChartRange))
        {
            return Task.CompletedTask;
        }

        var series = new TimescaleCandleSeries(
            response.Identity is null
                ? new TimescaleMarketDataSymbol(
                    provider.Identity.Provider,
                    ProviderSymbolId: null,
                    normalizedSymbol,
                    Name: null,
                    Exchange: null,
                    Currency: null,
                    AssetClass: null)
                : TimescaleMarketDataSymbol.FromIdentity(response.Identity),
            normalizedChartRange,
            response.Source,
            response.GeneratedAt,
            response.Candles);

        return TryWriteCacheAsync(
            "persist candle series",
            token => repository.UpsertCandleSeriesAsync(series, token),
            cancellationToken);
    }

    private static bool TrySelectLookbackCandles(
        TimescaleCandleSeries series,
        TimeframeDefinition definition,
        DateTimeOffset nowUtc,
        out IReadOnlyList<OhlcvCandle> candles)
    {
        var orderedCandles = series.Candles
            .Where(candle => IsWithinLookbackWindow(candle.Time, definition, nowUtc))
            .OrderBy(candle => candle.Time)
            .ToArray();
        if (orderedCandles.Length == 0 || !HasCompatibleCachedCandleCadence(orderedCandles, definition))
        {
            candles = Array.Empty<OhlcvCandle>();
            return false;
        }

        candles = definition.Name == ChartRangePresets.All
            ? orderedCandles
            : orderedCandles.TakeLast(definition.CandleCount).ToArray();
        return candles.Count > 0;
    }

    private static bool IsWithinLookbackWindow(DateTimeOffset candleTime, TimeframeDefinition definition, DateTimeOffset nowUtc)
    {
        var candleTimeUtc = candleTime.ToUniversalTime();
        var upperBoundUtc = nowUtc.ToUniversalTime();
        return candleTimeUtc <= upperBoundUtc && (definition.LookbackStartUtc is null || candleTimeUtc >= definition.LookbackStartUtc.Value);
    }

    private static bool HasCompatibleCachedCandleCadence(IReadOnlyList<OhlcvCandle> candles, TimeframeDefinition definition)
    {
        if (definition.Name == ChartRangePresets.All || definition.Step < TimeSpan.FromDays(1) || candles.Count < 2)
        {
            return true;
        }

        var minimumObservedGap = TimeSpan.MaxValue;
        for (var index = 1; index < candles.Count; index++)
        {
            var gap = candles[index].Time.ToUniversalTime() - candles[index - 1].Time.ToUniversalTime();
            if (gap > TimeSpan.Zero && gap < minimumObservedGap)
            {
                minimumObservedGap = gap;
            }
        }

        return minimumObservedGap == TimeSpan.MaxValue || minimumObservedGap >= TimeSpan.FromTicks(definition.Step.Ticks / 2);
    }

    private async Task<T?> TryReadCacheAsync<T>(string operation, Func<CancellationToken, Task<T?>> read, CancellationToken cancellationToken) where T : class
    {
        if (!await TryEnsureSchemaInitializedAsync(operation, cancellationToken).ConfigureAwait(false))
        {
            return null;
        }

        try
        {
            return await read(cancellationToken).ConfigureAwait(false);
        }
        catch (TimescaleMarketDataStorageUnavailableException exception)
        {
            logger.LogWarning(exception, "Timescale market-data cache {Operation} failed; continuing with provider-backed market data.", operation);
            return null;
        }
    }

    private async Task TryWriteCacheAsync(string operation, Func<CancellationToken, Task> write, CancellationToken cancellationToken)
    {
        if (!await TryEnsureSchemaInitializedAsync(operation, cancellationToken).ConfigureAwait(false))
        {
            return;
        }

        try
        {
            await write(cancellationToken).ConfigureAwait(false);
        }
        catch (TimescaleMarketDataStorageUnavailableException exception)
        {
            logger.LogWarning(exception, "Timescale market-data cache {Operation} failed; provider response will still be returned.", operation);
        }
    }

    private async Task<bool> TryEnsureSchemaInitializedAsync(string operation, CancellationToken cancellationToken)
    {
        if (schemaInitialized)
        {
            return true;
        }

        await schemaInitializationLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (schemaInitialized)
            {
                return true;
            }

            await schemaInitializer.InitializeAsync(cancellationToken).ConfigureAwait(false);
            schemaInitialized = true;
            return true;
        }
        catch (TimescaleMarketDataStorageUnavailableException exception)
        {
            logger.LogWarning(exception, "Timescale market-data schema initialization failed while attempting to {Operation}; continuing with provider-backed market data.", operation);
            return false;
        }
        finally
        {
            schemaInitializationLock.Release();
        }
    }

    private DateTimeOffset GetFreshnessCutoffUtc() => timeProvider.GetUtcNow().ToUniversalTime() - options.CacheFreshnessPeriod;

    private TimescaleTrendingSnapshotSymbol ToTimescaleTrendingSymbol(TrendingSymbol symbol) => new(
        new TimescaleMarketDataSymbol(
            provider.Identity.Provider,
            symbol.Identity?.ProviderSymbolId,
            NormalizeSymbol(symbol.Symbol) ?? symbol.Symbol,
            symbol.Name,
            symbol.Identity?.Exchange ?? symbol.Exchange,
            symbol.Identity?.Currency,
            symbol.Identity?.AssetClass ?? symbol.AssetClass),
        symbol.Sector,
        symbol.LastPrice,
        symbol.ChangePercent,
        symbol.Score,
        symbol.Factors,
        symbol.Reasons);

    private static TrendingSymbol ToTrendingSymbol(TimescaleTrendingSnapshotSymbol symbol)
    {
        var identity = symbol.Symbol.ToMarketDataSymbolIdentity();
        return new TrendingSymbol(
            symbol.Symbol.Symbol,
            symbol.Symbol.Name ?? symbol.Symbol.Symbol,
            symbol.Symbol.AssetClass ?? MarketDataAssetClasses.Stock,
            symbol.Symbol.Exchange ?? "UNKNOWN",
            symbol.Sector ?? string.Empty,
            symbol.LastPrice,
            symbol.ChangePercent,
            symbol.Score,
            symbol.Factors,
            symbol.Reasons,
            identity);
    }

    private static string ToCacheSource(string source)
    {
        var normalizedSource = string.IsNullOrWhiteSpace(source) ? "provider" : source.Trim();
        return $"{CacheSourcePrefix}:{normalizedSource}";
    }

    private MarketDataSymbolIdentity? NormalizeIdentityForProvider(MarketDataSymbolIdentity? identity)
    {
        if (identity is null || !string.Equals(identity.Provider, provider.Identity.Provider, StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        return identity.ToExactInstrumentIdentity().ToMarketDataSymbolIdentity();
    }

    private static MarketDataError ToReadError(MarketDataError? error) => error ?? new MarketDataError(
        MarketDataProviderErrorCodes.MarketDataRequestFailed,
        "Market-data request failed.");

    private static string? NormalizeSymbol(string? symbol) => string.IsNullOrWhiteSpace(symbol) ? null : symbol.Trim().ToUpperInvariant();
}
