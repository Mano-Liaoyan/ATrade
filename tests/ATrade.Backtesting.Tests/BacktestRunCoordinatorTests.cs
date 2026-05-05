using System.Text.Json;
using ATrade.Backtesting;
using ATrade.MarketData;
using Microsoft.Extensions.Logging;

namespace ATrade.Backtesting.Tests;

public sealed class BacktestRunCoordinatorTests
{
    private static readonly BacktestWorkspaceScope Scope = new("local-user", "paper-workspace");
    private static readonly DateTimeOffset ObservedAtUtc = new(2026, 5, 6, 13, 0, 0, TimeSpan.Zero);

    [Fact]
    public async Task ProcessNextQueuedRunAsync_ClaimsQueuedRunMarksRunningAndPersistsCompletedResult()
    {
        var repository = new InMemoryBacktestRunRepository([Run("bt_completed", BacktestRunStatuses.Queued)]);
        var result = Json("""{"summary":{"totalTrades":0},"equity":[]}""");
        var pipeline = new ScriptedBacktestRunPipeline(BacktestRunExecutionResult.Completed(result));
        var coordinator = CreateCoordinator(repository, pipeline);

        var processed = await coordinator.ProcessNextQueuedRunAsync();

        Assert.True(processed);
        Assert.Equal(1, repository.ClaimAttempts);
        Assert.Equal([BacktestRunStatuses.Running], pipeline.ObservedStatuses);
        var savedRun = Assert.Single(repository.Runs).Run;
        Assert.Equal(BacktestRunStatuses.Completed, savedRun.Status);
        Assert.Equal(ObservedAtUtc, savedRun.StartedAtUtc);
        Assert.Equal(ObservedAtUtc, savedRun.CompletedAtUtc);
        Assert.Null(savedRun.Error);
        Assert.NotNull(savedRun.Result);
        Assert.Contains("totalTrades", savedRun.Result!.Value.GetRawText(), StringComparison.Ordinal);
        var statusUpdate = Assert.Single(repository.StatusUpdates);
        Assert.Equal(BacktestRunStatuses.Completed, statusUpdate.Status);
    }

    [Fact]
    public async Task ProcessNextQueuedRunAsync_PersistsSafeFailureWhenPipelineThrows()
    {
        var repository = new InMemoryBacktestRunRepository([Run("bt_failed", BacktestRunStatuses.Queued)]);
        var pipeline = new ScriptedBacktestRunPipeline(new InvalidOperationException("boom"));
        var coordinator = CreateCoordinator(repository, pipeline);

        var processed = await coordinator.ProcessNextQueuedRunAsync();

        Assert.True(processed);
        var savedRun = Assert.Single(repository.Runs).Run;
        Assert.Equal(BacktestRunStatuses.Failed, savedRun.Status);
        Assert.Equal(BacktestErrorCodes.RunnerFailed, savedRun.Error?.Code);
        Assert.Equal(BacktestSafeMessages.RunnerFailed, savedRun.Error?.Message);
        Assert.Equal(ObservedAtUtc, savedRun.StartedAtUtc);
        Assert.Equal(ObservedAtUtc, savedRun.CompletedAtUtc);
    }

    [Fact]
    public async Task RecoverInterruptedRunsAsync_FailsRunningRunsAndLeavesQueuedRunsRunnable()
    {
        var repository = new InMemoryBacktestRunRepository(
        [
            Run("bt_running", BacktestRunStatuses.Running),
            Run("bt_queued", BacktestRunStatuses.Queued),
        ]);
        var coordinator = CreateCoordinator(repository, new ScriptedBacktestRunPipeline(BacktestRunExecutionResult.Completed()));

        var recovered = await coordinator.RecoverInterruptedRunsAsync();

        Assert.Equal(1, recovered);
        var interrupted = repository.Runs.Single(run => run.Run.Id == "bt_running").Run;
        var queued = repository.Runs.Single(run => run.Run.Id == "bt_queued").Run;
        Assert.Equal(BacktestRunStatuses.Failed, interrupted.Status);
        Assert.Equal(BacktestErrorCodes.RunInterrupted, interrupted.Error?.Code);
        Assert.Equal(BacktestSafeMessages.RunInterrupted, interrupted.Error?.Message);
        Assert.Equal(ObservedAtUtc, interrupted.CompletedAtUtc);
        Assert.Equal(BacktestRunStatuses.Queued, queued.Status);
        Assert.Null(queued.CompletedAtUtc);
    }

    [Fact]
    public async Task ProcessNextQueuedRunAsync_ConcurrentCallsOnlyExecuteSingleClaimedRun()
    {
        var repository = new InMemoryBacktestRunRepository([Run("bt_once", BacktestRunStatuses.Queued)]);
        var pipeline = new ScriptedBacktestRunPipeline(BacktestRunExecutionResult.Completed());
        var coordinator = CreateCoordinator(repository, pipeline);

        var results = await Task.WhenAll(
            coordinator.ProcessNextQueuedRunAsync(),
            coordinator.ProcessNextQueuedRunAsync());

        Assert.Single(results, result => result);
        Assert.Equal(2, repository.ClaimAttempts);
        Assert.Equal(1, pipeline.ExecuteCount);
        Assert.Equal(BacktestRunStatuses.Completed, Assert.Single(repository.Runs).Run.Status);
    }

