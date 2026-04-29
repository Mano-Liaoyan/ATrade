using Microsoft.Extensions.DependencyInjection;

namespace ATrade.MarketData;

public static class MarketDataModuleServiceCollectionExtensions
{
    public static IServiceCollection AddMarketDataModule(this IServiceCollection services)
    {
        services.AddSingleton<IndicatorService>();
        services.AddSingleton<TrendingService>();
        services.AddSingleton<IMarketDataService, MockMarketDataService>();
        services.AddSingleton<IMarketDataStreamingService, MockMarketDataStreamingService>();

        return services;
    }
}
