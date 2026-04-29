using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace ATrade.Analysis;

public static class AnalysisModuleServiceCollectionExtensions
{
    public static IServiceCollection AddAnalysisModule(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);

        services.TryAddSingleton<NoConfiguredAnalysisEngine>();
        services.TryAddSingleton<IAnalysisEngineRegistry, AnalysisEngineRegistry>();

        return services;
    }
}
