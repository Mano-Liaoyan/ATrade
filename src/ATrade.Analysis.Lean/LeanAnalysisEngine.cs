using ATrade.Analysis;
using Microsoft.Extensions.Logging;

namespace ATrade.Analysis.Lean;

public sealed class LeanAnalysisEngine(
    LeanAnalysisOptions options,
    ILeanRuntimeExecutor runtimeExecutor,
    ILeanAnalysisWorkspaceFactory workspaceFactory,
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

    public async ValueTask<AnalysisResult> AnalyzeAsync(AnalysisRequest request, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        cancellationToken.ThrowIfCancellationRequested();

        LeanPreparedWorkspace? workspace = null;
        var source = CreateSource();

        try
        {
            workspace = await workspaceFactory.CreateAsync(request, cancellationToken);
            var execution = await runtimeExecutor.ExecuteAsync(
                new LeanRuntimeExecutionRequest(
                    workspace.WorkspacePath,
                    workspace.ProjectName,
                    workspace.OutputDirectory,
                    options.Timeout),
                cancellationToken);

            if (execution.TimedOut)
            {
                return CreateErrorResult(
                    request,
                    source,
                    AnalysisResultStatuses.Failed,
                    AnalysisEngineErrorCodes.EngineUnavailable,
                    $"LEAN analysis timed out after {options.Timeout.TotalSeconds:N0} seconds.");
            }

            if (execution.ExitCode != 0)
            {
                logger.LogWarning("LEAN runtime exited with code {ExitCode}: {StandardError}", execution.ExitCode, Truncate(execution.StandardError));
                return CreateErrorResult(
                    request,
                    source,
                    AnalysisResultStatuses.Failed,
                    AnalysisEngineErrorCodes.EngineUnavailable,
                    $"LEAN runtime exited with code {execution.ExitCode}. {Truncate(execution.StandardError)}".Trim());
            }

            return LeanAnalysisResultParser.Parse(execution, request, workspace.Input, Metadata, source);
        }
        catch (LeanInputConversionException exception)
        {
            return CreateErrorResult(
                request,
                source,
                AnalysisResultStatuses.Failed,
                AnalysisEngineErrorCodes.InvalidRequest,
                exception.Message);
        }
        catch (LeanRuntimeUnavailableException exception)
        {
            logger.LogWarning(exception, "LEAN runtime is not available.");
            return CreateErrorResult(
                request,
                source,
                AnalysisResultStatuses.Failed,
                AnalysisEngineErrorCodes.EngineUnavailable,
                exception.Message);
        }
        catch (LeanAnalysisResultParseException exception)
        {
            logger.LogWarning(exception, "LEAN runtime output could not be parsed.");
            return CreateErrorResult(
                request,
                source,
                AnalysisResultStatuses.Failed,
                AnalysisEngineErrorCodes.EngineUnavailable,
                exception.Message);
        }
        finally
        {
            if (workspace is not null)
            {
                workspaceFactory.Cleanup(workspace);
            }
        }
    }

    private AnalysisDataSource CreateSource() => new(
        LeanAnalysisOptions.DefaultProvider,
        $"{options.RuntimeDescription}; project={LeanAnalysisWorkspaceFactory.ProjectName}",
        DateTimeOffset.UtcNow);

    private AnalysisResult CreateErrorResult(
        AnalysisRequest request,
        AnalysisDataSource source,
        string status,
        string errorCode,
        string message) => new(
            status,
            Metadata with { State = AnalysisEngineStates.Unavailable, Message = message },
            source,
            request.Symbol,
            request.Timeframe,
            DateTimeOffset.UtcNow,
            Array.Empty<AnalysisSignal>(),
            Array.Empty<AnalysisMetric>(),
            Backtest: null,
            new AnalysisError(errorCode, message));

    private static string Truncate(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return string.Empty;
        }

        var normalized = value.ReplaceLineEndings(" ").Trim();
        return normalized.Length <= 500
            ? normalized
            : normalized[..500];
    }
}
