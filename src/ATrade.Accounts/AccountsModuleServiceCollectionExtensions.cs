using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace ATrade.Accounts;

public static class AccountsModuleServiceCollectionExtensions
{
    public static IServiceCollection AddAccountsModule(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);

        services.AddSingleton<IAccountOverviewProvider, AccountOverviewService>();
        services.AddSingleton<IPaperCapitalIdentityProvider, LocalPaperCapitalIdentityProvider>();
        services.AddSingleton<IIbkrPaperCapitalProvider, UnavailableIbkrPaperCapitalProvider>();

        return services;
    }

    public static IServiceCollection AddAccountsModule(this IServiceCollection services, IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(services);
        ArgumentNullException.ThrowIfNull(configuration);

        services.AddAccountsModule();
        services.AddSingleton<IAccountsPostgresDataSourceProvider>(_ => new AccountsPostgresDataSourceProvider(configuration));
        services.AddSingleton<ILocalPaperCapitalSchemaInitializer, PostgresLocalPaperCapitalSchemaInitializer>();
        services.AddSingleton<ILocalPaperCapitalRepository, PostgresLocalPaperCapitalRepository>();
        services.AddSingleton<IPaperCapitalService, PaperCapitalService>();

        return services;
    }
}
