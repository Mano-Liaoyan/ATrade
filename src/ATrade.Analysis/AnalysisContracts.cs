using System.Text.Json;
using ATrade.MarketData;

namespace ATrade.Analysis;

public static class AnalysisEngineStates
{
    public const string Available = "available";
    public const string NotConfigured = "not-configured";
    public const string Unavailable = "unavailable";
}

public static class AnalysisEngineErrorCodes
{
    public const string EngineNotConfigured = "analysis-engine-not-configured";
    public const string EngineUnavailable = "analysis-engine-unavailable";
    public const string InvalidRequest = "analysis-request-invalid";
}

public static class AnalysisResultStatuses
{
    public const string Completed = "completed";
    public const string NotConfigured = "not-configured";
    public const string Failed = "failed";
}

public sealed record AnalysisEngineCapabilities(
    bool SupportsSignals,
    bool SupportsBacktests,
    bool SupportsMetrics,
    bool SupportsOptimization,
    bool RequiresExternalRuntime);

public sealed record AnalysisEngineMetadata(
    string EngineId,
    string DisplayName,
    string Provider,
    string Version,
    string State,
    string? Message = null);

public sealed record AnalysisEngineDescriptor(
    AnalysisEngineMetadata Metadata,
    AnalysisEngineCapabilities Capabilities);

public sealed record AnalysisBacktestSettings(
    decimal InitialCapital,
    decimal CommissionPerTrade,
    decimal CommissionBps,
    decimal SlippageBps,
    string Currency);

public sealed record AnalysisRequest(
    MarketDataSymbolIdentity Symbol,
    string Timeframe,
    DateTimeOffset RequestedAtUtc,
    IReadOnlyList<OhlcvCandle> Bars,
    string? EngineId = null,
    string? StrategyName = null,
    IReadOnlyDictionary<string, JsonElement>? StrategyParameters = null,
    AnalysisBacktestSettings? BacktestSettings = null);

public sealed record AnalysisDataSource(
    string Provider,
    string Source,
    DateTimeOffset GeneratedAtUtc);

public sealed record AnalysisResult(
    string Status,
    AnalysisEngineMetadata Engine,
    AnalysisDataSource Source,
    MarketDataSymbolIdentity Symbol,
    string Timeframe,
    DateTimeOffset GeneratedAtUtc,
    IReadOnlyList<AnalysisSignal> Signals,
    IReadOnlyList<AnalysisMetric> Metrics,
    BacktestSummary? Backtest,
    AnalysisError? Error,
    AnalysisBacktestDetails? BacktestDetails = null);

public sealed record AnalysisSignal(
    DateTimeOffset Time,
    string Kind,
    string Direction,
    decimal Confidence,
    string Rationale);

public sealed record AnalysisMetric(
    string Name,
    decimal Value,
    string? Unit = null);

public sealed record BacktestSummary(
    DateTimeOffset StartUtc,
    DateTimeOffset EndUtc,
    decimal InitialCapital,
    decimal FinalEquity,
    decimal TotalReturnPercent,
    int TradeCount,
    decimal WinRatePercent,
    decimal MaxDrawdownPercent = 0m,
    decimal TotalCost = 0m);

public sealed record AnalysisBacktestDetails(
    IReadOnlyList<AnalysisEquityCurvePoint> EquityCurve,
    IReadOnlyList<AnalysisSimulatedTrade> Trades,
    AnalysisBenchmark? Benchmark,
    AnalysisBacktestAccounting Accounting);

public sealed record AnalysisEquityCurvePoint(
    DateTimeOffset Time,
    decimal Equity,
    decimal DrawdownPercent);

public sealed record AnalysisSimulatedTrade(
    DateTimeOffset EntryTime,
    DateTimeOffset? ExitTime,
    string Direction,
    decimal EntryPrice,
    decimal? ExitPrice,
    decimal Quantity,
    decimal GrossPnl,
    decimal NetPnl,
    decimal ReturnPercent,
    decimal TotalCost,
    string ExitReason);

public sealed record AnalysisBenchmark(
    string Mode,
    string Label,
    decimal InitialCapital,
    decimal FinalEquity,
    decimal TotalReturnPercent,
    IReadOnlyList<AnalysisEquityCurvePoint> EquityCurve);

public sealed record AnalysisBacktestAccounting(
    decimal CommissionPerTrade,
    decimal CommissionBps,
    decimal SlippageBps,
    string Currency);

public sealed record AnalysisError(string Code, string Message);
