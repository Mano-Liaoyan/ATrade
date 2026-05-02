using ATrade.MarketData;
using Microsoft.Extensions.Logging.Abstractions;

namespace ATrade.MarketData.Timescale.Tests;

public sealed class TimescaleMarketDataCacheAsideTests
{
    [Fact]
    public async Task GetTrendingSymbolsReadsFreshTimescaleSnapshotBeforeProviderCall()
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

        var result = await service.GetTrendingSymbolsAsync(CancellationToken.None);
        var response = result.Value;

        Assert.True(result.IsSuccess);
        Assert.NotNull(response);
        Assert.Equal(0, provider.GetTrendingSymbolsCalls);
        var query = Assert.Single(repository.TrendingQueries);
        Assert.Equal(provider.Identity.Provider, query.Provider);
        Assert.Null(query.Source);
        Assert.Equal(now - freshness, query.FreshnessCutoffUtc);
        var symbol = Assert.Single(response!.Symbols);
        Assert.Equal("AAPL", symbol.Symbol);
    }

    [Fact]
    public async Task GetTrendingSymbolsReturnsFreshPersistedSnapshotWithCacheSourceMetadata()
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

        var result = await service.GetTrendingSymbolsAsync(CancellationToken.None);
        var response = result.Value;

        Assert.True(result.IsSuccess);
        Assert.NotNull(response);
        Assert.Equal("timescale-cache:ibkr-scanner", response!.Source);
        Assert.Equal(now.AddMinutes(-3), response.GeneratedAt);
        var symbol = Assert.Single(response.Symbols);
        Assert.Equal("Apple Inc.", symbol.Name);
        Assert.Equal("NASDAQ", symbol.Exchange);
        Assert.Equal("Technology", symbol.Sector);
        Assert.NotNull(symbol.Identity);
        Assert.Equal("265598", symbol.Identity.ProviderSymbolId);
        Assert.Equal("NASDAQ", symbol.Identity.Exchange);
        Assert.Equal("USD", symbol.Identity.Currency);
        Assert.Equal(91.5m, symbol.Score);
        Assert.Equal(["volume spike"], symbol.Reasons);
        Assert.Equal(0, provider.GetTrendingSymbolsCalls);
    }

    [Fact]
    public async Task GetTrendingSymbolsFetchesProviderPersistsSnapshotAndReturnsProviderResponseOnCacheMiss()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 14, 0, TimeSpan.Zero);
        var providerResponse = CreateProviderTrendingResponse(now.AddSeconds(-10), source: "ibkr-scanner");
        var repository = new RecordingTimescaleMarketDataRepository();
        var provider = new RecordingMarketDataProvider
        {
            TrendingResponse = providerResponse,
        };
        var service = CreateService(provider, repository, now, TimeSpan.FromMinutes(30));

        var result = await service.GetTrendingSymbolsAsync(CancellationToken.None);
        var response = result.Value;

        Assert.True(result.IsSuccess);
        Assert.Same(providerResponse, response);
        Assert.Equal("ibkr-scanner", response.Source);
        Assert.Equal(1, provider.GetTrendingSymbolsCalls);
        Assert.Single(repository.TrendingQueries);
        var written = Assert.Single(repository.WrittenTrendingSnapshots);
        Assert.Equal(provider.Identity.Provider, written.Provider);
        Assert.Equal(providerResponse.Source, written.Source);
        Assert.Equal(providerResponse.GeneratedAt, written.GeneratedAtUtc);
        Assert.Equal(providerResponse.Symbols.Count, written.Symbols.Count);
        var writtenSymbol = Assert.Single(written.Symbols).Symbol;
        Assert.Equal("AAPL", writtenSymbol.Symbol);
        Assert.Equal("265598", writtenSymbol.ProviderSymbolId);
        Assert.Equal("NASDAQ", writtenSymbol.Exchange);
        Assert.Equal("USD", writtenSymbol.Currency);
    }

    [Fact]
    public async Task GetTrendingSymbolsReturnsFreshCacheWhenProviderIsUnavailable()
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

        var result = await service.GetTrendingSymbolsAsync(CancellationToken.None);
        var response = result.Value;

        Assert.True(result.IsSuccess);
        Assert.NotNull(response);
        Assert.Equal("timescale-cache:ibkr-scanner", response!.Source);
        Assert.Equal(0, provider.GetTrendingSymbolsCalls);
        Assert.Single(repository.TrendingQueries);
    }

    [Fact]
    public async Task GetTrendingSymbolsSurfacesProviderUnavailableWhenNoFreshCacheExists()
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

        var result = await service.GetTrendingSymbolsAsync(CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.NotNull(result.Error);
        Assert.Equal(MarketDataProviderErrorCodes.ProviderUnavailable, result.Error!.Code);
        Assert.Contains("iBeam", result.Error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Equal(0, provider.GetTrendingSymbolsCalls);
        Assert.Equal(2, repository.TrendingQueries.Count);
        Assert.Empty(repository.WrittenTrendingSnapshots);
    }

    [Fact]
    public async Task GetTrendingSymbolsServesPersistedSnapshotAcrossServiceInstances()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 32, 0, TimeSpan.Zero);
        var providerResponse = CreateProviderTrendingResponse(now.AddMinutes(-1), source: "ibkr-scanner");
        var repository = new RecordingTimescaleMarketDataRepository();
        var firstProvider = new RecordingMarketDataProvider
        {
            TrendingResponse = providerResponse,
        };
        var firstService = CreateService(firstProvider, repository, now, TimeSpan.FromMinutes(30));

        var providerRead = await firstService.GetTrendingSymbolsAsync(CancellationToken.None);
        var providerResult = providerRead.Value;
        repository.TrendingQueries.Clear();

        var restartedProvider = new RecordingMarketDataProvider
        {
            Status = MarketDataProviderStatus.Unavailable(
                MarketDataProviderIdentity.Create(RecordingMarketDataProvider.ProviderName, "Interactive Brokers"),
                RecordingMarketDataProvider.DefaultCapabilities,
                "iBeam is not reachable after restart."),
            ThrowIfTrendingRequested = true,
        };
        var restartedService = CreateService(restartedProvider, repository, now.AddMinutes(1), TimeSpan.FromMinutes(30));

        var restartedRead = await restartedService.GetTrendingSymbolsAsync(CancellationToken.None);
        var homePageTrending = restartedRead.Value;

        Assert.True(providerRead.IsSuccess);
        Assert.True(restartedRead.IsSuccess);
        Assert.NotNull(homePageTrending);
        Assert.Same(providerResponse, providerResult);
        Assert.Equal("timescale-cache:ibkr-scanner", homePageTrending.Source);
        Assert.Equal(providerResponse.GeneratedAt, homePageTrending.GeneratedAt);
        Assert.Equal("AAPL", Assert.Single(homePageTrending.Symbols).Symbol);
        Assert.Equal(0, restartedProvider.GetTrendingSymbolsCalls);
        Assert.Single(repository.TrendingQueries);
    }

    [Fact]
    public async Task TryGetCandlesReadsFreshTimescaleSeriesBeforeProviderCall()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 21, 0, TimeSpan.Zero);
        var freshness = TimeSpan.FromMinutes(30);
        var repository = new RecordingTimescaleMarketDataRepository
        {
            CandleSeries = CreateCandleSeries(now.AddMinutes(-4), source: "ibkr-history"),
        };
        var provider = new RecordingMarketDataProvider
        {
            ThrowIfCandlesRequested = true,
        };
        var service = CreateService(provider, repository, now, freshness);

        var result = await service.GetCandlesAsync(" aapl ", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
        var response = result.Value;

        Assert.True(result.IsSuccess);
        Assert.Null(result.Error);
        Assert.NotNull(response);
        Assert.Equal(0, provider.TryGetCandlesCalls);
        var query = Assert.Single(repository.CandleQueries);
        Assert.Equal(provider.Identity.Provider, query.Provider);
        Assert.Null(query.Source);
        Assert.Equal("AAPL", query.Symbol);
        Assert.Equal(MarketDataTimeframes.OneDay, query.Timeframe);
        Assert.Equal(now - freshness, query.FreshnessCutoffUtc);
        Assert.NotNull(response.Identity);
        Assert.Equal("265598", response.Identity.ProviderSymbolId);
        Assert.Equal("NASDAQ", response.Identity.Exchange);
        Assert.Equal("USD", response.Identity.Currency);
    }

    [Fact]
    public async Task TryGetCandlesUsesExactIdentityFiltersWhenProvided()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 22, 0, TimeSpan.Zero);
        var identity = CreateIdentity();
        var repository = new RecordingTimescaleMarketDataRepository
        {
            CandleSeries = CreateCandleSeries(now.AddMinutes(-4), source: "ibkr-history"),
        };
        var provider = new RecordingMarketDataProvider
        {
            ThrowIfCandlesRequested = true,
        };
        var service = CreateService(provider, repository, now, TimeSpan.FromMinutes(30));

        var result = await service.GetCandlesAsync("aapl", MarketDataTimeframes.OneDay, identity, CancellationToken.None);
        var response = result.Value;

        Assert.True(result.IsSuccess);
        Assert.Null(result.Error);
        Assert.NotNull(response);
        var query = Assert.Single(repository.CandleQueries);
        Assert.Equal("265598", query.ProviderSymbolId);
        Assert.Equal("NASDAQ", query.Exchange);
        Assert.Equal("USD", query.Currency);
        Assert.Equal(MarketDataAssetClasses.Stock, query.AssetClass);
    }

    [Fact]
    public async Task TryGetCandlesFetchesProviderPersistsSeriesAndReturnsProviderResponseOnCacheMiss()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 23, 0, TimeSpan.Zero);
        var providerResponse = CreateProviderCandleResponse(now.AddSeconds(-5), source: "ibkr-history");
        var repository = new RecordingTimescaleMarketDataRepository();
        var provider = new RecordingMarketDataProvider
        {
            CandleResponse = providerResponse,
        };
        var service = CreateService(provider, repository, now, TimeSpan.FromMinutes(30));

        var result = await service.GetCandlesAsync("AAPL", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
        var response = result.Value;

        Assert.True(result.IsSuccess);
        Assert.Null(result.Error);
        Assert.Same(providerResponse, response);
        Assert.Equal(1, provider.TryGetCandlesCalls);
        Assert.Single(repository.CandleQueries);
        var written = Assert.Single(repository.WrittenCandleSeries);
        Assert.Equal(provider.Identity.Provider, written.Symbol.Provider);
        Assert.Equal("AAPL", written.Symbol.Symbol);
        Assert.Equal(MarketDataTimeframes.OneDay, written.Timeframe);
        Assert.Equal(providerResponse.Source, written.Source);
        Assert.Equal(providerResponse.GeneratedAt, written.GeneratedAtUtc);
        Assert.Equal(providerResponse.Candles.Count, written.Candles.Count);
        Assert.Equal("265598", written.Symbol.ProviderSymbolId);
        Assert.Equal("NASDAQ", written.Symbol.Exchange);
        Assert.Equal("USD", written.Symbol.Currency);
    }

    [Fact]
    public async Task TryGetIndicatorsComputesFromFreshCachedCandlesWithoutProviderCall()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 25, 0, TimeSpan.Zero);
        var cachedSeries = CreateCandleSeries(now.AddMinutes(-6), source: "ibkr-history");
        var repository = new RecordingTimescaleMarketDataRepository
        {
            CandleSeries = cachedSeries,
        };
        var provider = new RecordingMarketDataProvider
        {
            ThrowIfCandlesRequested = true,
        };
        var service = CreateService(provider, repository, now, TimeSpan.FromMinutes(30));

        var result = await service.GetIndicatorsAsync("AAPL", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
        var response = result.Value;

        Assert.True(result.IsSuccess);
        Assert.Null(result.Error);
        Assert.NotNull(response);
        Assert.Equal("AAPL", response.Symbol);
        Assert.Equal(MarketDataTimeframes.OneDay, response.Timeframe);
        Assert.Equal("timescale-cache:ibkr-history", response.Source);
        Assert.NotNull(response.Identity);
        Assert.Equal("265598", response.Identity.ProviderSymbolId);
        Assert.Equal("NASDAQ", response.Identity.Exchange);
        Assert.Equal("USD", response.Identity.Currency);
        Assert.Equal(cachedSeries.Candles.Count, response.MovingAverages.Count);
        Assert.Equal(cachedSeries.Candles.Count, response.Rsi.Count);
        Assert.Equal(cachedSeries.Candles.Count, response.Macd.Count);
        Assert.Equal(0, provider.TryGetCandlesCalls);
        Assert.Equal(0, provider.TryGetIndicatorsCalls);
        Assert.Single(repository.CandleQueries);
        Assert.Empty(repository.WrittenCandleSeries);
    }

    [Fact]
    public async Task TryGetCandlesPreservesUnsupportedTimeframeErrorInsteadOfReturningCachedSeries()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 27, 0, TimeSpan.Zero);
        var repository = new RecordingTimescaleMarketDataRepository
        {
            CandleSeries = CreateCandleSeries(now.AddMinutes(-5), source: "ibkr-history"),
        };
        var provider = new RecordingMarketDataProvider
        {
            CandleError = new MarketDataError("unsupported-timeframe", "Timeframe '2m' is not supported."),
        };
        var service = CreateService(provider, repository, now, TimeSpan.FromMinutes(30));

        var result = await service.GetCandlesAsync("AAPL", "2m", cancellationToken: CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.NotNull(result.Error);
        Assert.Equal("unsupported-timeframe", result.Error!.Code);
        Assert.Equal(1, provider.TryGetCandlesCalls);
        Assert.Empty(repository.CandleQueries);
        Assert.Empty(repository.WrittenCandleSeries);
    }

    [Fact]
    public async Task TryGetCandlesPreservesProviderUnavailableWhenNoFreshCacheExists()
    {
        var now = new DateTimeOffset(2026, 4, 30, 17, 29, 0, TimeSpan.Zero);
        var repository = new RecordingTimescaleMarketDataRepository();
        var provider = new RecordingMarketDataProvider
        {
            Status = MarketDataProviderStatus.Unavailable(
                MarketDataProviderIdentity.Create(RecordingMarketDataProvider.ProviderName, "Interactive Brokers"),
                RecordingMarketDataProvider.DefaultCapabilities,
                "iBeam is not reachable."),
        };
        var service = CreateService(provider, repository, now, TimeSpan.FromMinutes(30));

        var result = await service.GetCandlesAsync("AAPL", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.NotNull(result.Error);
        Assert.Equal(MarketDataProviderErrorCodes.ProviderUnavailable, result.Error!.Code);
        Assert.Contains("iBeam", result.Error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Equal(0, provider.TryGetCandlesCalls);
        Assert.Single(repository.CandleQueries);
        Assert.Empty(repository.WrittenCandleSeries);
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
                    ProviderSymbolId: "265598",
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
                ["volume spike"],
                CreateIdentity()),
        ],
        source);

    private static TimescaleCandleSeries CreateCandleSeries(
        DateTimeOffset generatedAtUtc,
        string source,
        string symbol = "AAPL",
        string timeframe = MarketDataTimeframes.OneDay) => new(
        new TimescaleMarketDataSymbol(
            RecordingMarketDataProvider.ProviderName,
            ProviderSymbolId: "265598",
            Symbol: symbol,
            Name: "Apple Inc.",
            Exchange: "NASDAQ",
            Currency: "USD",
            AssetClass: MarketDataAssetClasses.Stock),
        timeframe,
        source,
        generatedAtUtc,
        CreateCandles(generatedAtUtc));

    private static CandleSeriesResponse CreateProviderCandleResponse(
        DateTimeOffset generatedAtUtc,
        string source,
        string symbol = "AAPL",
        string timeframe = MarketDataTimeframes.OneDay) => new(
        symbol,
        timeframe,
        generatedAtUtc,
        CreateCandles(generatedAtUtc),
        source,
        CreateIdentity(symbol));

    private static MarketDataSymbolIdentity CreateIdentity(string symbol = "AAPL") => MarketDataSymbolIdentity.Create(
        symbol,
        RecordingMarketDataProvider.ProviderName,
        "265598",
        MarketDataAssetClasses.Stock,
        "NASDAQ",
        "USD",
        ibkrConid: 265598);

    private static IReadOnlyList<OhlcvCandle> CreateCandles(DateTimeOffset generatedAtUtc) =>
    [
        new OhlcvCandle(generatedAtUtc.AddDays(-2), 180m, 185m, 179m, 184m, 10_000_000),
        new OhlcvCandle(generatedAtUtc.AddDays(-1), 184m, 188m, 183m, 187m, 11_000_000),
        new OhlcvCandle(generatedAtUtc, 187m, 191m, 186m, 190m, 12_000_000),
    ];

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
        public TimescaleTrendingSnapshot? TrendingSnapshot { get; set; }

        public TimescaleCandleSeries? CandleSeries { get; set; }

        public List<TimescaleFreshTrendingSnapshotQuery> TrendingQueries { get; } = [];

        public List<TimescaleFreshCandleSeriesQuery> CandleQueries { get; } = [];

        public List<TimescaleTrendingSnapshot> WrittenTrendingSnapshots { get; } = [];

        public List<TimescaleCandleSeries> WrittenCandleSeries { get; } = [];

        public Task UpsertCandleSeriesAsync(TimescaleCandleSeries series, CancellationToken cancellationToken = default)
        {
            WrittenCandleSeries.Add(series);
            CandleSeries = series;
            return Task.CompletedTask;
        }

        public Task<TimescaleCandleSeries?> GetFreshCandleSeriesAsync(TimescaleFreshCandleSeriesQuery query, CancellationToken cancellationToken = default)
        {
            CandleQueries.Add(query);
            return Task.FromResult(CandleSeries);
        }

        public Task UpsertTrendingSnapshotAsync(TimescaleTrendingSnapshot snapshot, CancellationToken cancellationToken = default)
        {
            WrittenTrendingSnapshots.Add(snapshot);
            TrendingSnapshot = snapshot;
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

        public bool ThrowIfCandlesRequested { get; init; }

        public TrendingSymbolsResponse? TrendingResponse { get; init; }

        public CandleSeriesResponse? CandleResponse { get; init; }

        public MarketDataError? CandleError { get; init; }

        public MarketDataProviderStatus? Status { get; init; }

        public int GetTrendingSymbolsCalls { get; private set; }

        public int TryGetCandlesCalls { get; private set; }

        public int TryGetIndicatorsCalls { get; private set; }

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

        public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
        {
            TryGetCandlesCalls++;
            if (ThrowIfCandlesRequested)
            {
                throw new InvalidOperationException("Provider should not be called when fresh Timescale candles are available.");
            }

            if (CandleResponse is not null)
            {
                response = CandleResponse;
                error = null;
                return true;
            }

            response = null;
            error = CandleError ?? new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, "Candles are not needed by this test.");
            return false;
        }

        public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
        {
            TryGetIndicatorsCalls++;
            response = null;
            error = new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, "Indicators are not needed by this test.");
            return false;
        }

        public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
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
