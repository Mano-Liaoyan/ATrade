using ATrade.MarketData.Timescale;
using Microsoft.Extensions.Configuration;

namespace ATrade.MarketData.Timescale.Tests;

public sealed class TimescaleMarketDataOptionsTests
{
    [Fact]
    public void FromConfigurationDefaultsToThirtyMinutesWhenFreshnessIsAbsent()
    {
        var options = TimescaleMarketDataOptions.FromConfiguration(CreateConfiguration());

        Assert.Equal(TimeSpan.FromMinutes(30), options.CacheFreshnessPeriod);
    }

    [Fact]
    public void FromConfigurationDefaultsToThirtyMinutesWhenFreshnessIsBlank()
    {
        var options = TimescaleMarketDataOptions.FromConfiguration(CreateConfiguration(new()
        {
            [TimescaleMarketDataEnvironmentVariables.CacheFreshnessMinutes] = "   ",
        }));

        Assert.Equal(TimeSpan.FromMinutes(30), options.CacheFreshnessPeriod);
    }

    [Theory]
    [InlineData("1", 1)]
    [InlineData("45", 45)]
    [InlineData("0.5", 0.5)]
    public void FromConfigurationUsesConfiguredPositiveFreshnessMinutes(string configuredMinutes, double expectedMinutes)
    {
        var options = TimescaleMarketDataOptions.FromConfiguration(CreateConfiguration(new()
        {
            [TimescaleMarketDataEnvironmentVariables.CacheFreshnessMinutes] = configuredMinutes,
        }));

        Assert.Equal(TimeSpan.FromMinutes(expectedMinutes), options.CacheFreshnessPeriod);
    }

    [Theory]
    [InlineData("0")]
    [InlineData("-1")]
    [InlineData("not-a-number")]
    [InlineData("NaN")]
    [InlineData("Infinity")]
    public void FromConfigurationRejectsInvalidFreshnessMinutes(string configuredMinutes)
    {
        var exception = Assert.Throws<InvalidOperationException>(() => TimescaleMarketDataOptions.FromConfiguration(CreateConfiguration(new()
        {
            [TimescaleMarketDataEnvironmentVariables.CacheFreshnessMinutes] = configuredMinutes,
        })));

        Assert.Contains(TimescaleMarketDataEnvironmentVariables.CacheFreshnessMinutes, exception.Message, StringComparison.Ordinal);
    }

    private static IConfiguration CreateConfiguration(Dictionary<string, string?>? values = null)
    {
        return new ConfigurationBuilder()
            .AddInMemoryCollection(values ?? new Dictionary<string, string?>())
            .Build();
    }
}
