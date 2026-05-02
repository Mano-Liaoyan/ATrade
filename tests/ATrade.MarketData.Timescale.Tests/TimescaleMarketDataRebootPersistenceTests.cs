using ATrade.MarketData;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;

namespace ATrade.MarketData.Timescale.Tests;

public sealed class TimescaleMarketDataRebootPersistenceTests
{
    private const string ConnectionStringEnvironmentVariable = "ATRADE_MARKET_DATA_TIMESCALE_TEST_CONNECTION_STRING";

    [Fact]
    public async Task FreshTrendingCacheSurvivesRepositoryAndServiceRecreationWithoutProviderCall()
    {
        var connectionString = Environment.GetEnvironmentVariable(ConnectionStringEnvironmentVariable);
        if (string.IsNullOrWhiteSpace(connectionString))
        {
            return;
        }

        var now = new DateTimeOffset(2026, 5, 1, 12, 0, 0, TimeSpan.Zero);
        var providerName = UniqueProviderName("trending");
        var symbol = UniqueSymbol("TPT");
        var source = UniqueSource("ibkr-scanner");
        var freshness = TimeSpan.FromMinutes(30);
        var providerResponse = CreateTrendingResponse(symbol, now.AddMinutes(-2), source);
        var writerProvider = RecordingMarketDataProvider.Available(providerName, trendingResponse: providerResponse);

        await using (var writerDataSource = CreateDataSourceProvider(connectionString))
        {
            var writerService = CreateService(writerProvider, writerDataSource, now, freshness);

            var firstRead = await writerService.GetTrendingSymbolsAsync(CancellationToken.None);
            var firstResponse = firstRead.Value;

            Assert.True(firstRead.IsSuccess);
            Assert.Same(providerResponse, firstResponse);
            Assert.Equal(1, writerProvider.GetTrendingSymbolsCalls);
        }

        var restartedProvider = RecordingMarketDataProvider.Unavailable(providerName, "iBeam is intentionally unavailable after restart") with
        {
            ThrowIfTrendingRequested = true,
        };
        await using var restartedDataSource = CreateDataSourceProvider(connectionString);
        var restartedService = CreateService(restartedProvider, restartedDataSource, now.AddMinutes(1), freshness);

        var restartedRead = await restartedService.GetTrendingSymbolsAsync(CancellationToken.None);
        var restartedResponse = restartedRead.Value;

        Assert.True(restartedRead.IsSuccess);
        Assert.NotNull(restartedResponse);
        Assert.Equal($"timescale-cache:{source}", restartedResponse!.Source);
        Assert.Equal(providerResponse.GeneratedAt, restartedResponse.GeneratedAt);
        var restartedSymbol = Assert.Single(restartedResponse.Symbols);
        Assert.Equal(symbol, restartedSymbol.Symbol);
        Assert.Equal(0, restartedProvider.GetTrendingSymbolsCalls);
    }

