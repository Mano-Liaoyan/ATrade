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
        Assert.Equal(run.Run.Request.Parameters, analysis.Request.StrategyParameters);
        Assert.Equal(run.Run.Capital.InitialCapital, analysis.Request.BacktestSettings?.InitialCapital);
        Assert.Equal(run.Run.Request.CostModel.CommissionPerTrade, analysis.Request.BacktestSettings?.CommissionPerTrade);
        Assert.Equal(run.Run.Request.CostModel.CommissionBps, analysis.Request.BacktestSettings?.CommissionBps);
        Assert.Equal(run.Run.Request.SlippageBps, analysis.Request.BacktestSettings?.SlippageBps);
        Assert.Equal(candles.Candles, analysis.Request.Bars);
        Assert.Equal(candles.Timeframe, analysis.Request.Timeframe);
        Assert.Equal(ObservedAtUtc, analysis.Request.RequestedAtUtc);

        var persistedResult = result.Result.Value;
        Assert.Equal("tp-061.backtest-result.v1", persistedResult.GetProperty("schemaVersion").GetString());
        Assert.Equal("completed", persistedResult.GetProperty("status").GetString());
        Assert.Equal(run.Run.Request.StrategyId, persistedResult.GetProperty("strategyId").GetString());
        Assert.Equal(run.Run.Request.Parameters[BacktestStrategyParameterNames.BreakoutLookbackWindow].GetInt32(), persistedResult.GetProperty("parameters").GetProperty(BacktestStrategyParameterNames.BreakoutLookbackWindow).GetInt32());
        Assert.Equal("lean", persistedResult.GetProperty("engine").GetProperty("engineId").GetString());
        Assert.True(persistedResult.GetProperty("metrics").GetArrayLength() > 0);
        Assert.True(persistedResult.GetProperty("signals").GetArrayLength() > 0);
        Assert.True(persistedResult.GetProperty("equityCurve").GetArrayLength() > 0);
        Assert.True(persistedResult.GetProperty("trades").GetArrayLength() > 0);
        Assert.Equal(BacktestBenchmarkModes.BuyAndHold, persistedResult.GetProperty("benchmark").GetProperty("mode").GetString());
        Assert.Equal("Buy and hold", persistedResult.GetProperty("benchmark").GetProperty("label").GetString());
        Assert.Equal(run.Run.Request.SlippageBps, persistedResult.GetProperty("accounting").GetProperty("slippageBps").GetDecimal());
        Assert.Equal("ibkr-ibeam-history", persistedResult.GetProperty("source").GetProperty("marketDataSource").GetString());
        Assert.DoesNotContain("workspace", persistedResult.GetRawText(), StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("/tmp", persistedResult.GetRawText(), StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("docker exec", persistedResult.GetRawText(), StringComparison.OrdinalIgnoreCase);
    }

    [Theory]
    [InlineData(BacktestStrategyIds.SmaCrossover)]
    [InlineData(BacktestStrategyIds.RsiMeanReversion)]
    [InlineData(BacktestStrategyIds.Breakout)]
    public async Task ExecuteAsync_CompletesRichResultsForEachBuiltInStrategy(string strategyId)
    {
        var run = Run(strategyId);
        var candles = CandleSeries(run.Run.Request.Symbol, ChartRangePresets.SixMonths);
        var marketData = new FakeMarketDataService(MarketDataReadResult<CandleSeriesResponse>.Success(candles));
        var analysis = new CapturingAnalysisEngineRegistry(CompletedAnalysis(run.Run.Request.Symbol, candles));
        var pipeline = new BacktestRunAnalysisExecutionPipeline(marketData, analysis, new StaticTimeProvider(ObservedAtUtc));

        var result = await pipeline.ExecuteAsync(run);

        Assert.Equal(BacktestRunStatuses.Completed, result.Status);
        var persistedResult = result.Result!.Value;
        Assert.Equal(strategyId, persistedResult.GetProperty("strategyId").GetString());
        Assert.Equal(BacktestRunStatuses.Completed, persistedResult.GetProperty("status").GetString());
        Assert.True(persistedResult.GetProperty("backtest").GetProperty("finalEquity").GetDecimal() > 0m);
        Assert.True(persistedResult.GetProperty("equityCurve").GetArrayLength() > 0);
        Assert.True(persistedResult.GetProperty("trades").GetArrayLength() > 0);
        Assert.Equal(BacktestBenchmarkModes.BuyAndHold, persistedResult.GetProperty("benchmark").GetProperty("mode").GetString());
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

    private static BacktestRunRecord Run(string strategyId = BacktestStrategyIds.Breakout) => new(
        new BacktestWorkspaceScope("local-user", "paper-workspace"),
        new BacktestRunEnvelope(
            Id: "bt_pipeline",
            Status: BacktestRunStatuses.Running,
            SourceRunId: null,
            Request: new BacktestRequestSnapshot(
                MarketDataSymbolIdentity.Create("AAPL", "ibkr", "265598", MarketDataAssetClasses.Stock, "NASDAQ", "USD"),
                strategyId,
                DefaultParameters(strategyId),
                ChartRangePresets.SixMonths,
                new BacktestCostModelSnapshot(1.25m, 2.5m, "USD"),
                SlippageBps: 3.75m,
                BacktestBenchmarkModes.BuyAndHold,
                EngineId: "lean"),
            Capital: new BacktestCapitalSnapshot(100000m, "USD", "local-paper-ledger"),
            CreatedAtUtc: ObservedAtUtc.AddMinutes(-5),
            UpdatedAtUtc: ObservedAtUtc,
            StartedAtUtc: ObservedAtUtc,
            CompletedAtUtc: null,
            Error: null,
            Result: null));

    private static IReadOnlyDictionary<string, JsonElement> DefaultParameters(string strategyId) =>
        BacktestStrategyCatalog.CreateDefaultParameters(strategyId).ToDictionary(
            parameter => parameter.Key,
            parameter => parameter.Value.Clone(),
            StringComparer.Ordinal);

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
            WinRatePercent: 100m,
            MaxDrawdownPercent: 0.5m,
            TotalCost: 9.25m),
        Error: null,
        BacktestDetails: new AnalysisBacktestDetails(
            [
                new AnalysisEquityCurvePoint(ObservedAtUtc.AddDays(-2), 100000m, 0m),
                new AnalysisEquityCurvePoint(ObservedAtUtc.AddDays(-1), 101500m, 0m),
            ],
            [
                new AnalysisSimulatedTrade(
                    ObservedAtUtc.AddDays(-2),
                    ObservedAtUtc.AddDays(-1),
                    "long",
                    104m,
                    107m,
                    10m,
                    30m,
                    20.75m,
                    0.0208m,
                    9.25m,
                    "strategy-exit"),
            ],
            Benchmark: null,
            Accounting: new AnalysisBacktestAccounting(1.25m, 2.5m, 3.75m, "USD")));

    private static JsonElement Json(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.Clone();
    }

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
