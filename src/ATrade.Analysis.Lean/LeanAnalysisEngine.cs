using ATrade.Analysis;
using Microsoft.Extensions.Logging;

namespace ATrade.Analysis.Lean;

public sealed class LeanAnalysisEngine(
    LeanAnalysisOptions options,
    ILeanRuntimeExecutor runtimeExecutor,
    ILogger<LeanAnalysisEngine> logger) : IAnalysisEngine
{
    private static readonly AnalysisEngineCapabilities LeanCapabilities = new(
        SupportsSignals: true,
        SupportsBacktests: true,
        SupportsMetrics: true,
        SupportsOptimization: false,
        RequiresExternalRuntime: true);

    public AnalysisEngineMetadata Metadata { get; } = new(
        LeanAnalysisOptions.EngineId,
        LeanAnalysisOptions.DefaultDisplayName,
        LeanAnalysisOptions.DefaultProvider,
        LeanAnalysisOptions.DefaultVersion,
        AnalysisEngineStates.Available,
        "Configured to invoke the official LEAN runtime for analysis-only backtests.");

    public AnalysisEngineCapabilities Capabilities => LeanCapabilities;

    public ValueTask<AnalysisResult> AnalyzeAsync(AnalysisRequest request, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        cancellationToken.ThrowIfCancellationRequested();
        _ = runtimeExecutor;
        logger.LogInformation("LEAN analysis engine is configured with {RuntimeDescription}.", options.RuntimeDescription);

        var result = new AnalysisResult(
            AnalysisResultStatuses.Failed,
            Metadata,
            new AnalysisDataSource(LeanAnalysisOptions.DefaultProvider, options.RuntimeDescription, DateTimeOffset.UtcNow),
            request.Symbol,
            request.Timeframe,
            DateTimeOffset.UtcNow,
            Array.Empty<AnalysisSignal>(),
            Array.Empty<AnalysisMetric>(),
            Backtest: null,
            new AnalysisError(AnalysisEngineErrorCodes.EngineUnavailable, "LEAN runtime integration is configured; analysis execution will generate a LEAN workspace in the execution step."));

        return ValueTask.FromResult(result);
    }
}
