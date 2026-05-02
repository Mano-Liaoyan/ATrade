using ATrade.Analysis;
using ATrade.MarketData;

namespace ATrade.Analysis.Tests;

public sealed class AnalysisRequestIntakeTests
{
    [Fact]
    public async Task DirectBarsUseSuppliedSymbolDefaultsAndEngineHandoff()
    {
        var symbol = CreateIdentity("AAPL", "ibkr", "265598");
        var bar = CreateBar(0);
        var requestedAt = new DateTimeOffset(2026, 5, 2, 12, 0, 0, TimeSpan.Zero);
        var marketData = new FakeMarketDataService();
        var registry = new CapturingAnalysisEngineRegistry();
        var intake = new AnalysisRequestIntake(marketData, registry);

        var result = await intake.RunAsync(new AnalysisRunRequest(
            symbol,
            SymbolCode: null,
            Timeframe: " 1h ",
            requestedAt,
            new[] { bar },
            EngineId: "lean",
            StrategyName: "breakout"));

        Assert.True(result.IsSuccess);
        Assert.Null(result.InvalidRequestError);
        Assert.Null(result.MarketDataError);
        Assert.Empty(marketData.CandleRequests);
        Assert.NotNull(registry.LastRequest);
        Assert.Equal(symbol, registry.LastRequest.Symbol);
        Assert.Equal(MarketDataTimeframes.OneHour, registry.LastRequest.Timeframe);
        Assert.Equal(requestedAt, registry.LastRequest.RequestedAtUtc);
        Assert.Equal("lean", registry.LastRequest.EngineId);
        Assert.Equal("breakout", registry.LastRequest.StrategyName);
        Assert.Equal(bar, Assert.Single(registry.LastRequest.Bars));
        Assert.Equal(AnalysisResultStatuses.Completed, result.Result?.Status);
    }

    [Fact]
    public async Task MissingBarsAcquireCandlesAndResolveSymbolIdentityThroughMarketDataReadSeam()
    {
        var resolvedIdentity = CreateIdentity("MSFT", "ibkr", "272093");
        var candles = new[] { CreateBar(0), CreateBar(1) };
        var marketData = new FakeMarketDataService
        {
            CandleHandler = (symbol, timeframe, identity, _) =>
            {
                Assert.Equal("MSFT", symbol);
                Assert.Equal(MarketDataTimeframes.OneDay, timeframe);
                Assert.Null(identity);
                return Task.FromResult(MarketDataReadResult<CandleSeriesResponse>.Success(new CandleSeriesResponse(
                    "MSFT",
                    MarketDataTimeframes.FiveMinutes,
                    new DateTimeOffset(2026, 5, 2, 12, 5, 0, TimeSpan.Zero),
                    candles,
                    Source: "unit-provider")));
            },
            SymbolHandler = (symbol, _) =>
            {
                Assert.Equal("MSFT", symbol);
                return Task.FromResult(MarketDataReadResult<MarketDataSymbol>.Success(new MarketDataSymbol(
                    "MSFT",
                    "Microsoft Corp.",
                    MarketDataAssetClasses.Stock,
                    "NASDAQ",
                    "Technology",
                    LastPrice: 420m,
                    ChangePercent: 1.2m,
                    AverageVolume: 12_000_000,
                    resolvedIdentity)));
            },
        };
        var registry = new CapturingAnalysisEngineRegistry();
        var intake = new AnalysisRequestIntake(marketData, registry);

        var result = await intake.RunAsync(new AnalysisRunRequest(
            Symbol: null,
            SymbolCode: "MSFT",
            Timeframe: null,
            RequestedAtUtc: null,
            Bars: null,
            EngineId: null,
            StrategyName: null));

        Assert.True(result.IsSuccess);
        Assert.Single(marketData.CandleRequests);
        Assert.Equal(new[] { "MSFT" }, marketData.SymbolRequests);
        Assert.NotNull(registry.LastRequest);
        Assert.Equal(resolvedIdentity, registry.LastRequest.Symbol);
        Assert.Equal(MarketDataTimeframes.FiveMinutes, registry.LastRequest.Timeframe);
        Assert.Equal(candles, registry.LastRequest.Bars);
    }

