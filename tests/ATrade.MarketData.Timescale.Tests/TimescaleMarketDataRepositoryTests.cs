using ATrade.MarketData.Timescale;
using Microsoft.Extensions.Configuration;

namespace ATrade.MarketData.Timescale.Tests;

public sealed class TimescaleMarketDataRepositoryTests
{
    [Fact]
    public void DataSourceProviderDefaultsToTimescaleConnectionStringName()
    {
        Assert.Equal("timescaledb", TimescaleMarketDataDataSourceProvider.DefaultConnectionStringName);
    }

    [Fact]
    public void DataSourceProviderRejectsRegularPostgresWorkspaceConnectionName()
    {
        var exception = Assert.Throws<InvalidOperationException>(() => new TimescaleMarketDataDataSourceProvider(CreateConfiguration(), "postgres"));

        Assert.Contains("ConnectionStrings:timescaledb", exception.Message, StringComparison.Ordinal);
        Assert.Contains("ConnectionStrings:postgres", exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void DataSourceProviderReportsMissingTimescaleConnectionAsStorageUnavailable()
    {
        using var provider = new TimescaleMarketDataDataSourceProvider(CreateConfiguration());

        var exception = Assert.Throws<TimescaleMarketDataStorageUnavailableException>(provider.GetDataSource);

        Assert.Contains("ConnectionStrings:timescaledb", exception.Message, StringComparison.Ordinal);
        Assert.IsType<InvalidOperationException>(exception.InnerException);
    }

    private static IConfiguration CreateConfiguration() => new ConfigurationBuilder()
        .AddInMemoryCollection(new Dictionary<string, string?>())
        .Build();
}
