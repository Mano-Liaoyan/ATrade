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
            await command.ExecuteNonQueryAsync(cancellationToken);
        }
        catch (NpgsqlException exception)
        {
            throw new WorkspaceStorageUnavailableException("Postgres workspace watchlist unpin failed.", exception);
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

    private static WorkspaceWatchlistSymbol ReadSymbol(NpgsqlDataReader reader) => new(
        reader.GetString(0),
        reader.GetString(1),
        reader.IsDBNull(2) ? null : reader.GetString(2),
        reader.IsDBNull(3) ? null : reader.GetInt64(3),
        reader.IsDBNull(4) ? null : reader.GetString(4),
        reader.IsDBNull(5) ? null : reader.GetString(5),
        reader.IsDBNull(6) ? null : reader.GetString(6),
        reader.IsDBNull(7) ? null : reader.GetString(7),
        reader.GetInt32(8),
        reader.GetFieldValue<DateTimeOffset>(9),
        reader.GetFieldValue<DateTimeOffset>(10));
}
