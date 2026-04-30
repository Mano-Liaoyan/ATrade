namespace ATrade.Analysis.Lean;

public sealed record LeanRuntimeExecutionRequest(
    string WorkspacePath,
    string ProjectName,
    string OutputDirectory,
    TimeSpan Timeout);

public sealed record LeanRuntimeExecutionResult(
    int ExitCode,
    string StandardOutput,
    string StandardError,
    bool TimedOut);

public interface ILeanRuntimeExecutor
{
    Task<LeanRuntimeExecutionResult> ExecuteAsync(LeanRuntimeExecutionRequest request, CancellationToken cancellationToken = default);
}

public sealed class LeanRuntimeUnavailableException(string message, Exception? innerException = null) : Exception(message, innerException);
