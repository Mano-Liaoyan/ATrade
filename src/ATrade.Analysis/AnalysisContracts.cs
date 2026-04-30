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

public sealed record AnalysisRequest(
    MarketDataSymbolIdentity Symbol,
    string Timeframe,
    DateTimeOffset RequestedAtUtc,
    IReadOnlyList<OhlcvCandle> Bars,
    string? EngineId = null,
    string? StrategyName = null);

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
    AnalysisError? Error);

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
    decimal WinRatePercent);

public sealed record AnalysisError(string Code, string Message);
