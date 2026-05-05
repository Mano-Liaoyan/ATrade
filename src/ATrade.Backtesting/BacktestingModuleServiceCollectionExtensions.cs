using ATrade.Accounts;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace ATrade.Backtesting;

public static class BacktestingModuleServiceCollectionExtensions
{
    public static IServiceCollection AddBacktestingModule(this IServiceCollection services, IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(services);
        ArgumentNullException.ThrowIfNull(configuration);

        services.AddSingleton<IBacktestingPostgresDataSourceProvider>(_ => new BacktestingPostgresDataSourceProvider(configuration));
        services.AddSingleton<IBacktestRunSchemaInitializer, PostgresBacktestRunSchemaInitializer>();
        services.AddSingleton<IBacktestRunRepository>(serviceProvider => new PostgresBacktestRunRepository(
            serviceProvider.GetRequiredService<IBacktestingPostgresDataSourceProvider>()));
        services.AddSingleton<IBacktestRunFactory>(serviceProvider => new BacktestRunFactory(
            serviceProvider.GetRequiredService<IPaperCapitalService>(),
            serviceProvider.GetRequiredService<IPaperCapitalIdentityProvider>()));

        return services;
    }
}
