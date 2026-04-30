using ATrade.MarketData;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;

namespace ATrade.MarketData.Timescale;

public static class TimescaleMarketDataServiceCollectionExtensions
{
    public static IServiceCollection AddTimescaleMarketDataPersistence(this IServiceCollection services, IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(services);
        ArgumentNullException.ThrowIfNull(configuration);

        var options = TimescaleMarketDataOptions.FromConfiguration(configuration);
        services.AddSingleton<IOptions<TimescaleMarketDataOptions>>(_ => Options.Create(options));
        services.AddSingleton(static serviceProvider => serviceProvider.GetRequiredService<IOptions<TimescaleMarketDataOptions>>().Value);
        services.AddSingleton<ITimescaleMarketDataDataSourceProvider>(_ => new TimescaleMarketDataDataSourceProvider(configuration));
        services.AddSingleton<ITimescaleMarketDataSchemaInitializer, TimescaleMarketDataSchemaInitializer>();
        services.AddSingleton<ITimescaleMarketDataRepository, TimescaleMarketDataRepository>();
        return services;
    }

    public static IServiceCollection AddTimescaleMarketDataCacheAside(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);

        services.TryAddSingleton(TimeProvider.System);
        services.AddSingleton<IMarketDataService, TimescaleCachedMarketDataService>();
        return services;
    }
}
