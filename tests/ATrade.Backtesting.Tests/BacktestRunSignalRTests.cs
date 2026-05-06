using System.Text.Json;
using ATrade.Backtesting;
using ATrade.MarketData;

namespace ATrade.Backtesting.Tests;

public sealed class BacktestRunSignalRTests
{
    [Fact]
    public void BacktestRunUpdatePayload_ContainsSafeStatusResultAndErrorShapeOnly()
    {
        var result = Json("""{"schemaVersion":"tp-060.backtest-result.v1","status":"completed","metrics":[]}""");
        var run = Run(BacktestRunStatuses.Completed, result, new BacktestError("analysis-engine-unavailable", "safe unavailable"));

        var payload = BacktestRunUpdatePayload.From(BacktestRunUpdateEvents.RunCompleted, run);
        var serialized = JsonSerializer.Serialize(payload, new JsonSerializerOptions(JsonSerializerDefaults.Web));

        Assert.Equal(BacktestRunUpdateEvents.RunCompleted, payload.Event);
        Assert.Equal(BacktestRunStatuses.Completed, payload.Status);
        Assert.Equal("AAPL", payload.Symbol.Symbol);
        Assert.Equal("sma-crossover", payload.StrategyId);
        Assert.Equal("lean", payload.EngineId);
        Assert.NotNull(payload.Result);
        Assert.Equal("analysis-engine-unavailable", payload.Error?.Code);
        Assert.DoesNotContain("capital", serialized, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("account", serialized, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("gateway", serialized, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("token", serialized, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("cookie", serialized, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("session", serialized, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("workspace", serialized, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("docker exec", serialized, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("https://", serialized, StringComparison.OrdinalIgnoreCase);
    }

    [Theory]
    [InlineData(BacktestRunStatuses.Running, BacktestRunUpdateEvents.StatusChanged)]
    [InlineData(BacktestRunStatuses.Completed, BacktestRunUpdateEvents.RunCompleted)]
    [InlineData(BacktestRunStatuses.Failed, BacktestRunUpdateEvents.RunFailed)]
    [InlineData(BacktestRunStatuses.Cancelled, BacktestRunUpdateEvents.RunCancelled)]
    public void BacktestRunUpdateEvents_MapTerminalStatusesToBrowserEventNames(string status, string expectedEvent)
    {
        Assert.Equal(expectedEvent, BacktestRunUpdateEvents.ForRunStatus(status));
    }

    private static BacktestRunEnvelope Run(string status, JsonElement? result, BacktestError? error) => new(
        Id: "bt_signalr",
        Status: status,
        SourceRunId: null,
        Request: new BacktestRequestSnapshot(
            MarketDataSymbolIdentity.Create("AAPL", "ibkr", "265598", MarketDataAssetClasses.Stock, "NASDAQ", "USD"),
            BacktestStrategyIds.SmaCrossover,
            new Dictionary<string, JsonElement>(StringComparer.Ordinal),
            ChartRangePresets.OneYear,
            new BacktestCostModelSnapshot(0m, 0m, "USD"),
            0m,
            BacktestBenchmarkModes.None,
            EngineId: "lean"),
        Capital: new BacktestCapitalSnapshot(100000m, "USD", "local-paper-ledger"),
        CreatedAtUtc: DateTimeOffset.UnixEpoch,
        UpdatedAtUtc: DateTimeOffset.UnixEpoch.AddMinutes(1),
        StartedAtUtc: DateTimeOffset.UnixEpoch.AddSeconds(30),
        CompletedAtUtc: DateTimeOffset.UnixEpoch.AddMinutes(1),
        Error: error,
        Result: result);

    private static JsonElement Json(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.Clone();
    }
}
