using Microsoft.Extensions.DependencyInjection;

namespace ATrade.Orders;

public static class OrdersModuleServiceCollectionExtensions
{
    public static IServiceCollection AddOrdersModule(this IServiceCollection services)
    {
        services.AddSingleton<IOrderSimulationService, OrderSimulationService>();

        return services;
    }
}
