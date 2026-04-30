using ATrade.MarketData.Timescale;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;

namespace ATrade.MarketData.Timescale.Tests;

public sealed class TimescaleMarketDataServiceCollectionExtensionsTests
{
    [Fact]
    public void AddTimescaleMarketDataPersistenceRegistersOptionsAndRepositoryServices()
    {
        var services = new ServiceCollection();
        services.AddTimescaleMarketDataPersistence(CreateConfiguration(new()
        {
            [$"ConnectionStrings:{TimescaleMarketDataDataSourceProvider.DefaultConnectionStringName}"] = "Host=localhost;Database=atrade;Username=atrade;Password=atrade",
            [TimescaleMarketDataEnvironmentVariables.CacheFreshnessMinutes] = "12",
        }));

        using var provider = services.BuildServiceProvider();

        Assert.Equal(TimeSpan.FromMinutes(12), provider.GetRequiredService<TimescaleMarketDataOptions>().CacheFreshnessPeriod);
        Assert.Equal(TimeSpan.FromMinutes(12), provider.GetRequiredService<IOptions<TimescaleMarketDataOptions>>().Value.CacheFreshnessPeriod);
        Assert.IsType<TimescaleMarketDataDataSourceProvider>(provider.GetRequiredService<ITimescaleMarketDataDataSourceProvider>());
        Assert.IsType<TimescaleMarketDataSchemaInitializer>(provider.GetRequiredService<ITimescaleMarketDataSchemaInitializer>());
        Assert.IsType<TimescaleMarketDataRepository>(provider.GetRequiredService<ITimescaleMarketDataRepository>());
    }

    [Fact]
    public void RegisteredDataSourceProviderReportsMissingTimescaleConnectionAsStorageUnavailable()
    {
        var services = new ServiceCollection();
        services.AddTimescaleMarketDataPersistence(CreateConfiguration());
        using var provider = services.BuildServiceProvider();

        var dataSourceProvider = provider.GetRequiredService<ITimescaleMarketDataDataSourceProvider>();
        var exception = Assert.Throws<TimescaleMarketDataStorageUnavailableException>(dataSourceProvider.GetDataSource);

        Assert.Contains("ConnectionStrings:timescaledb", exception.Message, StringComparison.Ordinal);
    }

    private static IConfiguration CreateConfiguration(Dictionary<string, string?>? values = null) => new ConfigurationBuilder()
        .AddInMemoryCollection(values ?? new Dictionary<string, string?>())
        .Build();
}
