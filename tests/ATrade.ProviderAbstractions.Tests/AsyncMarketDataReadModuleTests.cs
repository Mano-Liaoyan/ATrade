using ATrade.MarketData;

namespace ATrade.ProviderAbstractions.Tests;

public sealed class AsyncMarketDataReadModuleTests
{
    [Fact]
    public async Task AsyncReadMethods_ReturnConsistentResultShapeForProviderSuccess()
    {
        var provider = new TestMarketDataProvider(MarketDataProviderStatus.Available(
            TestMarketDataProvider.ProviderIdentity,
            TestMarketDataProvider.ProviderCapabilities));
        var service = new MarketDataService(provider);

        var trending = await service.GetTrendingSymbolsAsync(CancellationToken.None);
        var search = await service.SearchSymbolsAsync("test", "stock", 5, CancellationToken.None);
        var symbol = await service.GetSymbolAsync("TEST", CancellationToken.None);
        var candles = await service.GetCandlesAsync("TEST", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
        var indicators = await service.GetIndicatorsAsync("TEST", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);
        var latest = await service.GetLatestUpdateAsync("TEST", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);

        Assert.True(trending.IsSuccess);
        Assert.Null(trending.Error);
        Assert.NotNull(trending.Value);
        Assert.Single(trending.Value!.Symbols);
        Assert.True(search.IsSuccess);
        Assert.Null(search.Error);
        Assert.NotNull(search.Value);
        Assert.Single(search.Value!.Results);
        Assert.True(symbol.IsSuccess);
        Assert.Equal("TEST", symbol.Value?.Symbol);
        Assert.True(candles.IsSuccess);
        Assert.Equal("TEST", candles.Value?.Symbol);
        Assert.True(indicators.IsSuccess);
        Assert.Equal("TEST", indicators.Value?.Symbol);
        Assert.True(latest.IsSuccess);
        Assert.Equal("TEST", latest.Value?.Symbol);
        Assert.Equal(6, provider.StatusCallCount);
        Assert.Equal(1, provider.TrendingCallCount);
        Assert.Equal(1, provider.SearchCallCount);
        Assert.Equal(1, provider.SymbolCallCount);
        Assert.Equal(1, provider.CandleCallCount);
        Assert.Equal(1, provider.IndicatorCallCount);
        Assert.Equal(1, provider.LatestUpdateCallCount);
    }

    [Fact]
    public async Task AsyncReadMethods_ReturnUnavailableResultWithoutCallingReadProvider()
    {
        var provider = new TestMarketDataProvider(MarketDataProviderStatus.NotConfigured(
            TestMarketDataProvider.ProviderIdentity,
            TestMarketDataProvider.ProviderCapabilities,
            "Configure a market-data provider before requesting candles."));
        var service = new MarketDataService(provider);

        var result = await service.GetCandlesAsync("TEST", MarketDataTimeframes.OneDay, cancellationToken: CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.NotNull(result.Error);
        Assert.Equal(MarketDataProviderErrorCodes.ProviderNotConfigured, result.Error!.Code);
        Assert.Equal(1, provider.StatusCallCount);
        Assert.Equal(0, provider.CandleCallCount);
    }

    [Fact]
    public async Task AsyncReadMethods_ReturnInvalidRequestResultBeforeProviderStatusCheck()
    {
        var provider = new TestMarketDataProvider(MarketDataProviderStatus.Available(
            TestMarketDataProvider.ProviderIdentity,
            TestMarketDataProvider.ProviderCapabilities));
        var service = new MarketDataService(provider);

        var result = await service.SearchSymbolsAsync("T", "stock", 5, CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.NotNull(result.Error);
        Assert.Equal(MarketDataProviderErrorCodes.InvalidSearchQuery, result.Error!.Code);
        Assert.Equal(0, provider.StatusCallCount);
        Assert.Equal(0, provider.SearchCallCount);
    }

    [Fact]
    public async Task AsyncReadMethods_HonorPreCanceledTokenBeforeProviderStatusCheck()
    {
        var provider = new TestMarketDataProvider(MarketDataProviderStatus.Available(
            TestMarketDataProvider.ProviderIdentity,
            TestMarketDataProvider.ProviderCapabilities));
        var service = new MarketDataService(provider);
        using var cancellation = new CancellationTokenSource();
        await cancellation.CancelAsync();

        await Assert.ThrowsAsync<OperationCanceledException>(() => service.GetTrendingSymbolsAsync(cancellation.Token));

        Assert.Equal(0, provider.StatusCallCount);
        Assert.Equal(0, provider.TrendingCallCount);
    }

    private sealed class TestMarketDataProvider(MarketDataProviderStatus status) : IMarketDataProvider
    {
        public static MarketDataProviderIdentity ProviderIdentity { get; } = MarketDataProviderIdentity.Create("test-market-data", "Test market data");

        public static MarketDataProviderCapabilities ProviderCapabilities { get; } = new(
            SupportsTrendingScanner: true,
            SupportsHistoricalCandles: true,
            SupportsIndicators: true,
            SupportsStreamingSnapshots: true,
            SupportsSymbolSearch: true,
            UsesMockData: false);

        public int StatusCallCount { get; private set; }

        public int TrendingCallCount { get; private set; }

        public int SearchCallCount { get; private set; }

        public int SymbolCallCount { get; private set; }

        public int CandleCallCount { get; private set; }

        public int IndicatorCallCount { get; private set; }

        public int LatestUpdateCallCount { get; private set; }

        public MarketDataProviderIdentity Identity => ProviderIdentity;

        public MarketDataProviderCapabilities Capabilities => ProviderCapabilities;

        public MarketDataProviderStatus GetStatus()
        {
            StatusCallCount++;
            return status;
        }

        public TrendingSymbolsResponse GetTrendingSymbols()
        {
            TrendingCallCount++;
            return new TrendingSymbolsResponse(
                DateTimeOffset.UtcNow,
                new[]
                {
                    new TrendingSymbol(
                        "TEST",
                        "Test Corp.",
                        MarketDataAssetClasses.Stock,
                        "TESTEX",
                        "Testing",
                        101m,
                        1.25m,
                        99m,
                        new TrendingFactorBreakdown(1m, 1m, 1m, 0m),
                        new[] { "test provider result" },
                        TestIdentity),
                },
                Identity.Provider);
        }

        public bool TrySearchSymbols(string query, out MarketDataSymbolSearchResponse? response, out MarketDataError? error)
        {
            SearchCallCount++;
            response = new MarketDataSymbolSearchResponse(
                DateTimeOffset.UtcNow,
                new[]
                {
                    new MarketDataSymbolSearchResult(TestIdentity, "Test Corp.", "Testing"),
                },
                Identity.Provider);
            error = null;
            return true;
        }

        public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol)
        {
            SymbolCallCount++;
            marketSymbol = new MarketDataSymbol("TEST", "Test Corp.", MarketDataAssetClasses.Stock, "TESTEX", "Testing", 101m, 1.25m, 1_000_000, TestIdentity);
            return true;
        }

        public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
        {
            CandleCallCount++;
            response = new CandleSeriesResponse(
                "TEST",
                MarketDataTimeframes.OneDay,
                DateTimeOffset.UtcNow,
                new[]
                {
                    TestCandle,
                },
                Identity.Provider,
                TestIdentity);
            error = null;
            return true;
        }

        public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
        {
            IndicatorCallCount++;
            response = new IndicatorResponse(
                "TEST",
                MarketDataTimeframes.OneDay,
                new[] { new MovingAveragePoint(TestCandle.Time, 100m, 100m) },
                new[] { new RsiPoint(TestCandle.Time, 50m) },
                new[] { new MacdPoint(TestCandle.Time, 0m, 0m, 0m) },
                Identity.Provider,
                TestIdentity);
            error = null;
            return true;
        }

        public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
        {
            LatestUpdateCallCount++;
            update = new MarketDataUpdate(
                "TEST",
                MarketDataTimeframes.OneDay,
                DateTimeOffset.UtcNow,
                100m,
                102m,
                99m,
                101m,
                1_000_000,
                1.25m,
                Identity.Provider,
                TestIdentity);
            error = null;
            return true;
        }

        private static MarketDataSymbolIdentity TestIdentity => MarketDataSymbolIdentity.Create(
            "TEST",
            ProviderIdentity.Provider,
            "provider-test-id",
            MarketDataAssetClasses.Stock,
            "TESTEX",
            "USD");

        private static OhlcvCandle TestCandle => new(DateTimeOffset.UtcNow.AddDays(-1), 100m, 102m, 99m, 101m, 1_000_000);
    }
}
