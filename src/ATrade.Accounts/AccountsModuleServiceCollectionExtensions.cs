using Microsoft.Extensions.DependencyInjection;

namespace ATrade.Accounts;

public static class AccountsModuleServiceCollectionExtensions
{
    public static IServiceCollection AddAccountsModule(this IServiceCollection services)
    {
        services.AddSingleton<IAccountOverviewProvider, AccountOverviewService>();

        return services;
    }
}
