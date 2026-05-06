using System.Text.Json;
using Npgsql;
using NpgsqlTypes;

namespace ATrade.Backtesting;

public interface IBacktestRunSchemaInitializer
{
    Task InitializeAsync(CancellationToken cancellationToken = default);
}

public interface IBacktestRunRepository
{
    Task<BacktestRunRecord> CreateAsync(BacktestRunRecord queuedRun, CancellationToken cancellationToken = default);

    Task<IReadOnlyList<BacktestRunEnvelope>> ListAsync(
        BacktestWorkspaceScope scope,
        int limit = BacktestRunRepositoryDefaults.DefaultListLimit,
        CancellationToken cancellationToken = default);

    Task<BacktestRunRecord?> GetAsync(BacktestWorkspaceScope scope, string runId, CancellationToken cancellationToken = default);

    Task<int> FailInterruptedRunningAsync(BacktestError error, CancellationToken cancellationToken = default);

    Task<BacktestRunRecord?> ClaimNextQueuedAsync(CancellationToken cancellationToken = default);

    Task<BacktestRunRecord?> UpdateStatusAsync(
        BacktestWorkspaceScope scope,
        string runId,
        string status,
        BacktestError? error = null,
        JsonElement? result = null,
        CancellationToken cancellationToken = default);

    Task<BacktestRunRecord?> CancelAsync(BacktestWorkspaceScope scope, string runId, CancellationToken cancellationToken = default);

    Task<BacktestRunRecord?> CreateRetryAsync(
        BacktestWorkspaceScope scope,
        string sourceRunId,
        BacktestRunRecord retryRun,
        CancellationToken cancellationToken = default);
}

public static class BacktestRunRepositoryDefaults
{
    public const int DefaultListLimit = 50;
    public const int MaximumListLimit = 200;
}

public sealed class BacktestStorageUnavailableException : InvalidOperationException
{
    public BacktestStorageUnavailableException(string message, Exception? innerException = null)
        : base(message, innerException)
    {
    }

    public string Code => BacktestErrorCodes.StorageUnavailable;
}

