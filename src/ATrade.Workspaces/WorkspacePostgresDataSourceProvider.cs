using Microsoft.Extensions.Configuration;
using Npgsql;

namespace ATrade.Workspaces;

public interface IWorkspacePostgresDataSourceProvider
{
    NpgsqlDataSource GetDataSource();
}

public sealed class WorkspacePostgresDataSourceProvider : IWorkspacePostgresDataSourceProvider, IAsyncDisposable, IDisposable
{
    public const string DefaultConnectionStringName = "postgres";

    private readonly IConfiguration configuration;
    private readonly string connectionStringName;
    private readonly Lazy<NpgsqlDataSource> dataSource;

    public WorkspacePostgresDataSourceProvider(IConfiguration configuration)
        : this(configuration, DefaultConnectionStringName)
    {
    }

    public WorkspacePostgresDataSourceProvider(IConfiguration configuration, string connectionStringName)
    {
        this.configuration = configuration;
        this.connectionStringName = connectionStringName;
        dataSource = new Lazy<NpgsqlDataSource>(CreateDataSource, LazyThreadSafetyMode.ExecutionAndPublication);
    }

    public NpgsqlDataSource GetDataSource()
    {
        try
        {
            return dataSource.Value;
        }
        catch (Exception exception) when (exception is InvalidOperationException or ArgumentException)
        {
            throw new WorkspaceStorageUnavailableException(
                $"Postgres connection string 'ConnectionStrings:{connectionStringName}' is not available for workspace watchlists.",
                exception);
        }
    }

    public async ValueTask DisposeAsync()
    {
        if (dataSource.IsValueCreated)
        {
            await dataSource.Value.DisposeAsync();
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
            throw new InvalidOperationException($"ConnectionStrings:{connectionStringName} is required for workspace watchlists.");
        }

        return NpgsqlDataSource.Create(connectionString);
    }
}
