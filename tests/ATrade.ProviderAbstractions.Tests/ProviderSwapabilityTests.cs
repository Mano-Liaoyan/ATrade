using ATrade.Brokers;
using ATrade.MarketData;

namespace ATrade.ProviderAbstractions.Tests;

public sealed class ProviderSwapabilityTests
{
    [Fact]
    public async Task BrokerEndpointContract_CanUseSwappedProviderStatus()
    {
        IBrokerProvider provider = new TestBrokerProvider();

        var status = await provider.GetStatusAsync(CancellationToken.None);

        Assert.Equal("test-broker", provider.Identity.Provider);
        Assert.Equal("test-broker", status.Provider);
        Assert.Equal(BrokerProviderStates.Authenticated, status.State);
        Assert.Equal(BrokerAccountModes.Paper, status.Mode);
        Assert.True(status.Capabilities.SupportsSessionStatus);
        Assert.False(status.Capabilities.SupportsBrokerOrderPlacement);
    }

    [Fact]
    public void MarketDataService_UsesSwappedProviderWithoutMockDependency()
    {
        var provider = new TestMarketDataProvider(MarketDataProviderStatus.Available(TestMarketDataProvider.ProviderIdentity, TestMarketDataProvider.ProviderCapabilities));
        var service = new MarketDataService(provider);

        var trending = service.GetTrendingSymbols();
        var searchResult = service.TrySearchSymbols("test", "stock", 5, out var search, out var searchError);
        var candlesResult = service.TryGetCandles("TEST", MarketDataTimeframes.OneDay, out var candles, out var error);

        Assert.Equal("test-market-data", provider.Identity.Provider);
        Assert.Single(trending.Symbols);
        Assert.True(searchResult);
        Assert.Null(searchError);
        var searchMatch = Assert.Single(search!.Results);
        Assert.Equal("test-market-data", searchMatch.Identity.Provider);
        Assert.Equal("provider-test-id", searchMatch.Identity.ProviderSymbolId);
        Assert.Equal("USD", searchMatch.Identity.Currency);
        Assert.True(candlesResult);
        Assert.Null(error);
        Assert.NotNull(candles);
        Assert.Equal("TEST", candles.Symbol);
        Assert.Equal(1, provider.TrendingCallCount);
        Assert.Equal(1, provider.SearchCallCount);
        Assert.Equal(1, provider.CandleCallCount);
    }

    [Fact]
    public void MarketDataService_ReturnsProviderNotConfiguredErrorWithoutFallback()
    {
        var provider = new TestMarketDataProvider(MarketDataProviderStatus.NotConfigured(
            TestMarketDataProvider.ProviderIdentity,
            TestMarketDataProvider.ProviderCapabilities,
            "Configure a market-data provider before requesting candles."));
        var service = new MarketDataService(provider);

        var result = service.TryGetCandles("TEST", MarketDataTimeframes.OneDay, out var candles, out var error);

        Assert.False(result);
        Assert.Null(candles);
        Assert.NotNull(error);
        Assert.Equal(MarketDataProviderErrorCodes.ProviderNotConfigured, error.Code);
        Assert.Equal(0, provider.CandleCallCount);
    }

    [Fact]
    public void MarketDataService_ValidatesSearchRequestsAndClampsLimitBeforeCallingProvider()
    {
        var provider = new TestMarketDataProvider(
            MarketDataProviderStatus.Available(TestMarketDataProvider.ProviderIdentity, TestMarketDataProvider.ProviderCapabilities),
            searchResultCount: MarketDataSymbolSearchLimits.MaximumLimit + 5);
        var service = new MarketDataService(provider);

        var tooShort = service.TrySearchSymbols("T", "stock", 5, out var tooShortResponse, out var tooShortError);
        var unsupportedAssetClass = service.TrySearchSymbols("TEST", "crypto", 5, out var unsupportedResponse, out var unsupportedError);
        var invalidLimit = service.TrySearchSymbols("TEST", "stock", 0, out var invalidLimitResponse, out var invalidLimitError);
        var clampedLimit = service.TrySearchSymbols("TEST", "stock", 999, out var clampedResponse, out var clampedError);

        Assert.False(tooShort);
        Assert.Null(tooShortResponse);
        Assert.Equal(MarketDataProviderErrorCodes.InvalidSearchQuery, tooShortError?.Code);
        Assert.False(unsupportedAssetClass);
        Assert.Null(unsupportedResponse);
        Assert.Equal(MarketDataProviderErrorCodes.UnsupportedAssetClass, unsupportedError?.Code);
        Assert.False(invalidLimit);
        Assert.Null(invalidLimitResponse);
        Assert.Equal(MarketDataProviderErrorCodes.InvalidSearchLimit, invalidLimitError?.Code);
        Assert.True(clampedLimit);
        Assert.Null(clampedError);
        Assert.Equal(MarketDataSymbolSearchLimits.MaximumLimit, clampedResponse!.Results.Count);
        Assert.Equal(1, provider.SearchCallCount);
    }

