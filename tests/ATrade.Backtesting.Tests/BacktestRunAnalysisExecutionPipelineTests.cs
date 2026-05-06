using System.Text.Json;
using ATrade.Analysis;
using ATrade.Backtesting;
using ATrade.MarketData;

namespace ATrade.Backtesting.Tests;

public sealed class BacktestRunAnalysisExecutionPipelineTests
{
    private static readonly DateTimeOffset ObservedAtUtc = new(2026, 5, 6, 14, 0, 0, TimeSpan.Zero);

    [Fact]
    public async Task ExecuteAsync_FetchesCandlesServerSideAndInvokesAnalysisWithSavedStrategy()
    {
        var run = Run();
        var candles = CandleSeries(run.Run.Request.Symbol, ChartRangePresets.SixMonths);
        var marketData = new FakeMarketDataService(MarketDataReadResult<CandleSeriesResponse>.Success(candles));
        var analysis = new CapturingAnalysisEngineRegistry(CompletedAnalysis(run.Run.Request.Symbol, candles));
        var pipeline = new BacktestRunAnalysisExecutionPipeline(marketData, analysis, new StaticTimeProvider(ObservedAtUtc));

        var result = await pipeline.ExecuteAsync(run);

        Assert.Equal(BacktestRunStatuses.Completed, result.Status);
        Assert.Null(result.Error);
        Assert.NotNull(result.Result);
        Assert.Equal(run.Run.Request.Symbol.Symbol, marketData.RequestedSymbol);
        Assert.Equal(run.Run.Request.ChartRange, marketData.RequestedChartRange);
        Assert.Equal(run.Run.Request.Symbol, marketData.RequestedIdentity);
        Assert.NotNull(analysis.Request);
        Assert.Equal(run.Run.Request.StrategyId, analysis.Request.StrategyName);
        Assert.Equal("lean", analysis.Request.EngineId);
        Assert.Equal(candles.Candles, analysis.Request.Bars);
        Assert.Equal(candles.Timeframe, analysis.Request.Timeframe);
        Assert.Equal(ObservedAtUtc, analysis.Request.RequestedAtUtc);

        var persistedResult = result.Result.Value;
        Assert.Equal("tp-060.backtest-result.v1", persistedResult.GetProperty("schemaVersion").GetString());
        Assert.Equal("completed", persistedResult.GetProperty("status").GetString());
        Assert.Equal(run.Run.Request.StrategyId, persistedResult.GetProperty("strategyId").GetString());
        Assert.Equal("lean", persistedResult.GetProperty("engine").GetProperty("engineId").GetString());
        Assert.True(persistedResult.GetProperty("metrics").GetArrayLength() > 0);
        Assert.True(persistedResult.GetProperty("signals").GetArrayLength() > 0);
        Assert.Equal("ibkr-ibeam-history", persistedResult.GetProperty("source").GetProperty("marketDataSource").GetString());
        Assert.DoesNotContain("workspace", persistedResult.GetRawText(), StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("/tmp", persistedResult.GetRawText(), StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("docker exec", persistedResult.GetRawText(), StringComparison.OrdinalIgnoreCase);
    }

    [Theory]
    [InlineData(MarketDataProviderErrorCodes.ProviderNotConfigured, "Market-data provider is not configured for backtest execution.")]
    [InlineData(MarketDataProviderErrorCodes.ProviderUnavailable, "Market-data provider is unavailable for backtest execution.")]
    [InlineData(MarketDataProviderErrorCodes.AuthenticationRequired, "Market-data provider authentication is required for backtest execution.")]
    public async Task ExecuteAsync_MapsMarketDataUnavailableStatesToFailedRuns(string providerCode, string expectedMessage)
    {
        var marketData = new FakeMarketDataService(MarketDataReadResult<CandleSeriesResponse>.Failure(new MarketDataError(
            providerCode,
            "unsafe provider detail should not be persisted")));
        var analysis = new CapturingAnalysisEngineRegistry(CompletedAnalysis(Run().Run.Request.Symbol, CandleSeries(Run().Run.Request.Symbol, ChartRangePresets.OneYear)));
        var pipeline = new BacktestRunAnalysisExecutionPipeline(marketData, analysis, new StaticTimeProvider(ObservedAtUtc));

        var result = await pipeline.ExecuteAsync(Run());

        Assert.Equal(BacktestRunStatuses.Failed, result.Status);
        Assert.Equal(providerCode, result.Error?.Code);
        Assert.Equal(expectedMessage, result.Error?.Message);
        Assert.Null(result.Result);
        Assert.Null(analysis.Request);
    }

    [Fact]
    public async Task ExecuteAsync_MapsEmptyCandlesToFailedRunWithoutFakeAnalysisSuccess()
    {
        var run = Run();
        var emptySeries = CandleSeries(run.Run.Request.Symbol, ChartRangePresets.OneYear) with
        {
            Candles = [],
        };
        var marketData = new FakeMarketDataService(MarketDataReadResult<CandleSeriesResponse>.Success(emptySeries));
        var analysis = new CapturingAnalysisEngineRegistry(CompletedAnalysis(run.Run.Request.Symbol, emptySeries));
        var pipeline = new BacktestRunAnalysisExecutionPipeline(marketData, analysis, new StaticTimeProvider(ObservedAtUtc));

        var result = await pipeline.ExecuteAsync(run);

        Assert.Equal(BacktestRunStatuses.Failed, result.Status);
        Assert.Equal(BacktestErrorCodes.MarketDataUnavailable, result.Error?.Code);
        Assert.Equal(BacktestSafeMessages.MarketDataUnavailable, result.Error?.Message);
        Assert.Null(analysis.Request);
    }

    [Theory]
    [InlineData(AnalysisEngineErrorCodes.EngineNotConfigured, "No analysis engine is configured for backtest execution.")]
    [InlineData(AnalysisEngineErrorCodes.EngineUnavailable, "Analysis engine is unavailable for backtest execution.")]
    [InlineData(AnalysisEngineErrorCodes.InvalidRequest, "Analysis engine rejected the saved backtest request.")]
    public async Task ExecuteAsync_MapsAnalysisUnavailableStatesToFailedRunsWithSafeMessages(string analysisCode, string expectedMessage)
    {
        var run = Run();
        var candles = CandleSeries(run.Run.Request.Symbol, ChartRangePresets.SixMonths);
        var marketData = new FakeMarketDataService(MarketDataReadResult<CandleSeriesResponse>.Success(candles));
        var analysis = new CapturingAnalysisEngineRegistry(FailedAnalysis(run.Run.Request.Symbol, candles, analysisCode));
        var pipeline = new BacktestRunAnalysisExecutionPipeline(marketData, analysis, new StaticTimeProvider(ObservedAtUtc));

        var result = await pipeline.ExecuteAsync(run);

        Assert.Equal(BacktestRunStatuses.Failed, result.Status);
        Assert.Equal(analysisCode, result.Error?.Code);
        Assert.Equal(expectedMessage, result.Error?.Message);
        Assert.Null(result.Result);
        Assert.NotNull(analysis.Request);
    }

    private static BacktestRunRecord Run() => new(
        new BacktestWorkspaceScope("local-user", "paper-workspace"),
        new BacktestRunEnvelope(
            Id: "bt_pipeline",
            Status: BacktestRunStatuses.Running,
            SourceRunId: null,
            Request: new BacktestRequestSnapshot(
                MarketDataSymbolIdentity.Create("AAPL", "ibkr", "265598", MarketDataAssetClasses.Stock, "NASDAQ", "USD"),
                BacktestStrategyIds.Breakout,
                new Dictionary<string, JsonElement>(StringComparer.Ordinal),
                ChartRangePresets.SixMonths,
                new BacktestCostModelSnapshot(0m, 0m, "USD"),
                SlippageBps: 0m,
                BacktestBenchmarkModes.None,
                EngineId: "lean"),
            Capital: new BacktestCapitalSnapshot(100000m, "USD", "local-paper-ledger"),
            CreatedAtUtc: ObservedAtUtc.AddMinutes(-5),
            UpdatedAtUtc: ObservedAtUtc,
            StartedAtUtc: ObservedAtUtc,
            CompletedAtUtc: null,
            Error: null,
            Result: null));

    private static CandleSeriesResponse CandleSeries(MarketDataSymbolIdentity identity, string chartRange) => new(
        identity.Symbol,
        chartRange,
        ObservedAtUtc,
        [
            new OhlcvCandle(ObservedAtUtc.AddDays(-2), 100m, 105m, 99m, 104m, 1_000_000),
            new OhlcvCandle(ObservedAtUtc.AddDays(-1), 104m, 108m, 103m, 107m, 1_100_000),
        ],
        Source: "ibkr-ibeam-history",
        Identity: identity);

    private static AnalysisResult CompletedAnalysis(MarketDataSymbolIdentity symbol, CandleSeriesResponse candles) => new(
        AnalysisResultStatuses.Completed,
        new AnalysisEngineMetadata("lean", "LEAN analysis engine", "LEAN", "official-runtime", AnalysisEngineStates.Available),
        new AnalysisDataSource("LEAN", "official LEAN CLI command 'lean'; project=atrade-analysis", ObservedAtUtc),
        symbol,
        candles.Timeframe,
        ObservedAtUtc,
        [new AnalysisSignal(ObservedAtUtc.AddDays(-1), "crossover", "long", 0.75m, "SMA crossover")],
        [new AnalysisMetric("totalReturnPercent", 1.5m, "%")],
        new BacktestSummary(
            ObservedAtUtc.AddDays(-2),
            ObservedAtUtc.AddDays(-1),
            InitialCapital: 100000m,
            FinalEquity: 101500m,
            TotalReturnPercent: 1.5m,
            TradeCount: 1,
            WinRatePercent: 100m),
        Error: null);

    private static AnalysisResult FailedAnalysis(MarketDataSymbolIdentity symbol, CandleSeriesResponse candles, string errorCode) => new(
        errorCode == AnalysisEngineErrorCodes.EngineNotConfigured ? AnalysisResultStatuses.NotConfigured : AnalysisResultStatuses.Failed,
        new AnalysisEngineMetadata("not-configured", "No engine", "none", "0.0.0", AnalysisEngineStates.NotConfigured),
        new AnalysisDataSource("none", "/tmp/lean-workspace should be redacted", ObservedAtUtc),
        symbol,
        candles.Timeframe,
        ObservedAtUtc,
        [],
        [],
        Backtest: null,
        new AnalysisError(errorCode, "unsafe /tmp/lean-workspace or docker exec detail should not be persisted"));

    private sealed class FakeMarketDataService(MarketDataReadResult<CandleSeriesResponse> candleResult) : IMarketDataService
    {
        public string? RequestedSymbol { get; private set; }

        public string? RequestedChartRange { get; private set; }

        public MarketDataSymbolIdentity? RequestedIdentity { get; private set; }

        public TrendingSymbolsResponse GetTrendingSymbols() => throw new NotSupportedException();

        public bool TrySearchSymbols(string? query, string? assetClass, int? limit, out MarketDataSymbolSearchResponse? response, out MarketDataError? error) =>
            throw new NotSupportedException();

        public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol) => throw new NotSupportedException();

        public bool TryGetCandles(
            string symbol,
            string? chartRange,
            out CandleSeriesResponse? response,
            out MarketDataError? error,
            MarketDataSymbolIdentity? identity = null) =>
            throw new NotSupportedException();

        public bool TryGetIndicators(
            string symbol,
            string? chartRange,
            out IndicatorResponse? response,
            out MarketDataError? error,
            MarketDataSymbolIdentity? identity = null) =>
            throw new NotSupportedException();

        public bool TryGetLatestUpdate(
            string symbol,
            string? chartRange,
            out MarketDataUpdate? update,
            out MarketDataError? error,
            MarketDataSymbolIdentity? identity = null) =>
            throw new NotSupportedException();

        public Task<MarketDataReadResult<CandleSeriesResponse>> GetCandlesAsync(
            string symbol,
            string? chartRange,
            MarketDataSymbolIdentity? identity = null,
            CancellationToken cancellationToken = default)
        {
            RequestedSymbol = symbol;
            RequestedChartRange = chartRange;
            RequestedIdentity = identity;
            return Task.FromResult(candleResult);
        }
    }

    private sealed class CapturingAnalysisEngineRegistry(AnalysisResult result) : IAnalysisEngineRegistry
    {
        public AnalysisRequest? Request { get; private set; }

        public IReadOnlyList<AnalysisEngineDescriptor> GetEngines() => [];

        public ValueTask<AnalysisResult> AnalyzeAsync(AnalysisRequest request, CancellationToken cancellationToken = default)
        {
            Request = request;
            return ValueTask.FromResult(result);
        }
    }

    private sealed class StaticTimeProvider(DateTimeOffset utcNow) : TimeProvider
    {
        public override DateTimeOffset GetUtcNow() => utcNow;
    }
}
