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

    public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
    {
        response = null;
        error = null;

        var normalizedIdentity = NormalizeIdentityForProvider(identity);
        var normalizedSymbol = NormalizeSymbol(normalizedIdentity?.Symbol ?? symbol);
        if (normalizedSymbol is not null
            && MarketDataTimeframes.TryGetDefinition(timeframe, out var definition)
            && TryGetCachedCandles(normalizedSymbol, definition.Name, normalizedIdentity, out response)
            && response is not null)
        {
            return true;
        }

        if (!providerBackedService.TryGetCandles(symbol, timeframe, out response, out error, normalizedIdentity) || response is null)
        {
            return false;
        }

        if (response.Identity is null && normalizedIdentity is not null)
        {
            response = response with { Identity = normalizedIdentity };
        }

        TryPersistCandleSeries(response);
        return true;
    }

    public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
    {
        response = null;
        if (!TryGetCandles(symbol, timeframe, out var candles, out error, identity) || candles is null)
        {
            return false;
        }

        response = indicatorService.Calculate(candles.Symbol, candles.Timeframe, candles.Candles, candles.Identity) with
        {
            Source = candles.Source,
        };
        error = null;
        return true;
    }

    public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null) =>
        providerBackedService.TryGetLatestUpdate(symbol, timeframe, out update, out error, NormalizeIdentityForProvider(identity));

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

    private bool TryGetCachedCandles(string symbol, string timeframe, MarketDataSymbolIdentity? identity, out CandleSeriesResponse? response)
    {
        response = null;
        var series = TryReadCache(
            "read fresh candle series",
            () => repository.GetFreshCandleSeriesAsync(new TimescaleFreshCandleSeriesQuery(
                provider.Identity.Provider,
                Source: null,
                symbol,
                timeframe,
                GetFreshnessCutoffUtc(),
                identity?.ProviderSymbolId,
                identity?.Exchange,
                identity?.Currency,
                identity?.AssetClass)));
        if (series is null)
        {
            return false;
        }

        response = new CandleSeriesResponse(
            series.Symbol.Symbol,
            series.Timeframe,
            series.GeneratedAtUtc,
            series.Candles,
            ToCacheSource(series.Source),
            series.Symbol.ToMarketDataSymbolIdentity());
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

    private static string? NormalizeSymbol(string? symbol) => string.IsNullOrWhiteSpace(symbol) ? null : symbol.Trim().ToUpperInvariant();
}
