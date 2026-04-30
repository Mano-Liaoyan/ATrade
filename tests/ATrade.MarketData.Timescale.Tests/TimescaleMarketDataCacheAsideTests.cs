using ATrade.MarketData;
using Microsoft.Extensions.Logging.Abstractions;

namespace ATrade.MarketData.Timescale.Tests;

public sealed class TimescaleMarketDataCacheAsideTests
{
    [Fact]
    public void GetTrendingSymbolsReadsFreshTimescaleSnapshotBeforeProviderCall()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 10, 0, TimeSpan.Zero);
        var freshness = TimeSpan.FromMinutes(30);
        var repository = new RecordingTimescaleMarketDataRepository
        {
            TrendingSnapshot = CreateTrendingSnapshot(now.AddMinutes(-5), source: "ibkr-scanner"),
        };
        var provider = new RecordingMarketDataProvider
        {
            ThrowIfTrendingRequested = true,
        };
        var service = CreateService(provider, repository, now, freshness);

        var response = service.GetTrendingSymbols();

        Assert.Equal(0, provider.GetTrendingSymbolsCalls);
        var query = Assert.Single(repository.TrendingQueries);
        Assert.Equal(provider.Identity.Provider, query.Provider);
        Assert.Null(query.Source);
        Assert.Equal(now - freshness, query.FreshnessCutoffUtc);
        var symbol = Assert.Single(response.Symbols);
        Assert.Equal("AAPL", symbol.Symbol);
    }

    [Fact]
    public void GetTrendingSymbolsReturnsFreshPersistedSnapshotWithCacheSourceMetadata()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 12, 0, TimeSpan.Zero);
        var repository = new RecordingTimescaleMarketDataRepository
        {
            TrendingSnapshot = CreateTrendingSnapshot(now.AddMinutes(-3), source: "ibkr-scanner"),
        };
        var provider = new RecordingMarketDataProvider
        {
            ThrowIfTrendingRequested = true,
        };
        var service = CreateService(provider, repository, now, TimeSpan.FromMinutes(30));

        var response = service.GetTrendingSymbols();

        Assert.Equal("timescale-cache:ibkr-scanner", response.Source);
        Assert.Equal(now.AddMinutes(-3), response.GeneratedAt);
        var symbol = Assert.Single(response.Symbols);
        Assert.Equal("Apple Inc.", symbol.Name);
        Assert.Equal("NASDAQ", symbol.Exchange);
        Assert.Equal("Technology", symbol.Sector);
        Assert.Equal(91.5m, symbol.Score);
        Assert.Equal(["volume spike"], symbol.Reasons);
        Assert.Equal(0, provider.GetTrendingSymbolsCalls);
    }

    [Fact]
    public void GetTrendingSymbolsFetchesProviderPersistsSnapshotAndReturnsProviderResponseOnCacheMiss()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 14, 0, TimeSpan.Zero);
        var providerResponse = CreateProviderTrendingResponse(now.AddSeconds(-10), source: "ibkr-scanner");
        var repository = new RecordingTimescaleMarketDataRepository();
        var provider = new RecordingMarketDataProvider
        {
            TrendingResponse = providerResponse,
        };
        var service = CreateService(provider, repository, now, TimeSpan.FromMinutes(30));

        var response = service.GetTrendingSymbols();

        Assert.Same(providerResponse, response);
        Assert.Equal("ibkr-scanner", response.Source);
        Assert.Equal(1, provider.GetTrendingSymbolsCalls);
        Assert.Single(repository.TrendingQueries);
        var written = Assert.Single(repository.WrittenTrendingSnapshots);
        Assert.Equal(provider.Identity.Provider, written.Provider);
        Assert.Equal(providerResponse.Source, written.Source);
        Assert.Equal(providerResponse.GeneratedAt, written.GeneratedAtUtc);
        Assert.Equal(providerResponse.Symbols.Count, written.Symbols.Count);
        Assert.Equal("AAPL", Assert.Single(written.Symbols).Symbol.Symbol);
    }

    [Fact]
    public void GetTrendingSymbolsReturnsFreshCacheWhenProviderIsUnavailable()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 16, 0, TimeSpan.Zero);
        var repository = new RecordingTimescaleMarketDataRepository
        {
            TrendingSnapshot = CreateTrendingSnapshot(now.AddMinutes(-2), source: "ibkr-scanner"),
        };
        var provider = new RecordingMarketDataProvider
        {
            Status = MarketDataProviderStatus.Unavailable(
                MarketDataProviderIdentity.Create(RecordingMarketDataProvider.ProviderName, "Interactive Brokers"),
                RecordingMarketDataProvider.DefaultCapabilities,
                "iBeam is not reachable."),
            ThrowIfTrendingRequested = true,
        };
        var service = CreateService(provider, repository, now, TimeSpan.FromMinutes(30));

        var response = service.GetTrendingSymbols();

        Assert.Equal("timescale-cache:ibkr-scanner", response.Source);
        Assert.Equal(0, provider.GetTrendingSymbolsCalls);
        Assert.Single(repository.TrendingQueries);
    }

    [Fact]
    public void GetTrendingSymbolsSurfacesProviderUnavailableWhenNoFreshCacheExists()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 18, 0, TimeSpan.Zero);
        var repository = new RecordingTimescaleMarketDataRepository();
        var provider = new RecordingMarketDataProvider
        {
            Status = MarketDataProviderStatus.Unavailable(
                MarketDataProviderIdentity.Create(RecordingMarketDataProvider.ProviderName, "Interactive Brokers"),
                RecordingMarketDataProvider.DefaultCapabilities,
                "iBeam is not reachable."),
            ThrowIfTrendingRequested = true,
        };
        var service = CreateService(provider, repository, now, TimeSpan.FromMinutes(30));

        var exception = Assert.Throws<MarketDataProviderUnavailableException>(() => service.GetTrendingSymbols());

        Assert.Equal(MarketDataProviderErrorCodes.ProviderUnavailable, exception.Error.Code);
        Assert.Contains("iBeam", exception.Error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Equal(0, provider.GetTrendingSymbolsCalls);
        Assert.Equal(2, repository.TrendingQueries.Count);
        Assert.Empty(repository.WrittenTrendingSnapshots);
    }

    private static TimescaleCachedMarketDataService CreateService(
        RecordingMarketDataProvider provider,
        RecordingTimescaleMarketDataRepository repository,
        DateTimeOffset now,
        TimeSpan freshness)
    {
        return new TimescaleCachedMarketDataService(
            new MarketDataService(provider),
            provider,
            new RecordingSchemaInitializer(),
            repository,
            new TimescaleMarketDataOptions { CacheFreshnessPeriod = freshness },
            new IndicatorService(),
            new FixedTimeProvider(now),
            NullLogger<TimescaleCachedMarketDataService>.Instance);
    }

    private static TimescaleTrendingSnapshot CreateTrendingSnapshot(DateTimeOffset generatedAtUtc, string source) => new(
        Provider: RecordingMarketDataProvider.ProviderName,
        Source: source,
        GeneratedAtUtc: generatedAtUtc,
        Symbols:
        [
            new TimescaleTrendingSnapshotSymbol(
                new TimescaleMarketDataSymbol(
                    RecordingMarketDataProvider.ProviderName,
                    ProviderSymbolId: null,
                    Symbol: "AAPL",
                    Name: "Apple Inc.",
                    Exchange: "NASDAQ",
                    Currency: "USD",
                    AssetClass: MarketDataAssetClasses.Stock),
                Sector: "Technology",
                LastPrice: 190.12m,
                ChangePercent: 1.23m,
                Score: 91.5m,
                Factors: new TrendingFactorBreakdown(2.1m, 1.2m, 0.8m, 0.4m),
                Reasons: ["volume spike"]),
        ]);

    private static TrendingSymbolsResponse CreateProviderTrendingResponse(DateTimeOffset generatedAtUtc, string source) => new(
        generatedAtUtc,
        [
            new TrendingSymbol(
                "AAPL",
                "Apple Inc.",
                MarketDataAssetClasses.Stock,
                "NASDAQ",
                "Technology",
                190.12m,
                1.23m,
                91.5m,
                new TrendingFactorBreakdown(2.1m, 1.2m, 0.8m, 0.4m),
                ["volume spike"]),
        ],
        source);

    private sealed class RecordingSchemaInitializer : ITimescaleMarketDataSchemaInitializer
    {
        public int InitializeCalls { get; private set; }

        public Task InitializeAsync(CancellationToken cancellationToken = default)
        {
            InitializeCalls++;
            return Task.CompletedTask;
        }
    }

    private sealed class RecordingTimescaleMarketDataRepository : ITimescaleMarketDataRepository
    {
        public TimescaleTrendingSnapshot? TrendingSnapshot { get; init; }

        public List<TimescaleFreshTrendingSnapshotQuery> TrendingQueries { get; } = [];

        public List<TimescaleTrendingSnapshot> WrittenTrendingSnapshots { get; } = [];

        public Task UpsertCandleSeriesAsync(TimescaleCandleSeries series, CancellationToken cancellationToken = default) => Task.CompletedTask;

        public Task<TimescaleCandleSeries?> GetFreshCandleSeriesAsync(TimescaleFreshCandleSeriesQuery query, CancellationToken cancellationToken = default) => Task.FromResult<TimescaleCandleSeries?>(null);

        public Task UpsertTrendingSnapshotAsync(TimescaleTrendingSnapshot snapshot, CancellationToken cancellationToken = default)
        {
            WrittenTrendingSnapshots.Add(snapshot);
            return Task.CompletedTask;
        }

        public Task<TimescaleTrendingSnapshot?> GetFreshTrendingSnapshotAsync(TimescaleFreshTrendingSnapshotQuery query, CancellationToken cancellationToken = default)
        {
            TrendingQueries.Add(query);
            return Task.FromResult(TrendingSnapshot);
        }
    }

    private sealed class RecordingMarketDataProvider : IMarketDataProvider
    {
        public const string ProviderName = "ibkr";

        public static readonly MarketDataProviderCapabilities DefaultCapabilities = new(
            SupportsTrendingScanner: true,
            SupportsHistoricalCandles: true,
            SupportsIndicators: true,
            SupportsStreamingSnapshots: true,
            SupportsSymbolSearch: true,
            UsesMockData: false);

        public MarketDataProviderIdentity Identity { get; } = MarketDataProviderIdentity.Create(ProviderName, "Interactive Brokers");

        public MarketDataProviderCapabilities Capabilities => DefaultCapabilities;

        public bool ThrowIfTrendingRequested { get; init; }

        public TrendingSymbolsResponse? TrendingResponse { get; init; }

        public MarketDataProviderStatus? Status { get; init; }

        public int GetTrendingSymbolsCalls { get; private set; }

        public MarketDataProviderStatus GetStatus() => Status ?? MarketDataProviderStatus.Available(Identity, Capabilities);

        public TrendingSymbolsResponse GetTrendingSymbols()
        {
            GetTrendingSymbolsCalls++;
            if (ThrowIfTrendingRequested)
            {
                throw new InvalidOperationException("Provider should not be called when fresh Timescale trending data is available.");
            }

            return TrendingResponse ?? new TrendingSymbolsResponse(DateTimeOffset.UtcNow, [], "ibkr-scanner");
        }

        public bool TrySearchSymbols(string query, out MarketDataSymbolSearchResponse? response, out MarketDataError? error)
        {
            response = null;
            error = new MarketDataError(MarketDataProviderErrorCodes.SearchNotSupported, "Search is not needed by these tests.");
            return false;
        }

        public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol)
        {
            marketSymbol = null;
            return false;
        }

        public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error)
        {
            response = null;
            error = new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, "Candles are not needed by this test.");
            return false;
        }

        public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error)
        {
            response = null;
            error = new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, "Indicators are not needed by this test.");
            return false;
        }

        public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error)
        {
            update = null;
            error = new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, "Latest updates are not needed by this test.");
            return false;
        }
    }

    private sealed class FixedTimeProvider(DateTimeOffset utcNow) : TimeProvider
    {
        public override DateTimeOffset GetUtcNow() => utcNow;
    }
}
