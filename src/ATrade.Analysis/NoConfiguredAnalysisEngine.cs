namespace ATrade.Analysis;

public sealed class NoConfiguredAnalysisEngine : IAnalysisEngine
{
    public const string EngineId = "not-configured";

    private const string Message = "No analysis engine is configured. Configure an analysis provider before requesting production analysis.";

    public AnalysisEngineMetadata Metadata { get; } = new(
        EngineId,
        "No analysis engine configured",
        "none",
        "0.0.0",
        AnalysisEngineStates.NotConfigured,
        Message);

    public AnalysisEngineCapabilities Capabilities { get; } = new(
        SupportsSignals: false,
        SupportsBacktests: false,
        SupportsMetrics: false,
        SupportsOptimization: false,
        RequiresExternalRuntime: false);

    public ValueTask<AnalysisResult> AnalyzeAsync(AnalysisRequest request, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        cancellationToken.ThrowIfCancellationRequested();

        var result = new AnalysisResult(
            AnalysisResultStatuses.NotConfigured,
            Metadata,
            new AnalysisDataSource("none", "analysis-engine-not-configured", DateTimeOffset.UtcNow),
            request.Symbol,
            request.Timeframe,
            DateTimeOffset.UtcNow,
            Array.Empty<AnalysisSignal>(),
            Array.Empty<AnalysisMetric>(),
            Backtest: null,
            new AnalysisError(AnalysisEngineErrorCodes.EngineNotConfigured, Message));

        return ValueTask.FromResult(result);
    }
}