    private sealed class TestBrokerProvider : IBrokerProvider
    {
        public BrokerProviderIdentity Identity { get; } = BrokerProviderIdentity.Create("test-broker", "Test broker");

        public BrokerProviderCapabilities Capabilities { get; } = new(
            SupportsSessionStatus: true,
            SupportsReadOnlyMarketData: true,
            SupportsBrokerOrderPlacement: false,
            SupportsCredentialPersistence: false,
            SupportsExecutionPersistence: false,
            UsesOfficialApisOnly: true);

        public Task<BrokerProviderStatus> GetStatusAsync(CancellationToken cancellationToken = default)
        {
            var status = new BrokerProviderStatus(
                Identity.Provider,
                BrokerProviderStates.Authenticated,
                BrokerAccountModes.Paper,
                IntegrationEnabled: true,
                HasPaperAccountId: true,
                Authenticated: true,
                Connected: true,
                Competing: false,
                Message: "test provider ready",
                ObservedAtUtc: DateTimeOffset.UtcNow,
                Capabilities);

            return Task.FromResult(status);
        }
    }

    private sealed class TestMarketDataProvider(MarketDataProviderStatus status, int searchResultCount = 1) : IMarketDataProvider
    {
        public static MarketDataProviderIdentity ProviderIdentity { get; } = MarketDataProviderIdentity.Create("test-market-data", "Test market data");

        public static MarketDataProviderCapabilities ProviderCapabilities { get; } = new(
            SupportsTrendingScanner: true,
            SupportsHistoricalCandles: true,
            SupportsIndicators: true,
            SupportsStreamingSnapshots: true,
            SupportsSymbolSearch: true,
            UsesMockData: false);

        public int TrendingCallCount { get; private set; }

        public int SearchCallCount { get; private set; }

        public int CandleCallCount { get; private set; }

        public MarketDataProviderIdentity Identity => ProviderIdentity;

        public MarketDataProviderCapabilities Capabilities => ProviderCapabilities;

        public MarketDataProviderStatus GetStatus() => status;

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
                        "Stock",
                        "TESTEX",
                        "Testing",
                        101m,
                        1.25m,
                        99m,
                        new TrendingFactorBreakdown(1m, 1m, 1m, 0m),
                        new[] { "test provider result" }),
                });
        }

        public bool TrySearchSymbols(string query, out MarketDataSymbolSearchResponse? response, out MarketDataError? error)
        {
            SearchCallCount++;
            response = new MarketDataSymbolSearchResponse(
                DateTimeOffset.UtcNow,
                Enumerable.Range(1, searchResultCount)
                    .Select(index => new MarketDataSymbolSearchResult(
                        new MarketDataSymbolIdentity(
                            index == 1 ? "TEST" : $"TEST{index}",
                            Identity.Provider,
                            index == 1 ? "provider-test-id" : $"provider-test-id-{index}",
                            MarketDataAssetClasses.Stock,
                            "TESTEX",
                            "USD"),
                        index == 1 ? "Test Corp." : $"Test Corp. {index}",
                        "Testing"))
                    .ToArray(),
                Identity.Provider);
            error = null;
            return true;
        }

        public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol)
        {
            marketSymbol = new MarketDataSymbol("TEST", "Test Corp.", "Stock", "TESTEX", "Testing", 101m, 1.25m, 1_000_000);
            return true;
        }

        public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error)
        {
            CandleCallCount++;
            response = new CandleSeriesResponse(
                "TEST",
                MarketDataTimeframes.OneDay,
                DateTimeOffset.UtcNow,
                new[]
                {
                    new OhlcvCandle(DateTimeOffset.UtcNow.AddDays(-1), 100m, 102m, 99m, 101m, 1_000_000),
                });
            error = null;
            return true;
        }

        public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error)
        {
            response = new IndicatorResponse("TEST", MarketDataTimeframes.OneDay, Array.Empty<MovingAveragePoint>(), Array.Empty<RsiPoint>(), Array.Empty<MacdPoint>());
            error = null;
            return true;
        }

        public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error)
        {
            update = new MarketDataUpdate("TEST", MarketDataTimeframes.OneDay, DateTimeOffset.UtcNow, 100m, 102m, 99m, 101m, 1_000_000, 1.25m, Identity.Provider);
            error = null;
            return true;
        }
    }
}