public sealed class PostgresBacktestRunRepository(
    IBacktestingPostgresDataSourceProvider dataSourceProvider,
    TimeProvider timeProvider) : IBacktestRunRepository
{
    public PostgresBacktestRunRepository(IBacktestingPostgresDataSourceProvider dataSourceProvider)
        : this(dataSourceProvider, TimeProvider.System)
    {
    }

    public async Task<BacktestRunRecord> CreateAsync(
        BacktestRunRecord queuedRun,
        CancellationToken cancellationToken = default)
    {
        ValidateQueuedRun(queuedRun, requireNoSourceRun: false);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresBacktestRunSql.InsertRun);
            AddRunParameters(command, queuedRun);

            await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            if (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                return ReadRecord(reader);
            }
        }
        catch (NpgsqlException exception)
        {
            throw new BacktestStorageUnavailableException("Postgres saved backtest run create failed.", exception);
        }

        throw new BacktestStorageUnavailableException("Postgres saved backtest run create returned no row.");
    }

    public async Task<IReadOnlyList<BacktestRunEnvelope>> ListAsync(
        BacktestWorkspaceScope scope,
        int limit = BacktestRunRepositoryDefaults.DefaultListLimit,
        CancellationToken cancellationToken = default)
    {
        ValidateScope(scope);
        var normalizedLimit = Math.Clamp(
            limit <= 0 ? BacktestRunRepositoryDefaults.DefaultListLimit : limit,
            1,
            BacktestRunRepositoryDefaults.MaximumListLimit);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresBacktestRunSql.SelectByWorkspace);
            AddScopeParameters(command, scope);
            command.Parameters.AddWithValue("limit", NpgsqlDbType.Integer, normalizedLimit);

            var runs = new List<BacktestRunEnvelope>();
            await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                runs.Add(ReadRecord(reader).Run);
            }

            return runs;
        }
        catch (NpgsqlException exception)
        {
            throw new BacktestStorageUnavailableException("Postgres saved backtest run list failed.", exception);
        }
    }

    public async Task<BacktestRunRecord?> GetAsync(
        BacktestWorkspaceScope scope,
        string runId,
        CancellationToken cancellationToken = default)
    {
        ValidateScope(scope);
        var normalizedRunId = BacktestRunId.Create(runId).Value;

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresBacktestRunSql.SelectByRunId);
            AddScopeParameters(command, scope);
            command.Parameters.AddWithValue("run_id", NpgsqlDbType.Text, normalizedRunId);

            await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            return await reader.ReadAsync(cancellationToken).ConfigureAwait(false) ? ReadRecord(reader) : null;
        }
        catch (NpgsqlException exception)
        {
            throw new BacktestStorageUnavailableException("Postgres saved backtest run read failed.", exception);
        }
    }

    public async Task<int> FailInterruptedRunningAsync(
        BacktestError error,
        CancellationToken cancellationToken = default)
    {
        var safeError = BacktestPersistenceSafety.NormalizeSafeError(error) ?? new BacktestError(
            BacktestErrorCodes.RunInterrupted,
            BacktestSafeMessages.RunInterrupted);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresBacktestRunSql.FailInterruptedRunningRuns);
            AddErrorParameters(command, safeError);
            command.Parameters.AddWithValue("observed_at_utc", NpgsqlDbType.TimestampTz, timeProvider.GetUtcNow());

            return await command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (NpgsqlException exception)
        {
            throw new BacktestStorageUnavailableException("Postgres saved backtest run recovery failed.", exception);
        }
    }

    public async Task<BacktestRunRecord?> ClaimNextQueuedAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresBacktestRunSql.ClaimNextQueuedRun);
            command.Parameters.AddWithValue("observed_at_utc", NpgsqlDbType.TimestampTz, timeProvider.GetUtcNow());

            await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            return await reader.ReadAsync(cancellationToken).ConfigureAwait(false) ? ReadRecord(reader) : null;
        }
        catch (NpgsqlException exception)
        {
            throw new BacktestStorageUnavailableException("Postgres saved backtest run queue claim failed.", exception);
        }
    }

    public async Task<BacktestRunRecord?> UpdateStatusAsync(
        BacktestWorkspaceScope scope,
        string runId,
        string status,
        BacktestError? error = null,
        JsonElement? result = null,
        CancellationToken cancellationToken = default)
    {
        ValidateScope(scope);
        var normalizedRunId = BacktestRunId.Create(runId).Value;
        var normalizedStatus = NormalizeStatus(status);
        var safeError = BacktestPersistenceSafety.NormalizeSafeError(error);
        var resultJson = BacktestPersistenceSafety.SerializeResult(result);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresBacktestRunSql.UpdateStatus);
            AddScopeParameters(command, scope);
            command.Parameters.AddWithValue("run_id", NpgsqlDbType.Text, normalizedRunId);
            command.Parameters.AddWithValue("status", NpgsqlDbType.Text, normalizedStatus);
            AddErrorParameters(command, safeError);
            command.Parameters.AddWithValue("result_json", NpgsqlDbType.Jsonb, NullableValue(resultJson));
            command.Parameters.AddWithValue("observed_at_utc", NpgsqlDbType.TimestampTz, timeProvider.GetUtcNow());

            await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            return await reader.ReadAsync(cancellationToken).ConfigureAwait(false) ? ReadRecord(reader) : null;
        }
        catch (NpgsqlException exception)
        {
            throw new BacktestStorageUnavailableException("Postgres saved backtest run status update failed.", exception);
        }
    }

    public async Task<BacktestRunRecord?> CancelAsync(
        BacktestWorkspaceScope scope,
        string runId,
        CancellationToken cancellationToken = default)
    {
        ValidateScope(scope);
        var normalizedRunId = BacktestRunId.Create(runId).Value;

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresBacktestRunSql.CancelRun);
            AddScopeParameters(command, scope);
            command.Parameters.AddWithValue("run_id", NpgsqlDbType.Text, normalizedRunId);
            command.Parameters.AddWithValue("observed_at_utc", NpgsqlDbType.TimestampTz, timeProvider.GetUtcNow());

            await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            if (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
            {
                return ReadRecord(reader);
            }
        }
        catch (NpgsqlException exception)
        {
            throw new BacktestStorageUnavailableException("Postgres saved backtest run cancel failed.", exception);
        }

        return await GetAsync(scope, normalizedRunId, cancellationToken).ConfigureAwait(false);
    }

    public async Task<BacktestRunRecord?> CreateRetryAsync(
        BacktestWorkspaceScope scope,
        string sourceRunId,
        BacktestRunRecord retryRun,
        CancellationToken cancellationToken = default)
    {
        ValidateScope(scope);
        ValidateQueuedRun(retryRun, requireNoSourceRun: true);
        EnsureScopeMatches(scope, retryRun.Scope);
        var normalizedSourceRunId = BacktestRunId.Create(sourceRunId).Value;

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresBacktestRunSql.InsertRetryRun);
            AddScopeParameters(command, scope);
            command.Parameters.AddWithValue("source_run_id", NpgsqlDbType.Text, normalizedSourceRunId);
            command.Parameters.AddWithValue("run_id", NpgsqlDbType.Text, BacktestRunId.Create(retryRun.Run.Id).Value);
            command.Parameters.AddWithValue("initial_capital", NpgsqlDbType.Numeric, retryRun.Run.Capital.InitialCapital);
            command.Parameters.AddWithValue("currency", NpgsqlDbType.Text, retryRun.Run.Capital.Currency);
            command.Parameters.AddWithValue("capital_source", NpgsqlDbType.Text, retryRun.Run.Capital.CapitalSource);
            command.Parameters.AddWithValue("created_at_utc", NpgsqlDbType.TimestampTz, retryRun.Run.CreatedAtUtc);
            command.Parameters.AddWithValue("updated_at_utc", NpgsqlDbType.TimestampTz, retryRun.Run.UpdatedAtUtc);

            await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
            return await reader.ReadAsync(cancellationToken).ConfigureAwait(false) ? ReadRecord(reader) : null;
        }
        catch (NpgsqlException exception)
        {
            throw new BacktestStorageUnavailableException("Postgres saved backtest run retry create failed.", exception);
        }
    }

    private static void AddRunParameters(NpgsqlCommand command, BacktestRunRecord record)
    {
        AddScopeParameters(command, record.Scope);
        command.Parameters.AddWithValue("run_id", NpgsqlDbType.Text, BacktestRunId.Create(record.Run.Id).Value);
        command.Parameters.AddWithValue("source_run_id", NpgsqlDbType.Text, NullableValue(record.Run.SourceRunId));
        command.Parameters.AddWithValue("status", NpgsqlDbType.Text, NormalizeStatus(record.Run.Status));
        command.Parameters.AddWithValue("request_json", NpgsqlDbType.Jsonb, BacktestPersistenceSafety.SerializeRequestSnapshot(record.Run.Request));
        command.Parameters.AddWithValue("initial_capital", NpgsqlDbType.Numeric, record.Run.Capital.InitialCapital);
        command.Parameters.AddWithValue("currency", NpgsqlDbType.Text, record.Run.Capital.Currency);
        command.Parameters.AddWithValue("capital_source", NpgsqlDbType.Text, record.Run.Capital.CapitalSource);
        AddErrorParameters(command, BacktestPersistenceSafety.NormalizeSafeError(record.Run.Error));
        command.Parameters.AddWithValue("result_json", NpgsqlDbType.Jsonb, NullableValue(BacktestPersistenceSafety.SerializeResult(record.Run.Result)));
        command.Parameters.AddWithValue("created_at_utc", NpgsqlDbType.TimestampTz, record.Run.CreatedAtUtc);
        command.Parameters.AddWithValue("updated_at_utc", NpgsqlDbType.TimestampTz, record.Run.UpdatedAtUtc);
        command.Parameters.AddWithValue("started_at_utc", NpgsqlDbType.TimestampTz, NullableValue(record.Run.StartedAtUtc));
        command.Parameters.AddWithValue("completed_at_utc", NpgsqlDbType.TimestampTz, NullableValue(record.Run.CompletedAtUtc));
    }

    private static void AddScopeParameters(NpgsqlCommand command, BacktestWorkspaceScope scope)
    {
        command.Parameters.AddWithValue("user_id", NpgsqlDbType.Text, scope.UserId);
        command.Parameters.AddWithValue("workspace_id", NpgsqlDbType.Text, scope.WorkspaceId);
    }

    private static void AddErrorParameters(NpgsqlCommand command, BacktestError? error)
    {
        command.Parameters.AddWithValue("error_code", NpgsqlDbType.Text, NullableValue(error?.Code));
        command.Parameters.AddWithValue("error_message", NpgsqlDbType.Text, NullableValue(error?.Message));
    }

    private static BacktestRunRecord ReadRecord(NpgsqlDataReader reader)
    {
        var scope = new BacktestWorkspaceScope(reader.GetString(0), reader.GetString(1));
        var request = BacktestPersistenceSafety.DeserializeRequestSnapshot(reader.GetString(5));
        var result = reader.IsDBNull(11)
            ? null
            : BacktestPersistenceSafety.DeserializeResult(reader.GetString(11));
        var error = reader.IsDBNull(9)
            ? null
            : new BacktestError(reader.GetString(9), reader.IsDBNull(10) ? "Backtest request failed." : reader.GetString(10));

        var run = new BacktestRunEnvelope(
            Id: reader.GetString(2),
            Status: reader.GetString(4),
            SourceRunId: reader.IsDBNull(3) ? null : reader.GetString(3),
            Request: request,
            Capital: new BacktestCapitalSnapshot(
                reader.GetDecimal(6),
                reader.GetString(7),
                reader.GetString(8)),
            CreatedAtUtc: reader.GetFieldValue<DateTimeOffset>(12),
            UpdatedAtUtc: reader.GetFieldValue<DateTimeOffset>(13),
            StartedAtUtc: reader.IsDBNull(14) ? null : reader.GetFieldValue<DateTimeOffset>(14),
            CompletedAtUtc: reader.IsDBNull(15) ? null : reader.GetFieldValue<DateTimeOffset>(15),
            Error: error,
            Result: result);

        return new BacktestRunRecord(scope, run);
    }

    private static void ValidateQueuedRun(BacktestRunRecord? record, bool requireNoSourceRun)
    {
        ArgumentNullException.ThrowIfNull(record);
        ValidateScope(record.Scope);
        _ = BacktestRunId.Create(record.Run.Id);
        if (!string.Equals(record.Run.Status, BacktestRunStatuses.Queued, StringComparison.OrdinalIgnoreCase))
        {
            throw new BacktestValidationException(
                BacktestErrorCodes.InvalidStatusTransition,
                "Saved backtest creation requires a queued run snapshot.",
                nameof(record.Run.Status));
        }

        if (requireNoSourceRun && !string.IsNullOrWhiteSpace(record.Run.SourceRunId))
        {
            throw new BacktestValidationException(
                BacktestErrorCodes.InvalidStatusTransition,
                "Retry creation assigns the source run id from the saved source run.",
                nameof(record.Run.SourceRunId));
        }

        if (record.Run.Capital.InitialCapital <= 0)
        {
            throw new BacktestValidationException(
                BacktestErrorCodes.CapitalUnavailable,
                BacktestSafeMessages.CapitalUnavailable,
                nameof(record.Run.Capital.InitialCapital));
        }

        if (string.IsNullOrWhiteSpace(record.Run.Capital.CapitalSource) ||
            string.Equals(record.Run.Capital.CapitalSource, "unavailable", StringComparison.OrdinalIgnoreCase))
        {
            throw new BacktestValidationException(
                BacktestErrorCodes.CapitalUnavailable,
                BacktestSafeMessages.CapitalUnavailable,
                nameof(record.Run.Capital.CapitalSource));
        }

        _ = BacktestPersistenceSafety.NormalizeSafeRequestSnapshot(record.Run.Request);
    }

    private static void ValidateScope(BacktestWorkspaceScope? scope)
    {
        ArgumentNullException.ThrowIfNull(scope);
        ArgumentException.ThrowIfNullOrWhiteSpace(scope.UserId);
        ArgumentException.ThrowIfNullOrWhiteSpace(scope.WorkspaceId);
    }

    private static void EnsureScopeMatches(BacktestWorkspaceScope expected, BacktestWorkspaceScope actual)
    {
        if (!string.Equals(expected.UserId, actual.UserId, StringComparison.Ordinal) ||
            !string.Equals(expected.WorkspaceId, actual.WorkspaceId, StringComparison.Ordinal))
        {
            throw new ArgumentException("Retry run scope must match the saved source run scope.", nameof(actual));
        }
    }

    private static string NormalizeStatus(string? status)
    {
        if (!BacktestRunStatuses.IsSupported(status))
        {
            throw new BacktestValidationException(
                BacktestErrorCodes.InvalidStatusTransition,
                "Backtest run status is not supported.",
                nameof(status));
        }

        return status!.Trim().ToLowerInvariant();
    }

    private static object NullableValue<T>(T? value)
        where T : struct => value.HasValue ? value.Value : DBNull.Value;

    private static object NullableValue(string? value) => value is null ? DBNull.Value : value;
}
