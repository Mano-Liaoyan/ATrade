using ATrade.Analysis;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;

namespace ATrade.Analysis.Lean;

public static class LeanModuleServiceCollectionExtensions
{
    public static IServiceCollection AddLeanAnalysisEngine(this IServiceCollection services, IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(services);
        ArgumentNullException.ThrowIfNull(configuration);

        var options = LeanAnalysisOptions.FromConfiguration(configuration);
        services.AddSingleton<IOptions<LeanAnalysisOptions>>(_ => Options.Create(options));
        services.AddSingleton(static serviceProvider => serviceProvider.GetRequiredService<IOptions<LeanAnalysisOptions>>().Value);

        if (!options.IsLeanSelected)
        {
            return services;
        }

        services.TryAddSingleton<ILeanRuntimeExecutor, LeanRuntimeExecutor>();
        services.TryAddSingleton<ILeanAnalysisWorkspaceFactory, LeanAnalysisWorkspaceFactory>();
        services.AddSingleton<IAnalysisEngine, LeanAnalysisEngine>();

        return services;
    }
}
