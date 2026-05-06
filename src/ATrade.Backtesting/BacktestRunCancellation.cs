using System.Collections.Concurrent;

namespace ATrade.Backtesting;

public interface IBacktestRunCancellationRegistry
{
    BacktestRunCancellationLease RegisterRunningRun(string runId, CancellationToken runnerCancellationToken);

    bool RequestCancellation(string runId);
}

public sealed class BacktestRunCancellationRegistry : IBacktestRunCancellationRegistry
{
    private readonly ConcurrentDictionary<string, CancellationTokenSource> runningRuns = new(StringComparer.Ordinal);

    public BacktestRunCancellationLease RegisterRunningRun(string runId, CancellationToken runnerCancellationToken)
    {
        var normalizedRunId = BacktestRunId.Create(runId).Value;
        var runCancellation = new CancellationTokenSource();
        if (!runningRuns.TryAdd(normalizedRunId, runCancellation))
        {
            runCancellation.Dispose();
            throw new InvalidOperationException("Backtest run is already registered as running.");
        }

        var linkedCancellation = CancellationTokenSource.CreateLinkedTokenSource(runnerCancellationToken, runCancellation.Token);
        return new BacktestRunCancellationLease(
            normalizedRunId,
            linkedCancellation,
            () =>
            {
                runningRuns.TryRemove(normalizedRunId, out _);
                linkedCancellation.Dispose();
                runCancellation.Dispose();
            });
    }

    public bool RequestCancellation(string runId)
    {
        var normalizedRunId = BacktestRunId.Create(runId).Value;
        if (!runningRuns.TryGetValue(normalizedRunId, out var cancellationTokenSource))
        {
            return false;
        }

        cancellationTokenSource.Cancel();
        return true;
    }
}

public sealed class BacktestRunCancellationLease(
    string runId,
    CancellationTokenSource linkedCancellation,
    Action dispose) : IDisposable
{
    private bool disposed;

    public string RunId { get; } = runId;

    public CancellationToken Token => linkedCancellation.Token;

    public bool IsCancellationRequested => linkedCancellation.IsCancellationRequested;

    public void Dispose()
    {
        if (disposed)
        {
            return;
        }

        disposed = true;
        dispose();
    }
}