    [Fact]
    public void PostgresSql_ClaimsQueuedRowsWithSkipLockedAndFailsInterruptedRunningRows()
    {
        Assert.Contains("WHERE status = 'queued'", PostgresBacktestRunSql.ClaimNextQueuedRun, StringComparison.Ordinal);
        Assert.Contains("ORDER BY created_at_utc ASC, run_id ASC", PostgresBacktestRunSql.ClaimNextQueuedRun, StringComparison.Ordinal);
        Assert.Contains("FOR UPDATE SKIP LOCKED", PostgresBacktestRunSql.ClaimNextQueuedRun, StringComparison.Ordinal);
        Assert.Contains("AND run.status = 'queued'", PostgresBacktestRunSql.ClaimNextQueuedRun, StringComparison.Ordinal);
        Assert.Contains("SET status = 'running'", PostgresBacktestRunSql.ClaimNextQueuedRun, StringComparison.Ordinal);
        Assert.Contains("started_at_utc = COALESCE(started_at_utc, @observed_at_utc)", PostgresBacktestRunSql.ClaimNextQueuedRun, StringComparison.Ordinal);

        Assert.Contains("WHERE status = 'running'", PostgresBacktestRunSql.FailInterruptedRunningRuns, StringComparison.Ordinal);
        Assert.Contains("SET status = 'failed'", PostgresBacktestRunSql.FailInterruptedRunningRuns, StringComparison.Ordinal);
        Assert.DoesNotContain("status = 'queued'", PostgresBacktestRunSql.FailInterruptedRunningRuns, StringComparison.Ordinal);
    }

    private static BacktestRunCoordinator CreateCoordinator(
        InMemoryBacktestRunRepository repository,
        IBacktestRunExecutionPipeline pipeline) =>
        new(new NoopSchemaInitializer(), repository, pipeline, new NoopLogger<BacktestRunCoordinator>());

    private static BacktestRunRecord Run(string id, string status)
    {
        var createdAtUtc = ObservedAtUtc.AddMinutes(-10);
        var startedAtUtc = string.Equals(status, BacktestRunStatuses.Running, StringComparison.Ordinal)
            ? createdAtUtc.AddMinutes(1)
            : (DateTimeOffset?)null;
        var completedAtUtc = BacktestRunStatuses.IsTerminal(status)
            ? createdAtUtc.AddMinutes(2)
            : (DateTimeOffset?)null;

        return new BacktestRunRecord(
            Scope,
            new BacktestRunEnvelope(
                Id: id,
                Status: status,
                SourceRunId: null,
                Request: SafeSnapshot(),
                Capital: new BacktestCapitalSnapshot(100000m, "USD", "local-paper-ledger"),
                CreatedAtUtc: createdAtUtc,
                UpdatedAtUtc: createdAtUtc,
                StartedAtUtc: startedAtUtc,
                CompletedAtUtc: completedAtUtc,
                Error: null,
                Result: null));
    }

    private static BacktestRequestSnapshot SafeSnapshot() => new(
        Symbol: MarketDataSymbolIdentity.Create("AAPL", "ibkr", "265598", MarketDataAssetClasses.Stock, "NASDAQ", "USD"),
        StrategyId: BacktestStrategyIds.SmaCrossover,
        Parameters: new Dictionary<string, JsonElement>(StringComparer.Ordinal),
        ChartRange: ChartRangePresets.OneYear,
        CostModel: new BacktestCostModelSnapshot(0m, 0m, "USD"),
        SlippageBps: 0m,
        BenchmarkMode: BacktestBenchmarkModes.None);

    private static JsonElement Json(string json)
    {
        using var document = JsonDocument.Parse(json);
        return document.RootElement.Clone();
    }

    private sealed class NoopSchemaInitializer : IBacktestRunSchemaInitializer
    {
        public Task InitializeAsync(CancellationToken cancellationToken = default) => Task.CompletedTask;
    }

    private sealed class ScriptedBacktestRunPipeline : IBacktestRunExecutionPipeline
    {
        private readonly object response;

        public ScriptedBacktestRunPipeline(object response) => this.response = response;

        public int ExecuteCount { get; private set; }

        public List<string> ObservedStatuses { get; } = [];

        public Task<BacktestRunExecutionResult> ExecuteAsync(BacktestRunRecord run, CancellationToken cancellationToken = default)
        {
            ExecuteCount++;
            ObservedStatuses.Add(run.Run.Status);

            if (response is Exception exception)
            {
                throw exception;
            }

            return Task.FromResult((BacktestRunExecutionResult)response);
        }
    }

