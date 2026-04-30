using ATrade.Brokers;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;

namespace ATrade.Brokers.Ibkr;

public static class IbkrServiceCollectionExtensions
{
    public static IServiceCollection AddIbkrBrokerAdapter(this IServiceCollection services, IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(services);
        ArgumentNullException.ThrowIfNull(configuration);

        services.AddSingleton<IOptions<IbkrGatewayOptions>>(_ => Options.Create(IbkrGatewayOptions.FromConfiguration(configuration)));
        services.AddSingleton(static serviceProvider => serviceProvider.GetRequiredService<IOptions<IbkrGatewayOptions>>().Value);
        services.AddSingleton<IIbkrPaperTradingGuard, IbkrPaperTradingGuard>();
        services.AddSingleton(IbkrBrokerAdapterCapabilities.PaperSafeReadOnly);
        services.AddSingleton<IIbkrBrokerStatusService, IbkrBrokerStatusService>();
        services.AddSingleton<IBrokerProvider>(static serviceProvider => serviceProvider.GetRequiredService<IIbkrBrokerStatusService>());
        services.AddHttpClient<IIbkrGatewayClient, IbkrGatewayClient>((serviceProvider, client) =>
        {
            var options = serviceProvider.GetRequiredService<IbkrGatewayOptions>();
            IbkrGatewayTransport.ConfigureHttpClient(client, options);
        })
        .ConfigurePrimaryHttpMessageHandler(serviceProvider =>
        {
            var options = serviceProvider.GetRequiredService<IbkrGatewayOptions>();
            return IbkrGatewayTransport.CreateHttpMessageHandler(options);
        });

        return services;
    }
}
