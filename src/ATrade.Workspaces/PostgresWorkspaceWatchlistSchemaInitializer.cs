using Npgsql;

namespace ATrade.Workspaces;

public sealed class PostgresWorkspaceWatchlistSchemaInitializer(IWorkspacePostgresDataSourceProvider dataSourceProvider) : IWorkspaceWatchlistSchemaInitializer
{
    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresWorkspaceWatchlistSql.Initialize);
            await command.ExecuteNonQueryAsync(cancellationToken);
        }
        catch (NpgsqlException exception)
        {
            throw new WorkspaceStorageUnavailableException("Postgres workspace watchlist schema initialization failed.", exception);
        }
    }
}
