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

    public TrendingSymbolsResponse GetTrendingSymbols()
    {
        if (TryGetCachedTrendingSymbols(out var cachedResponse) && cachedResponse is not null)
        {
            return cachedResponse;
        }

        try
        {
            var providerResponse = providerBackedService.GetTrendingSymbols();
            TryPersistTrendingSymbols(providerResponse);
            return providerResponse;
        }
        catch (MarketDataProviderUnavailableException)
        {
            if (TryGetCachedTrendingSymbols(out cachedResponse) && cachedResponse is not null)
            {
                return cachedResponse;
            }

            throw;
        }
    }

    public bool TrySearchSymbols(string? query, string? assetClass, int? limit, out MarketDataSymbolSearchResponse? response, out MarketDataError? error) =>
        providerBackedService.TrySearchSymbols(query, assetClass, limit, out response, out error);

    public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol) =>
        providerBackedService.TryGetSymbol(symbol, out marketSymbol);

    public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error)
    {
        response = null;
        error = null;

        var normalizedSymbol = NormalizeSymbol(symbol);
        if (normalizedSymbol is not null
            && MarketDataTimeframes.TryGetDefinition(timeframe, out var definition)
            && TryGetCachedCandles(normalizedSymbol, definition.Name, out response)
            && response is not null)
        {
            return true;
        }

        if (!providerBackedService.TryGetCandles(symbol, timeframe, out response, out error) || response is null)
        {
            return false;
        }

        TryPersistCandleSeries(response);
        return true;
    }

    public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error)
    {
        response = null;
        if (!TryGetCandles(symbol, timeframe, out var candles, out error) || candles is null)
        {
            return false;
        }

        response = indicatorService.Calculate(candles.Symbol, candles.Timeframe, candles.Candles) with
        {
            Source = candles.Source,
        };
        error = null;
        return true;
    }

    public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error) =>
        providerBackedService.TryGetLatestUpdate(symbol, timeframe, out update, out error);

    private bool TryGetCachedTrendingSymbols(out TrendingSymbolsResponse? response)
    {
        response = null;
        var snapshot = TryReadCache(
            "read fresh trending snapshot",
            () => repository.GetFreshTrendingSnapshotAsync(new TimescaleFreshTrendingSnapshotQuery(
                provider.Identity.Provider,
                Source: null,
                FreshnessCutoffUtc: GetFreshnessCutoffUtc())));
        if (snapshot is null)
        {
            return false;
        }

        response = new TrendingSymbolsResponse(
            snapshot.GeneratedAtUtc,
            snapshot.Symbols.Select(ToTrendingSymbol).ToArray(),
            ToCacheSource(snapshot.Source));
        return true;
    }

    private bool TryGetCachedCandles(string symbol, string timeframe, out CandleSeriesResponse? response)
    {
        response = null;
        var series = TryReadCache(
            "read fresh candle series",
            () => repository.GetFreshCandleSeriesAsync(new TimescaleFreshCandleSeriesQuery(
                provider.Identity.Provider,
                Source: null,
                symbol,
                timeframe,
                GetFreshnessCutoffUtc())));
        if (series is null)
        {
            return false;
        }

        response = new CandleSeriesResponse(
            series.Symbol.Symbol,
            series.Timeframe,
            series.GeneratedAtUtc,
            series.Candles,
            ToCacheSource(series.Source));
        return true;
    }

    private void TryPersistTrendingSymbols(TrendingSymbolsResponse response)
    {
        var snapshot = new TimescaleTrendingSnapshot(
            provider.Identity.Provider,
            response.Source,
            response.GeneratedAt,
            response.Symbols.Select(ToTimescaleTrendingSymbol).ToArray());

        TryWriteCache(
            "persist trending snapshot",
            () => repository.UpsertTrendingSnapshotAsync(snapshot));
    }

    private void TryPersistCandleSeries(CandleSeriesResponse response)
    {
        var normalizedSymbol = NormalizeSymbol(response.Symbol);
        if (normalizedSymbol is null || response.Candles.Count == 0)
        {
            return;
        }

        var series = new TimescaleCandleSeries(
            new TimescaleMarketDataSymbol(
                provider.Identity.Provider,
                ProviderSymbolId: null,
                normalizedSymbol,
                Name: null,
                Exchange: null,
                Currency: null,
                AssetClass: null),
            response.Timeframe,
            response.Source,
            response.GeneratedAt,
            response.Candles);

        TryWriteCache(
            "persist candle series",
            () => repository.UpsertCandleSeriesAsync(series));
    }

    private T? TryReadCache<T>(string operation, Func<Task<T?>> read) where T : class
    {
        if (!TryEnsureSchemaInitialized(operation))
        {
            return null;
        }

        try
        {
            return read().GetAwaiter().GetResult();
        }
        catch (TimescaleMarketDataStorageUnavailableException exception)
        {
            logger.LogWarning(exception, "Timescale market-data cache {Operation} failed; continuing with provider-backed market data.", operation);
            return null;
        }
    }

    private void TryWriteCache(string operation, Func<Task> write)
    {
        if (!TryEnsureSchemaInitialized(operation))
        {
            return;
        }

        try
        {
            write().GetAwaiter().GetResult();
        }
        catch (TimescaleMarketDataStorageUnavailableException exception)
        {
            logger.LogWarning(exception, "Timescale market-data cache {Operation} failed; provider response will still be returned.", operation);
        }
    }

    private bool TryEnsureSchemaInitialized(string operation)
    {
        if (schemaInitialized)
        {
            return true;
        }

        schemaInitializationLock.Wait();
        try
        {
            if (schemaInitialized)
            {
                return true;
            }

            schemaInitializer.InitializeAsync().GetAwaiter().GetResult();
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
            ProviderSymbolId: null,
            NormalizeSymbol(symbol.Symbol) ?? symbol.Symbol,
            symbol.Name,
            symbol.Exchange,
            Currency: null,
            symbol.AssetClass),
        symbol.Sector,
        symbol.LastPrice,
        symbol.ChangePercent,
        symbol.Score,
        symbol.Factors,
        symbol.Reasons);

    private static TrendingSymbol ToTrendingSymbol(TimescaleTrendingSnapshotSymbol symbol) => new(
        symbol.Symbol.Symbol,
        symbol.Symbol.Name ?? symbol.Symbol.Symbol,
        symbol.Symbol.AssetClass ?? MarketDataAssetClasses.Stock,
        symbol.Symbol.Exchange ?? "UNKNOWN",
        symbol.Sector ?? string.Empty,
        symbol.LastPrice,
        symbol.ChangePercent,
        symbol.Score,
        symbol.Factors,
        symbol.Reasons);

    private static string ToCacheSource(string source)
    {
        var normalizedSource = string.IsNullOrWhiteSpace(source) ? "provider" : source.Trim();
        return $"{CacheSourcePrefix}:{normalizedSource}";
    }

    private static string? NormalizeSymbol(string? symbol) => string.IsNullOrWhiteSpace(symbol) ? null : symbol.Trim().ToUpperInvariant();
}