    private sealed record StatusUpdate(string RunId, string Status, BacktestError? Error, JsonElement? Result);

    private sealed class InMemoryBacktestRunRepository(IReadOnlyList<BacktestRunRecord> initialRuns) : IBacktestRunRepository
    {
        private readonly object gate = new();
        private readonly List<BacktestRunRecord> runs = [.. initialRuns];

        public int ClaimAttempts { get; private set; }

        public List<StatusUpdate> StatusUpdates { get; } = [];

        public IReadOnlyList<BacktestRunRecord> Runs
        {
            get
            {
                lock (gate)
                {
                    return [.. runs];
                }
            }
        }

        public Task<BacktestRunRecord> CreateAsync(BacktestRunRecord queuedRun, CancellationToken cancellationToken = default) =>
            throw new NotSupportedException();

        public Task<IReadOnlyList<BacktestRunEnvelope>> ListAsync(
            BacktestWorkspaceScope scope,
            int limit = BacktestRunRepositoryDefaults.DefaultListLimit,
            CancellationToken cancellationToken = default) =>
            throw new NotSupportedException();

        public Task<BacktestRunRecord?> GetAsync(
            BacktestWorkspaceScope scope,
            string runId,
            CancellationToken cancellationToken = default) =>
            Task.FromResult(Runs.FirstOrDefault(run => run.Scope == scope && run.Run.Id == runId));

        public Task<int> FailInterruptedRunningAsync(BacktestError error, CancellationToken cancellationToken = default)
        {
            lock (gate)
            {
                var recovered = 0;
                for (var index = 0; index < runs.Count; index++)
                {
                    var run = runs[index];
                    if (!string.Equals(run.Run.Status, BacktestRunStatuses.Running, StringComparison.Ordinal))
                    {
                        continue;
                    }

                    recovered++;
                    runs[index] = run with
                    {
                        Run = run.Run with
                        {
                            Status = BacktestRunStatuses.Failed,
                            Error = error,
                            UpdatedAtUtc = ObservedAtUtc,
                            CompletedAtUtc = ObservedAtUtc,
                        },
                    };
                }

                return Task.FromResult(recovered);
            }
        }

        public Task<BacktestRunRecord?> ClaimNextQueuedAsync(CancellationToken cancellationToken = default)
        {
            lock (gate)
            {
                ClaimAttempts++;
                var index = runs.FindIndex(run => string.Equals(run.Run.Status, BacktestRunStatuses.Queued, StringComparison.Ordinal));
                if (index < 0)
                {
                    return Task.FromResult<BacktestRunRecord?>(null);
                }

                var queued = runs[index];
                var running = queued with
                {
                    Run = queued.Run with
                    {
                        Status = BacktestRunStatuses.Running,
                        Error = null,
                        Result = null,
                        UpdatedAtUtc = ObservedAtUtc,
                        StartedAtUtc = queued.Run.StartedAtUtc ?? ObservedAtUtc,
                        CompletedAtUtc = null,
                    },
                };
                runs[index] = running;
                return Task.FromResult<BacktestRunRecord?>(running);
            }
        }

        public Task<BacktestRunRecord?> UpdateStatusAsync(
            BacktestWorkspaceScope scope,
            string runId,
            string status,
            BacktestError? error = null,
            JsonElement? result = null,
            CancellationToken cancellationToken = default)
        {
            lock (gate)
            {
                StatusUpdates.Add(new StatusUpdate(runId, status, error, result));
                var index = runs.FindIndex(run => run.Scope == scope && run.Run.Id == runId);
                if (index < 0)
                {
                    return Task.FromResult<BacktestRunRecord?>(null);
                }

                var current = runs[index];
                var updated = current with
                {
                    Run = current.Run with
                    {
                        Status = status,
                        Error = error,
                        Result = result,
                        UpdatedAtUtc = ObservedAtUtc,
                        CompletedAtUtc = BacktestRunStatuses.IsTerminal(status) ? ObservedAtUtc : null,
                    },
                };
                runs[index] = updated;
                return Task.FromResult<BacktestRunRecord?>(updated);
            }
        }

        public Task<BacktestRunRecord?> CancelAsync(
            BacktestWorkspaceScope scope,
            string runId,
            CancellationToken cancellationToken = default) =>
            throw new NotSupportedException();

        public Task<BacktestRunRecord?> CreateRetryAsync(
            BacktestWorkspaceScope scope,
            string sourceRunId,
            BacktestRunRecord retryRun,
            CancellationToken cancellationToken = default) =>
            throw new NotSupportedException();
    }

    private sealed class NoopLogger<T> : ILogger<T>
    {
        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull =>
            null;

        public bool IsEnabled(LogLevel logLevel) => false;

        public void Log<TState>(
            LogLevel logLevel,
            EventId eventId,
            TState state,
            Exception? exception,
            Func<TState, Exception?, string> formatter)
        {
        }
    }
}
