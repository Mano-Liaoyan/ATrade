using Npgsql;

namespace ATrade.Backtesting;

public sealed class PostgresBacktestRunSchemaInitializer(IBacktestingPostgresDataSourceProvider dataSourceProvider) : IBacktestRunSchemaInitializer
{
    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(PostgresBacktestRunSql.Initialize);
            await command.ExecuteNonQueryAsync(cancellationToken);
        }
        catch (NpgsqlException exception)
        {
            throw new BacktestStorageUnavailableException("Postgres saved backtest run schema initialization failed.", exception);
        }
    }
}
