using Microsoft.Extensions.DependencyInjection;

namespace ATrade.MarketData;

public static class MarketDataModuleServiceCollectionExtensions
{
    public static IServiceCollection AddMarketDataModule(this IServiceCollection services)
    {
        services.AddSingleton<IndicatorService>();
        services.AddSingleton<TrendingService>();
        services.AddSingleton<MockMarketDataService>();
        services.AddSingleton<IMarketDataProvider>(static serviceProvider => serviceProvider.GetRequiredService<MockMarketDataService>());
        services.AddSingleton<IMarketDataService, MarketDataService>();
        services.AddSingleton<MockMarketDataStreamingService>();
        services.AddSingleton<IMarketDataStreamingProvider>(static serviceProvider => serviceProvider.GetRequiredService<MockMarketDataStreamingService>());
        services.AddSingleton<IMarketDataStreamingService, MarketDataStreamingService>();

        return services;
    }
}