    [Fact]
    public async Task ProviderErrorsAreReturnedWithoutCallingAnalysisEngine()
    {
        var providerError = new MarketDataError(MarketDataProviderErrorCodes.ProviderUnavailable, "Provider offline.");
        var marketData = new FakeMarketDataService
        {
            CandleHandler = (_, _, _, _) => Task.FromResult(MarketDataReadResult<CandleSeriesResponse>.Failure(providerError)),
        };
        var registry = new CapturingAnalysisEngineRegistry();
        var intake = new AnalysisRequestIntake(marketData, registry);

        var result = await intake.RunAsync(new AnalysisRunRequest(
            Symbol: null,
            SymbolCode: "AAPL",
            Timeframe: MarketDataTimeframes.OneDay,
            RequestedAtUtc: null,
            Bars: null,
            EngineId: null,
            StrategyName: null));

        Assert.False(result.IsSuccess);
        Assert.Equal(providerError, result.MarketDataError);
        Assert.Null(result.InvalidRequestError);
        Assert.Null(registry.LastRequest);
    }

    [Fact]
    public async Task InvalidPayloadsAreMappedBeforeMarketDataAndEngineCalls()
    {
        var marketData = new FakeMarketDataService();
        var registry = new CapturingAnalysisEngineRegistry();
        var intake = new AnalysisRequestIntake(marketData, registry);

        var nullResult = await intake.RunAsync(null);
        var missingSymbolResult = await intake.RunAsync(new AnalysisRunRequest(
            Symbol: null,
            SymbolCode: " ",
            Timeframe: null,
            RequestedAtUtc: null,
            Bars: null,
            EngineId: null,
            StrategyName: null));

        Assert.Equal(AnalysisEngineErrorCodes.InvalidRequest, nullResult.InvalidRequestError?.Code);
        Assert.Contains("payload", nullResult.InvalidRequestError?.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Equal(AnalysisEngineErrorCodes.InvalidRequest, missingSymbolResult.InvalidRequestError?.Code);
        Assert.Contains("symbol", missingSymbolResult.InvalidRequestError?.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Empty(marketData.CandleRequests);
        Assert.Null(registry.LastRequest);
    }

    [Fact]
    public async Task EmptyProviderCandlesAreMappedToInvalidRequest()
    {
        var marketData = new FakeMarketDataService
        {
            CandleHandler = (_, _, _, _) => Task.FromResult(MarketDataReadResult<CandleSeriesResponse>.Success(new CandleSeriesResponse(
                "AAPL",
                MarketDataTimeframes.OneDay,
                DateTimeOffset.UtcNow,
                Array.Empty<OhlcvCandle>(),
                Source: "unit-provider"))),
        };
        var registry = new CapturingAnalysisEngineRegistry();
        var intake = new AnalysisRequestIntake(marketData, registry);

        var result = await intake.RunAsync(new AnalysisRunRequest(
            Symbol: null,
            SymbolCode: "AAPL",
            Timeframe: MarketDataTimeframes.OneDay,
            RequestedAtUtc: null,
            Bars: null,
            EngineId: null,
            StrategyName: null));

        Assert.False(result.IsSuccess);
        Assert.Equal(AnalysisEngineErrorCodes.InvalidRequest, result.InvalidRequestError?.Code);
        Assert.Contains("no candles", result.InvalidRequestError?.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Null(registry.LastRequest);
    }

    [Fact]
    public async Task EngineUnavailableResultsFlowThroughIntakeResult()
    {
        var symbol = CreateIdentity("SPY", "ibkr", "756733");
        var registry = new CapturingAnalysisEngineRegistry(request => new AnalysisResult(
            AnalysisResultStatuses.Failed,
            new AnalysisEngineMetadata("lean", "LEAN", "QuantConnect", "1.0", AnalysisEngineStates.Unavailable),
            new AnalysisDataSource("LEAN", "unit-test", DateTimeOffset.UtcNow),
            request.Symbol,
            request.Timeframe,
            DateTimeOffset.UtcNow,
            Array.Empty<AnalysisSignal>(),
            Array.Empty<AnalysisMetric>(),
            Backtest: null,
            new AnalysisError(AnalysisEngineErrorCodes.EngineUnavailable, "LEAN runtime is unavailable.")));
        var intake = new AnalysisRequestIntake(new FakeMarketDataService(), registry);

        var result = await intake.RunAsync(new AnalysisRunRequest(
            symbol,
            SymbolCode: null,
            Timeframe: MarketDataTimeframes.OneDay,
            RequestedAtUtc: null,
            Bars: new[] { CreateBar(0) },
            EngineId: "lean",
            StrategyName: null));

        Assert.True(result.IsSuccess);
        Assert.Null(result.InvalidRequestError);
        Assert.Null(result.MarketDataError);
        Assert.Equal(AnalysisResultStatuses.Failed, result.Result?.Status);
        Assert.Equal(AnalysisEngineErrorCodes.EngineUnavailable, result.Result?.Error?.Code);
    }

    private static MarketDataSymbolIdentity CreateIdentity(string symbol, string provider, string providerSymbolId) =>
        MarketDataSymbolIdentity.Create(symbol, provider, providerSymbolId, MarketDataAssetClasses.Stock, "NASDAQ", "USD");

    private static OhlcvCandle CreateBar(int index) => new(
        new DateTimeOffset(2026, 5, 1, 0, 0, 0, TimeSpan.Zero).AddDays(index),
        Open: 100m + index,
        High: 102m + index,
        Low: 99m + index,
        Close: 101m + index,
        Volume: 1_000_000 + index);

    private sealed class CapturingAnalysisEngineRegistry(Func<AnalysisRequest, AnalysisResult>? analyze = null) : IAnalysisEngineRegistry
    {
        private readonly Func<AnalysisRequest, AnalysisResult> analyze = analyze ?? CreateCompletedResult;

        public AnalysisRequest? LastRequest { get; private set; }

        public IReadOnlyList<AnalysisEngineDescriptor> GetEngines() => Array.Empty<AnalysisEngineDescriptor>();

        public ValueTask<AnalysisResult> AnalyzeAsync(AnalysisRequest request, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            LastRequest = request;
            return ValueTask.FromResult(this.analyze(request));
        }

        private static AnalysisResult CreateCompletedResult(AnalysisRequest request) => new(
            AnalysisResultStatuses.Completed,
            new AnalysisEngineMetadata("unit", "Unit Test Engine", "unit", "1.0", AnalysisEngineStates.Available),
            new AnalysisDataSource("unit", "unit-test", DateTimeOffset.UtcNow),
            request.Symbol,
            request.Timeframe,
            DateTimeOffset.UtcNow,
            Array.Empty<AnalysisSignal>(),
            Array.Empty<AnalysisMetric>(),
            Backtest: null,
            Error: null);
    }

    private sealed class FakeMarketDataService : IMarketDataService
    {
        public List<(string Symbol, string? Timeframe, MarketDataSymbolIdentity? Identity)> CandleRequests { get; } = new();

        public List<string> SymbolRequests { get; } = new();

        public Func<string, string?, MarketDataSymbolIdentity?, CancellationToken, Task<MarketDataReadResult<CandleSeriesResponse>>> CandleHandler { get; init; } =
            (_, _, _, _) => throw new InvalidOperationException("Unexpected candle request.");

        public Func<string, CancellationToken, Task<MarketDataReadResult<MarketDataSymbol>>> SymbolHandler { get; init; } =
            (_, _) => Task.FromResult(MarketDataReadResult<MarketDataSymbol>.Failure(new MarketDataError(
                MarketDataProviderErrorCodes.UnsupportedSymbol,
                "Symbol metadata unavailable.")));

        public TrendingSymbolsResponse GetTrendingSymbols() => throw new NotSupportedException();

        public bool TrySearchSymbols(string? query, string? assetClass, int? limit, out MarketDataSymbolSearchResponse? response, out MarketDataError? error) =>
            throw new NotSupportedException();

        public bool TryGetSymbol(string symbol, out MarketDataSymbol? marketSymbol) => throw new NotSupportedException();

        public bool TryGetCandles(string symbol, string? timeframe, out CandleSeriesResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null) =>
            throw new NotSupportedException();

        public bool TryGetIndicators(string symbol, string? timeframe, out IndicatorResponse? response, out MarketDataError? error, MarketDataSymbolIdentity? identity = null) =>
            throw new NotSupportedException();

        public bool TryGetLatestUpdate(string symbol, string? timeframe, out MarketDataUpdate? update, out MarketDataError? error, MarketDataSymbolIdentity? identity = null) =>
            throw new NotSupportedException();

        public Task<MarketDataReadResult<CandleSeriesResponse>> GetCandlesAsync(
            string symbol,
            string? timeframe,
            MarketDataSymbolIdentity? identity = null,
            CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            CandleRequests.Add((symbol, timeframe, identity));
            return CandleHandler(symbol, timeframe, identity, cancellationToken);
        }

        public Task<MarketDataReadResult<MarketDataSymbol>> GetSymbolAsync(string symbol, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            SymbolRequests.Add(symbol);
            return SymbolHandler(symbol, cancellationToken);
        }
    }
}
