using Microsoft.Extensions.Configuration;
using Npgsql;

namespace ATrade.MarketData.Timescale;

public interface ITimescaleMarketDataDataSourceProvider
{
    NpgsqlDataSource GetDataSource();
}

public sealed class TimescaleMarketDataDataSourceProvider : ITimescaleMarketDataDataSourceProvider, IAsyncDisposable, IDisposable
{
    public const string DefaultConnectionStringName = "timescaledb";
    public const string DisallowedWorkspaceConnectionStringName = "postgres";

    private readonly IConfiguration configuration;
    private readonly string connectionStringName;
    private readonly Lazy<NpgsqlDataSource> dataSource;

    public TimescaleMarketDataDataSourceProvider(IConfiguration configuration)
        : this(configuration, DefaultConnectionStringName)
    {
    }

    public TimescaleMarketDataDataSourceProvider(IConfiguration configuration, string connectionStringName)
    {
        ArgumentNullException.ThrowIfNull(configuration);
        ArgumentException.ThrowIfNullOrWhiteSpace(connectionStringName);

        if (string.Equals(connectionStringName.Trim(), DisallowedWorkspaceConnectionStringName, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException($"Timescale market-data storage must use ConnectionStrings:{DefaultConnectionStringName}; ConnectionStrings:{DisallowedWorkspaceConnectionStringName} is reserved for regular Postgres workspace data.");
        }

        this.configuration = configuration;
        this.connectionStringName = connectionStringName.Trim();
        dataSource = new Lazy<NpgsqlDataSource>(CreateDataSource, LazyThreadSafetyMode.ExecutionAndPublication);
    }

    public NpgsqlDataSource GetDataSource()
    {
        try
        {
            return dataSource.Value;
        }
        catch (Exception exception) when (exception is InvalidOperationException or ArgumentException or NpgsqlException)
        {
            throw new TimescaleMarketDataStorageUnavailableException(
                $"TimescaleDB connection string 'ConnectionStrings:{connectionStringName}' is not available for market-data persistence.",
                exception);
        }
    }

    public async ValueTask DisposeAsync()
    {
        if (dataSource.IsValueCreated)
        {
            await dataSource.Value.DisposeAsync().ConfigureAwait(false);
        }
    }

    public void Dispose()
    {
        if (dataSource.IsValueCreated)
        {
            dataSource.Value.Dispose();
        }
    }

    private NpgsqlDataSource CreateDataSource()
    {
        var connectionString = configuration.GetConnectionString(connectionStringName);
        if (string.IsNullOrWhiteSpace(connectionString))
        {
            throw new InvalidOperationException($"ConnectionStrings:{connectionStringName} is required for Timescale market-data persistence.");
        }

        return NpgsqlDataSource.Create(connectionString);
    }
}
