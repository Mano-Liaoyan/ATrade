using ATrade.MarketData;

namespace ATrade.ProviderAbstractions.Tests;

public sealed class ChartRangePresetContractTests
{
    [Fact]
    public void SupportedPresets_ModelLookbacksFromNowForDayMonthAndSixMonths()
    {
        var nowUtc = new DateTimeOffset(2026, 5, 4, 15, 30, 0, TimeSpan.Zero);

        Assert.True(ChartRangePresets.TryGetPreset(ChartRangePresets.OneDay, out var oneDay));
        Assert.True(ChartRangePresets.TryGetPreset(ChartRangePresets.OneMonth, out var oneMonth));
        Assert.True(ChartRangePresets.TryGetPreset(ChartRangePresets.SixMonths, out var sixMonths));
        Assert.True(ChartRangePresets.TryGetPreset(ChartRangePresets.All, out var allTime));

        Assert.Equal(nowUtc.AddDays(-1), oneDay.GetLookbackStartUtc(nowUtc));
        Assert.Equal(nowUtc.AddMonths(-1), oneMonth.GetLookbackStartUtc(nowUtc));
        Assert.Equal(nowUtc.AddMonths(-6), sixMonths.GetLookbackStartUtc(nowUtc));
        Assert.Null(allTime.GetLookbackStartUtc(nowUtc));
        Assert.True(allTime.IsAllTime);
    }

    [Fact]
    public void SupportedPresets_UseUnambiguousMinuteLabelsAndMonthRangeValue()
    {
        var supported = ChartRangePresets.Supported;

        Assert.Equal(
            new[] { "1min", "5mins", "1h", "6h", "1D", "1m", "6m", "1y", "5y", "all" },
            supported);
        Assert.Equal("1min", MarketDataTimeframes.OneMinute);
        Assert.Equal("5mins", MarketDataTimeframes.FiveMinutes);
        Assert.Equal("1m", MarketDataTimeframes.OneMonth);
        Assert.DoesNotContain("5m", supported);

        var displayLabels = ChartRangePresets.AllPresets.Select(preset => preset.DisplayLabel).ToArray();
        Assert.Contains("1min", displayLabels);
        Assert.Contains("5mins", displayLabels);
        Assert.Contains("All time", displayLabels);
    }

    [Fact]
    public void UnsupportedRange_ProducesClearSupportedValuesError()
    {
        var error = ChartRangePresets.CreateUnsupportedRangeError("5m");

        Assert.Equal(MarketDataProviderErrorCodes.UnsupportedChartRange, error.Code);
        Assert.Contains("Chart range '5m' is not supported.", error.Message);
        Assert.Contains("Supported values: 1min, 5mins, 1h, 6h, 1D, 1m, 6m, 1y, 5y, all.", error.Message);
    }

    [Fact]
    public async Task MarketDataService_NormalizesChartRangesBeforeProviderCalls()
    {
        var provider = new CapturingMarketDataProvider();
        var service = new MarketDataService(provider);

        var monthResult = await service.GetCandlesAsync("TEST", " 1m ", cancellationToken: CancellationToken.None);
        var defaultResult = await service.GetLatestUpdateAsync("TEST", null, cancellationToken: CancellationToken.None);

        Assert.True(monthResult.IsSuccess);
        Assert.Equal(ChartRangePresets.OneMonth, provider.LastCandleRange);
        Assert.Equal(ChartRangePresets.OneMonth, monthResult.Value!.Timeframe);
        Assert.True(defaultResult.IsSuccess);
        Assert.Equal(ChartRangePresets.Default, provider.LastLatestUpdateRange);
        Assert.Equal(ChartRangePresets.Default, defaultResult.Value!.Timeframe);
    }

    [Fact]
    public async Task MarketDataService_RejectsUnsupportedChartRangesBeforeProviderStatusCheck()
    {
        var provider = new CapturingMarketDataProvider();
        var service = new MarketDataService(provider);

        var result = await service.GetCandlesAsync("TEST", "5m", cancellationToken: CancellationToken.None);

        Assert.True(result.IsFailure);
        Assert.Null(result.Value);
        Assert.Equal(MarketDataProviderErrorCodes.UnsupportedChartRange, result.Error?.Code);
        Assert.Contains("1min, 5mins", result.Error?.Message);
        Assert.Equal(0, provider.StatusCallCount);
        Assert.Null(provider.LastCandleRange);
    }

    private sealed class CapturingMarketDataProvider : IMarketDataProvider
    {
        private static readonly MarketDataProviderIdentity ProviderIdentity = MarketDataProviderIdentity.Create("test-market-data", "Test market data");
        private static readonly MarketDataProviderCapabilities ProviderCapabilities = new(
            SupportsTrendingScanner: true,
            SupportsHistoricalCandles: true,
            SupportsIndicators: true,
            SupportsStreamingSnapshots: true,
            SupportsSymbolSearch: true,
            UsesMockData: false);

        public int StatusCallCount { get; private set; }

        public string? LastCandleRange { get; private set; }

        public string? LastLatestUpdateRange { get; private set; }

        public MarketDataProviderIdentity Identity => ProviderIdentity;

        public MarketDataProviderCapabilities Capabilities => ProviderCapabilities;

        public MarketDataProviderStatus GetStatus()
        {
            StatusCallCount++;
            return MarketDataProviderStatus.Available(Identity, Capabilities);
        }

        public TrendingSymbolsResponse GetTrendingSymbols() => new(DateTimeOffset.UtcNow, Array.Empty<TrendingSymbol>(), Identity.Provider);

        public bool TrySearchSymbols(string query, out MarketDataSymbolSearchResponse? response, out MarketDataError? error)
        {
            response = new MarketDataSymbolSearchResponse(DateTimeOffset.UtcNow, Array.Empty<MarketDataSymbolSearchResult>(), Identity.Provider);
            error = null;
            return true;
        }

        public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol)
        {
            marketSymbol = new MarketDataSymbol("TEST", "Test Corp.", MarketDataAssetClasses.Stock, "TESTEX", "Testing", 100m, 0m, 1_000_000);
            return true;
        }

        public bool TryGetCandles(string symbol, string? chartRange, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
        {
            LastCandleRange = chartRange;
            response = new CandleSeriesResponse(
                "TEST",
                chartRange ?? ChartRangePresets.Default,
                DateTimeOffset.UtcNow,
                new[] { new OhlcvCandle(DateTimeOffset.UtcNow.AddMinutes(-1), 100m, 101m, 99m, 100.5m, 1_000) },
                Identity.Provider);
            error = null;
            return true;
        }

        public bool TryGetIndicators(string symbol, string? chartRange, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
        {
            response = new IndicatorResponse("TEST", chartRange ?? ChartRangePresets.Default, Array.Empty<MovingAveragePoint>(), Array.Empty<RsiPoint>(), Array.Empty<MacdPoint>(), Identity.Provider);
            error = null;
            return true;
        }

        public bool TryGetLatestUpdate(string symbol, string? chartRange, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null)
        {
            LastLatestUpdateRange = chartRange;
            update = new MarketDataUpdate("TEST", chartRange ?? ChartRangePresets.Default, DateTimeOffset.UtcNow, 100m, 101m, 99m, 100.5m, 1_000, 0.5m, Identity.Provider);
            error = null;
            return true;
        }
    }
}