    [Fact]
    public async Task FreshCandleCacheSurvivesRepositoryAndServiceRecreationForCandlesAndIndicatorsWithoutProviderCall()
    {
        var connectionString = Environment.GetEnvironmentVariable(ConnectionStringEnvironmentVariable);
        if (string.IsNullOrWhiteSpace(connectionString))
        {
            return;
        }

        var now = new DateTimeOffset(2026, 5, 1, 13, 0, 0, TimeSpan.Zero);
        var providerName = UniqueProviderName("candles");
        var symbol = UniqueSymbol("TPC");
        var source = UniqueSource("ibkr-history");
        var freshness = TimeSpan.FromMinutes(30);
        var providerResponse = CreateCandleResponse(symbol, now.AddMinutes(-3), source);
        var writerProvider = RecordingMarketDataProvider.Available(providerName, candleResponse: providerResponse);

        await using (var writerDataSource = CreateDataSourceProvider(connectionString))
        {
            var writerService = CreateService(writerProvider, writerDataSource, now, freshness);

            var writeRead = await writerService.GetCandlesAsync(symbol, MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
            var firstResponse = writeRead.Value;

            Assert.True(writeRead.IsSuccess);
            Assert.Null(writeRead.Error);
            Assert.Same(providerResponse, firstResponse);
            Assert.Equal(1, writerProvider.TryGetCandlesCalls);
        }

        var restartedProvider = RecordingMarketDataProvider.Unavailable(providerName, "iBeam is intentionally unavailable after restart") with
        {
            ThrowIfCandlesRequested = true,
        };
        await using var restartedDataSource = CreateDataSourceProvider(connectionString);
        var restartedService = CreateService(restartedProvider, restartedDataSource, now.AddMinutes(1), freshness);

        var readCandles = await restartedService.GetCandlesAsync(symbol.ToLowerInvariant(), MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
        var restartedResponse = readCandles.Value;
        var readIndicators = await restartedService.GetIndicatorsAsync(symbol, MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
        var indicatorResponse = readIndicators.Value;

        Assert.True(readCandles.IsSuccess);
        Assert.Null(readCandles.Error);
        Assert.NotNull(restartedResponse);
        Assert.Equal($"timescale-cache:{source}", restartedResponse!.Source);
        Assert.Equal(providerResponse.GeneratedAt, restartedResponse.GeneratedAt);
        Assert.Equal(providerResponse.Candles.Count, restartedResponse.Candles.Count);
        Assert.True(readIndicators.IsSuccess);
        Assert.Null(readIndicators.Error);
        Assert.NotNull(indicatorResponse);
        Assert.Equal($"timescale-cache:{source}", indicatorResponse!.Source);
        Assert.Equal(providerResponse.Candles.Count, indicatorResponse.MovingAverages.Count);
        Assert.Equal(0, restartedProvider.TryGetCandlesCalls);
        Assert.Equal(0, restartedProvider.TryGetIndicatorsCalls);
    }

    [Fact]
    public async Task StalePersistedTrendingRowsAreNotServedWhenProviderIsUnavailableAfterRecreation()
    {
        var connectionString = Environment.GetEnvironmentVariable(ConnectionStringEnvironmentVariable);
        if (string.IsNullOrWhiteSpace(connectionString))
        {
            return;
        }

        var now = new DateTimeOffset(2026, 5, 1, 14, 0, 0, TimeSpan.Zero);
        var providerName = UniqueProviderName("stale");
        var symbol = UniqueSymbol("TPS");
        var source = UniqueSource("ibkr-scanner");
        var freshness = TimeSpan.FromMinutes(5);
        var staleResponse = CreateTrendingResponse(symbol, now.AddMinutes(-20), source);
        var writerProvider = RecordingMarketDataProvider.Available(providerName, trendingResponse: staleResponse);

        await using (var writerDataSource = CreateDataSourceProvider(connectionString))
        {
            var writerService = CreateService(writerProvider, writerDataSource, now, freshness);

            var providerRead = await writerService.GetTrendingSymbolsAsync(CancellationToken.None);
            var providerResult = providerRead.Value;

            Assert.True(providerRead.IsSuccess);
            Assert.Same(staleResponse, providerResult);
            Assert.Equal(1, writerProvider.GetTrendingSymbolsCalls);
        }

        var unavailableProvider = RecordingMarketDataProvider.Unavailable(providerName, "iBeam is unavailable and stale cache must not be promoted") with
        {
            ThrowIfTrendingRequested = true,
        };
        await using var restartedDataSource = CreateDataSourceProvider(connectionString);
        var restartedService = CreateService(unavailableProvider, restartedDataSource, now.AddMinutes(1), freshness);

        var restartedRead = await restartedService.GetTrendingSymbolsAsync(CancellationToken.None);

        Assert.True(restartedRead.IsFailure);
        Assert.Null(restartedRead.Value);
        Assert.NotNull(restartedRead.Error);
        Assert.Equal(MarketDataProviderErrorCodes.ProviderUnavailable, restartedRead.Error!.Code);
        Assert.Equal(0, unavailableProvider.GetTrendingSymbolsCalls);
    }

    private static TimescaleMarketDataDataSourceProvider CreateDataSourceProvider(string connectionString)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                [$"ConnectionStrings:{TimescaleMarketDataDataSourceProvider.DefaultConnectionStringName}"] = connectionString,
            })
            .Build();

        return new TimescaleMarketDataDataSourceProvider(configuration);
    }

    private static TimescaleCachedMarketDataService CreateService(
        RecordingMarketDataProvider provider,
        TimescaleMarketDataDataSourceProvider dataSourceProvider,
        DateTimeOffset now,
        TimeSpan freshness)
    {
        return new TimescaleCachedMarketDataService(
            new MarketDataService(provider),
            provider,
            new TimescaleMarketDataSchemaInitializer(dataSourceProvider),
            new TimescaleMarketDataRepository(dataSourceProvider, new FixedTimeProvider(now)),
            new TimescaleMarketDataOptions { CacheFreshnessPeriod = freshness },
            new IndicatorService(),
            new FixedTimeProvider(now),
            NullLogger<TimescaleCachedMarketDataService>.Instance);
    }

