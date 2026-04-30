using Npgsql;
using NpgsqlTypes;

namespace ATrade.Workspaces;

public sealed class PostgresWorkspaceWatchlistRepository(IWorkspacePostgresDataSourceProvider dataSourceProvider, TimeProvider timeProvider) : IWorkspaceWatchlistRepository
{
    public PostgresWorkspaceWatchlistRepository(IWorkspacePostgresDataSourceProvider dataSourceProvider)
        : this(dataSourceProvider, TimeProvider.System)
    {
    }

    public async Task<WorkspaceWatchlistResponse> GetAsync(WorkspaceIdentity identity, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(identity);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresWorkspaceWatchlistSql.SelectByWorkspace);
            AddIdentityParameters(command, identity);

            var symbols = new List<WorkspaceWatchlistSymbol>();
            await using var reader = await command.ExecuteReaderAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                symbols.Add(ReadSymbol(reader));
            }

            return new WorkspaceWatchlistResponse(identity.UserId, identity.WorkspaceId, symbols);
        }
        catch (NpgsqlException exception)
        {
            throw new WorkspaceStorageUnavailableException("Postgres workspace watchlist read failed.", exception);
        }
    }

    public async Task<WorkspaceWatchlistResponse> PinAsync(
        WorkspaceIdentity identity,
        WorkspaceWatchlistSymbolInput symbol,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(identity);
        var normalizedSymbol = WorkspaceWatchlistNormalizer.Normalize(symbol);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresWorkspaceWatchlistSql.UpsertPinnedSymbol);
            AddIdentityParameters(command, identity);
            AddSymbolParameters(command, normalizedSymbol, timeProvider.GetUtcNow());
            await command.ExecuteNonQueryAsync(cancellationToken);
        }
        catch (NpgsqlException exception)
        {
            throw new WorkspaceStorageUnavailableException("Postgres workspace watchlist pin failed.", exception);
        }

        return await GetAsync(identity, cancellationToken);
    }

    public async Task<WorkspaceWatchlistResponse> ReplaceAsync(
        WorkspaceIdentity identity,
        IReadOnlyList<WorkspaceWatchlistSymbolInput> symbols,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(identity);
        ArgumentNullException.ThrowIfNull(symbols);
        var normalizedSymbols = WorkspaceWatchlistNormalizer.NormalizeReplacement(symbols);

        try
        {
            await using var connection = await dataSourceProvider.GetDataSource().OpenConnectionAsync(cancellationToken);
            await using var transaction = await connection.BeginTransactionAsync(cancellationToken);

            await using (var deleteCommand = connection.CreateCommand())
            {
                deleteCommand.Transaction = transaction;
                deleteCommand.CommandText = PostgresWorkspaceWatchlistSql.DeleteWorkspacePins;
                AddIdentityParameters(deleteCommand, identity);
                await deleteCommand.ExecuteNonQueryAsync(cancellationToken);
            }

            var observedAtUtc = timeProvider.GetUtcNow();
            foreach (var normalizedSymbol in normalizedSymbols)
            {
                await using var insertCommand = connection.CreateCommand();
                insertCommand.Transaction = transaction;
                insertCommand.CommandText = PostgresWorkspaceWatchlistSql.InsertReplacementPinnedSymbol;
                AddIdentityParameters(insertCommand, identity);
                AddSymbolParameters(insertCommand, normalizedSymbol, observedAtUtc);
                await insertCommand.ExecuteNonQueryAsync(cancellationToken);
            }

            await transaction.CommitAsync(cancellationToken);
        }
        catch (NpgsqlException exception)
        {
            throw new WorkspaceStorageUnavailableException("Postgres workspace watchlist replacement failed.", exception);
        }

        return await GetAsync(identity, cancellationToken);
    }

    public async Task<WorkspaceWatchlistResponse> UnpinAsync(
        WorkspaceIdentity identity,
        string symbol,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(identity);
        var normalizedSymbol = WorkspaceSymbolNormalizer.Normalize(symbol);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresWorkspaceWatchlistSql.DeletePinnedSymbol);
            AddIdentityParameters(command, identity);
            command.Parameters.AddWithValue("symbol", NpgsqlDbType.Text, normalizedSymbol);
            await using var reader = await command.ExecuteReaderAsync(cancellationToken);
            if (await reader.ReadAsync(cancellationToken))
            {
                var candidateCount = reader.GetInt32(0);
                if (candidateCount > 1)
                {
                    throw new WorkspaceWatchlistValidationException(
                        WorkspaceWatchlistErrorCodes.AmbiguousSymbol,
                        $"Symbol '{normalizedSymbol}' has multiple market-specific pins. Remove one by instrumentKey instead.",
                        nameof(symbol));
                }
            }
        }
        catch (NpgsqlException exception)
        {
            throw new WorkspaceStorageUnavailableException("Postgres workspace watchlist unpin failed.", exception);
        }

        return await GetAsync(identity, cancellationToken);
    }

    public async Task<WorkspaceWatchlistResponse> UnpinByInstrumentKeyAsync(
        WorkspaceIdentity identity,
        string instrumentKey,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(identity);
        var normalizedInstrumentKey = WorkspaceWatchlistInstrumentKey.NormalizeExistingKey(instrumentKey);

        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresWorkspaceWatchlistSql.DeletePinnedInstrumentKey);
            AddIdentityParameters(command, identity);
            command.Parameters.AddWithValue("instrument_key", NpgsqlDbType.Text, normalizedInstrumentKey);
            await command.ExecuteNonQueryAsync(cancellationToken);
        }
        catch (NpgsqlException exception)
        {
            throw new WorkspaceStorageUnavailableException("Postgres workspace watchlist exact unpin failed.", exception);
        }

        return await GetAsync(identity, cancellationToken);
    }

    private static void AddIdentityParameters(NpgsqlCommand command, WorkspaceIdentity identity)
    {
        command.Parameters.AddWithValue("user_id", NpgsqlDbType.Text, identity.UserId);
        command.Parameters.AddWithValue("workspace_id", NpgsqlDbType.Text, identity.WorkspaceId);
    }

    private static void AddSymbolParameters(NpgsqlCommand command, NormalizedWorkspaceWatchlistSymbolInput symbol, DateTimeOffset observedAtUtc)
    {
        command.Parameters.AddWithValue("instrument_key", NpgsqlDbType.Text, symbol.InstrumentKey);
        command.Parameters.AddWithValue("symbol", NpgsqlDbType.Text, symbol.Symbol);
        command.Parameters.AddWithValue("provider", NpgsqlDbType.Text, symbol.Provider);
        command.Parameters.AddWithValue("provider_symbol_id", NpgsqlDbType.Text, NullableValue(symbol.ProviderSymbolId));
        command.Parameters.AddWithValue("ibkr_conid", NpgsqlDbType.Bigint, NullableValue(symbol.IbkrConid));
        command.Parameters.AddWithValue("name", NpgsqlDbType.Text, NullableValue(symbol.Name));
        command.Parameters.AddWithValue("exchange", NpgsqlDbType.Text, NullableValue(symbol.Exchange));
        command.Parameters.AddWithValue("currency", NpgsqlDbType.Text, NullableValue(symbol.Currency));
        command.Parameters.AddWithValue("asset_class", NpgsqlDbType.Text, NullableValue(symbol.AssetClass));
        command.Parameters.AddWithValue("sort_order", NpgsqlDbType.Integer, symbol.SortOrder);
        command.Parameters.AddWithValue("observed_at_utc", NpgsqlDbType.TimestampTz, observedAtUtc);
    }

    private static object NullableValue<T>(T? value)
        where T : struct => value.HasValue ? value.Value : DBNull.Value;

    private static object NullableValue(string? value) => value is null ? DBNull.Value : value;

    private static WorkspaceWatchlistSymbol ReadSymbol(NpgsqlDataReader reader)
    {
        var symbol = reader.GetString(0);
        var instrumentKey = reader.GetString(1);

        return new WorkspaceWatchlistSymbol(
            symbol,
            instrumentKey,
            instrumentKey,
            reader.GetString(2),
            reader.IsDBNull(3) ? null : reader.GetString(3),
            reader.IsDBNull(4) ? null : reader.GetInt64(4),
            reader.IsDBNull(5) ? null : reader.GetString(5),
            reader.IsDBNull(6) ? null : reader.GetString(6),
            reader.IsDBNull(7) ? null : reader.GetString(7),
            reader.IsDBNull(8) ? null : reader.GetString(8),
            reader.GetInt32(9),
            reader.GetFieldValue<DateTimeOffset>(10),
            reader.GetFieldValue<DateTimeOffset>(11));
    }
}
