using Microsoft.Extensions.DependencyInjection;

namespace ATrade.MarketData;

public static class MarketDataModuleServiceCollectionExtensions
{
    public static IServiceCollection AddMarketDataModule(this IServiceCollection services)
    {
        services.AddSingleton<IndicatorService>();
        services.AddSingleton<TrendingService>();
        services.AddSingleton<MarketDataService>();
        services.AddSingleton<IMarketDataService>(static serviceProvider => serviceProvider.GetRequiredService<MarketDataService>());
        services.AddSingleton<IMarketDataStreamingService, MarketDataStreamingService>();

        return services;
    }
}
