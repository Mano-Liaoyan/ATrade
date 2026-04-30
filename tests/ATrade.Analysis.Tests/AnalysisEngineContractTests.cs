using ATrade.Analysis;
using ATrade.MarketData;
using Microsoft.Extensions.DependencyInjection;

namespace ATrade.Analysis.Tests;

public sealed class AnalysisEngineContractTests
{
    [Fact]
    public void AnalysisRequestUsesNormalizedMarketDataInputs()
    {
        var symbol = new MarketDataSymbolIdentity("AAPL", "ibkr", "265598", "STK", "NASDAQ", "USD");
        var bar = new OhlcvCandle(
            new DateTimeOffset(2026, 4, 29, 14, 30, 0, TimeSpan.Zero),
            Open: 190.10m,
            High: 191.25m,
            Low: 189.75m,
            Close: 190.95m,
            Volume: 1_250_000);

        var request = new AnalysisRequest(
            symbol,
            MarketDataTimeframes.OneDay,
            DateTimeOffset.UtcNow,
            new[] { bar },
            StrategyName: "contract-test-strategy");

        Assert.Equal(symbol, request.Symbol);
        Assert.Equal(MarketDataTimeframes.OneDay, request.Timeframe);
        Assert.Equal(bar, Assert.Single(request.Bars));
    }

    [Fact]
    public async Task NoConfiguredEngineReturnsExplicitNotConfiguredResult()
    {
        var engine = new NoConfiguredAnalysisEngine();
        var request = CreateRequest();

        var result = await engine.AnalyzeAsync(request);

        Assert.Equal(AnalysisResultStatuses.NotConfigured, result.Status);
        Assert.Equal(AnalysisEngineStates.NotConfigured, result.Engine.State);
        Assert.Equal(NoConfiguredAnalysisEngine.EngineId, result.Engine.EngineId);
        Assert.Equal("none", result.Engine.Provider);
        Assert.Equal("analysis-engine-not-configured", result.Source.Source);
        Assert.Equal(request.Symbol, result.Symbol);
        Assert.Equal(request.Timeframe, result.Timeframe);
        Assert.Empty(result.Signals);
        Assert.Empty(result.Metrics);
        Assert.Null(result.Backtest);
        Assert.NotNull(result.Error);
        Assert.Equal(AnalysisEngineErrorCodes.EngineNotConfigured, result.Error.Code);
    }

    [Fact]
    public void RegistryDescribesNotConfiguredEngineWhenNoProviderIsRegistered()
    {
        var fallback = new NoConfiguredAnalysisEngine();
        var registry = new AnalysisEngineRegistry(Array.Empty<IAnalysisEngine>(), fallback);

        var descriptor = Assert.Single(registry.GetEngines());

        Assert.Equal(NoConfiguredAnalysisEngine.EngineId, descriptor.Metadata.EngineId);
        Assert.Equal(AnalysisEngineStates.NotConfigured, descriptor.Metadata.State);
        Assert.False(descriptor.Capabilities.SupportsSignals);
        Assert.False(descriptor.Capabilities.SupportsBacktests);
    }

    [Fact]
    public async Task AnalysisModuleRegistersRegistryWithNoEngineFallback()
    {
        var services = new ServiceCollection()
            .AddAnalysisModule()
            .BuildServiceProvider();

        var registry = services.GetRequiredService<IAnalysisEngineRegistry>();
        var result = await registry.AnalyzeAsync(CreateRequest());

        Assert.Equal(AnalysisResultStatuses.NotConfigured, result.Status);
        Assert.Equal(AnalysisEngineErrorCodes.EngineNotConfigured, result.Error?.Code);
    }

    private static AnalysisRequest CreateRequest() => new(
        new MarketDataSymbolIdentity("MSFT", "ibkr", "272093", "STK", "NASDAQ", "USD"),
        MarketDataTimeframes.OneDay,
        DateTimeOffset.UtcNow,
        new[]
        {
            new OhlcvCandle(
                new DateTimeOffset(2026, 4, 29, 14, 30, 0, TimeSpan.Zero),
                Open: 410m,
                High: 415m,
                Low: 408m,
                Close: 413m,
                Volume: 950_000),
        });
}