    private static TrendingSymbolsResponse CreateTrendingResponse(string symbol, DateTimeOffset generatedAtUtc, string source) => new(
        generatedAtUtc,
        [
            new TrendingSymbol(
                symbol,
                $"{symbol} Corp",
                MarketDataAssetClasses.Stock,
                "NASDAQ",
                "Technology",
                190.12m,
                1.23m,
                91.5m,
                new TrendingFactorBreakdown(2.1m, 1.2m, 0.8m, 0.4m),
                ["tp-035-reboot-persistence"]),
        ],
        source);

    private static CandleSeriesResponse CreateCandleResponse(string symbol, DateTimeOffset generatedAtUtc, string source) => new(
        symbol,
        MarketDataTimeframes.OneDay,
        generatedAtUtc,
        CreateCandles(generatedAtUtc),
        source);

    private static IReadOnlyList<OhlcvCandle> CreateCandles(DateTimeOffset generatedAtUtc) =>
    [
        new OhlcvCandle(generatedAtUtc.AddDays(-4), 180m, 185m, 179m, 184m, 10_000_000),
        new OhlcvCandle(generatedAtUtc.AddDays(-3), 184m, 188m, 183m, 187m, 11_000_000),
        new OhlcvCandle(generatedAtUtc.AddDays(-2), 187m, 191m, 186m, 190m, 12_000_000),
        new OhlcvCandle(generatedAtUtc.AddDays(-1), 190m, 194m, 189m, 193m, 13_000_000),
        new OhlcvCandle(generatedAtUtc, 193m, 197m, 192m, 196m, 14_000_000),
    ];

    private static string UniqueProviderName(string prefix) => $"tp035-{prefix}-{Guid.NewGuid():N}";

    private static string UniqueSource(string prefix) => $"{prefix}:tp035:{Guid.NewGuid():N}";

    private static string UniqueSymbol(string prefix) => $"{prefix}{Random.Shared.Next(1000, 9999)}";

    private sealed record RecordingMarketDataProvider(
        MarketDataProviderIdentity Identity,
        MarketDataProviderStatus Status,
        TrendingSymbolsResponse? TrendingResponse,
        CandleSeriesResponse? CandleResponse) : IMarketDataProvider
    {
        public static readonly MarketDataProviderCapabilities DefaultCapabilities = new(
            SupportsTrendingScanner: true,
            SupportsHistoricalCandles: true,
            SupportsIndicators: true,
            SupportsStreamingSnapshots: true,
            SupportsSymbolSearch: true,
            UsesMockData: false);

        public MarketDataProviderCapabilities Capabilities => DefaultCapabilities;

        public bool ThrowIfTrendingRequested { get; init; }

        public bool ThrowIfCandlesRequested { get; init; }

        public int GetTrendingSymbolsCalls { get; private set; }

        public int TryGetCandlesCalls { get; private set; }

        public int TryGetIndicatorsCalls { get; private set; }

        public static RecordingMarketDataProvider Available(
            string providerName,
            TrendingSymbolsResponse? trendingResponse = null,
            CandleSeriesResponse? candleResponse = null)
        {
            var identity = MarketDataProviderIdentity.Create(providerName, $"TP-035 {providerName}");
            return new RecordingMarketDataProvider(
                identity,
                MarketDataProviderStatus.Available(identity, DefaultCapabilities),
                trendingResponse,
                candleResponse);
        }

        public static RecordingMarketDataProvider Unavailable(string providerName, string message)
        {
            var identity = MarketDataProviderIdentity.Create(providerName, $"TP-035 {providerName}");
            return new RecordingMarketDataProvider(
                identity,
                MarketDataProviderStatus.Unavailable(identity, DefaultCapabilities, message),
                TrendingResponse: null,
                CandleResponse: null);
        }

        public MarketDataProviderStatus GetStatus() => Status;

        public TrendingSymbolsResponse GetTrendingSymbols()
        {
            GetTrendingSymbolsCalls++;
            if (ThrowIfTrendingRequested)
            {
                throw new InvalidOperationException("Provider should not be called when fresh Timescale trending data is available.");
            }

            return TrendingResponse ?? new TrendingSymbolsResponse(DateTimeOffset.UtcNow, [], "tp035-empty-trending");
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
            error = new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, "Candles are not needed by this test.");
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
