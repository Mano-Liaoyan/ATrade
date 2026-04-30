using ATrade.MarketData;
using ATrade.MarketData.Timescale;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace ATrade.MarketData.Timescale.Tests;

public sealed class TimescaleMarketDataIntegrationTests
{
    private const string ConnectionStringEnvironmentVariable = "ATRADE_MARKET_DATA_TIMESCALE_TEST_CONNECTION_STRING";

    [Fact]
    public async Task RepositoryInitializesSchemaAndRoundTripsFakeMarketDataRowsWhenConnectionStringIsProvided()
    {
        var connectionString = Environment.GetEnvironmentVariable(ConnectionStringEnvironmentVariable);
        if (string.IsNullOrWhiteSpace(connectionString))
        {
            return;
        }

        var generatedAtUtc = DateTimeOffset.UtcNow;
        var services = new ServiceCollection();
        services.AddTimescaleMarketDataPersistence(new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                [$"ConnectionStrings:{TimescaleMarketDataDataSourceProvider.DefaultConnectionStringName}"] = connectionString,
                [TimescaleMarketDataEnvironmentVariables.CacheFreshnessMinutes] = "30",
            })
            .Build());

        await using var provider = services.BuildServiceProvider();
        await provider.GetRequiredService<ITimescaleMarketDataSchemaInitializer>().InitializeAsync();
        var repository = provider.GetRequiredService<ITimescaleMarketDataRepository>();

        var symbol = new TimescaleMarketDataSymbol(
            Provider: "test-provider",
            ProviderSymbolId: $"test-{Guid.NewGuid():N}",
            Symbol: $"TST{Random.Shared.Next(1000, 9999)}",
            Name: "Integration Test Corp",
            Exchange: "TEST",
            Currency: "USD",
            AssetClass: MarketDataAssetClasses.Stock);

        await repository.UpsertCandleSeriesAsync(new TimescaleCandleSeries(
            symbol,
            MarketDataTimeframes.OneDay,
            "integration-history",
            generatedAtUtc,
            new[]
            {
                new OhlcvCandle(generatedAtUtc.AddDays(-1), 10.00m, 11.00m, 9.50m, 10.75m, 123_456),
                new OhlcvCandle(generatedAtUtc, 10.75m, 12.00m, 10.25m, 11.50m, 234_567),
            }));

        var freshCandles = await repository.GetFreshCandleSeriesAsync(new TimescaleFreshCandleSeriesQuery(
            symbol.Provider,
            "integration-history",
            symbol.Symbol,
            MarketDataTimeframes.OneDay,
            generatedAtUtc.AddMinutes(-1)));

        Assert.NotNull(freshCandles);
        Assert.Equal(symbol.ProviderSymbolId, freshCandles.Symbol.ProviderSymbolId);
        Assert.Equal(2, freshCandles.Candles.Count);
        Assert.Equal(11.50m, freshCandles.Candles[^1].Close);

        await repository.UpsertTrendingSnapshotAsync(new TimescaleTrendingSnapshot(
            symbol.Provider,
            "integration-scanner",
            generatedAtUtc,
            new[]
            {
                new TimescaleTrendingSnapshotSymbol(
                    symbol,
                    "Technology",
                    LastPrice: 11.50m,
                    ChangePercent: 2.25m,
                    Score: 88.5m,
                    new TrendingFactorBreakdown(3.1m, 2.2m, 1.3m, 0.4m),
                    new[] { "integration-test", "fake-market-data" }),
            }));

        var freshSnapshot = await repository.GetFreshTrendingSnapshotAsync(new TimescaleFreshTrendingSnapshotQuery(
            symbol.Provider,
            "integration-scanner",
            generatedAtUtc.AddMinutes(-1),
            symbol.Symbol));

        Assert.NotNull(freshSnapshot);
        var trendingSymbol = Assert.Single(freshSnapshot.Symbols);
        Assert.Equal(symbol.ProviderSymbolId, trendingSymbol.Symbol.ProviderSymbolId);
        Assert.Equal(88.5m, trendingSymbol.Score);
        Assert.Contains("fake-market-data", trendingSymbol.Reasons);
    }
}
