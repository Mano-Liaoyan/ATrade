using Microsoft.Extensions.Configuration;
using Npgsql;

namespace ATrade.Accounts;

public interface IAccountsPostgresDataSourceProvider
{
    NpgsqlDataSource GetDataSource();
}

public sealed class AccountsPostgresDataSourceProvider : IAccountsPostgresDataSourceProvider, IAsyncDisposable, IDisposable
{
    public const string DefaultConnectionStringName = "postgres";

    private readonly IConfiguration configuration;
    private readonly string connectionStringName;
    private readonly Lazy<NpgsqlDataSource> dataSource;

    public AccountsPostgresDataSourceProvider(IConfiguration configuration)
        : this(configuration, DefaultConnectionStringName)
    {
    }

    public AccountsPostgresDataSourceProvider(IConfiguration configuration, string connectionStringName)
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
            throw new PaperCapitalStorageUnavailableException(
                $"Postgres connection string 'ConnectionStrings:{connectionStringName}' is not available for local paper capital.",
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
            throw new InvalidOperationException($"ConnectionStrings:{connectionStringName} is required for local paper capital.");
        }

        return NpgsqlDataSource.Create(connectionString);
    }
}
