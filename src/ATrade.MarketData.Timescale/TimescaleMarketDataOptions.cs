using System.Globalization;
using Microsoft.Extensions.Configuration;

namespace ATrade.MarketData.Timescale;

public sealed class TimescaleMarketDataOptions
{
    public const int DefaultCacheFreshnessMinutes = 30;

    public TimeSpan CacheFreshnessPeriod { get; init; } = TimeSpan.FromMinutes(DefaultCacheFreshnessMinutes);

    public static TimescaleMarketDataOptions FromConfiguration(IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(configuration);

        var configuredFreshness = configuration[TimescaleMarketDataEnvironmentVariables.CacheFreshnessMinutes];
        if (string.IsNullOrWhiteSpace(configuredFreshness))
        {
            return new TimescaleMarketDataOptions();
        }

        return new TimescaleMarketDataOptions
        {
            CacheFreshnessPeriod = ParsePositiveMinutes(configuredFreshness),
        };
    }

    private static TimeSpan ParsePositiveMinutes(string configuredFreshness)
    {
        if (!double.TryParse(configuredFreshness.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var minutes)
            || double.IsNaN(minutes)
            || double.IsInfinity(minutes)
            || minutes <= 0)
        {
            throw new InvalidOperationException($"{TimescaleMarketDataEnvironmentVariables.CacheFreshnessMinutes} must be a positive number of minutes.");
        }

        try
        {
            var freshnessPeriod = TimeSpan.FromMinutes(minutes);
            return freshnessPeriod > TimeSpan.Zero
                ? freshnessPeriod
                : throw new InvalidOperationException($"{TimescaleMarketDataEnvironmentVariables.CacheFreshnessMinutes} must be greater than zero minutes.");
        }
        catch (OverflowException exception)
        {
            throw new InvalidOperationException($"{TimescaleMarketDataEnvironmentVariables.CacheFreshnessMinutes} is too large to represent as a TimeSpan.", exception);
        }
    }
}
