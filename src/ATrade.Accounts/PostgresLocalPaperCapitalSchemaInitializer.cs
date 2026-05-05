using Npgsql;

namespace ATrade.Accounts;

public sealed class PostgresLocalPaperCapitalSchemaInitializer(IAccountsPostgresDataSourceProvider dataSourceProvider) : ILocalPaperCapitalSchemaInitializer
{
    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresLocalPaperCapitalSql.Initialize);
            await command.ExecuteNonQueryAsync(cancellationToken);
        }
        catch (NpgsqlException exception)
        {
            throw new PaperCapitalStorageUnavailableException("Postgres local paper capital schema initialization failed.", exception);
        }
    }
}
