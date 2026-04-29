using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace ATrade.Workspaces;

public static class WorkspaceModuleServiceCollectionExtensions
{
    public static IServiceCollection AddWorkspacesModule(this IServiceCollection services, IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(services);
        ArgumentNullException.ThrowIfNull(configuration);

        services.AddSingleton<IWorkspaceIdentityProvider, LocalWorkspaceIdentityProvider>();
        services.AddSingleton<IWorkspacePostgresDataSourceProvider>(_ => new WorkspacePostgresDataSourceProvider(configuration));
        services.AddSingleton<IWorkspaceWatchlistSchemaInitializer, PostgresWorkspaceWatchlistSchemaInitializer>();
        services.AddSingleton<IWorkspaceWatchlistRepository, PostgresWorkspaceWatchlistRepository>();

        return services;
    }
}
