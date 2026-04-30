using Npgsql;

namespace ATrade.MarketData.Timescale;

public interface ITimescaleMarketDataSchemaInitializer
{
    Task InitializeAsync(CancellationToken cancellationToken = default);
}

public sealed class TimescaleMarketDataSchemaInitializer(ITimescaleMarketDataDataSourceProvider dataSourceProvider) : ITimescaleMarketDataSchemaInitializer
{
    public async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            await using var command = dataSourceProvider.GetDataSource().CreateCommand(TimescaleMarketDataSql.Initialize);
            await command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (TimescaleMarketDataStorageUnavailableException)
        {
            throw;
        }
        catch (NpgsqlException exception)
        {
            throw new TimescaleMarketDataStorageUnavailableException("Timescale market-data schema initialization failed.", exception);
        }
    }
}
