using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;

namespace ATrade.ServiceDefaults;

public sealed record LocalDevelopmentPortContract(
    string RepositoryRoot,
    string FrontendDirectory,
    string LoadedFromPath,
    int ApiHttpPort,
    int FrontendDirectHttpPort,
    int AppHostFrontendHttpPort,
    int AspireDashboardHttpPort);

public static class LocalDevelopmentPortContractLoader
{
    public const string ApiHttpPortVariableName = LocalRuntimeEnvironmentVariables.ApiHttpPort;
    public const string FrontendDirectHttpPortVariableName = LocalRuntimeEnvironmentVariables.FrontendDirectHttpPort;
    public const string AppHostFrontendHttpPortVariableName = LocalRuntimeEnvironmentVariables.AppHostFrontendHttpPort;
    public const string AspireDashboardHttpPortVariableName = LocalRuntimeEnvironmentVariables.AspireDashboardHttpPort;

    private static readonly Lazy<LocalDevelopmentPortContract> CurrentContract = new(() => FromRuntimeContract(LocalRuntimeContractLoader.Load()));

    public static LocalDevelopmentPortContract Load() => CurrentContract.Value;

    public static LocalDevelopmentPortContract FromRuntimeContract(LocalRuntimeContract runtimeContract)
    {
        ArgumentNullException.ThrowIfNull(runtimeContract);

        return new LocalDevelopmentPortContract(
            runtimeContract.RepositoryRoot,
            runtimeContract.FrontendDirectory,
            runtimeContract.LoadedFromPath,
            runtimeContract.Ports.ApiHttpPort,
            runtimeContract.Ports.FrontendDirectHttpPort,
            runtimeContract.Ports.AppHostFrontendHttpPort,
            runtimeContract.Ports.AspireDashboardHttpPort);
    }

    public static void ApplyApiHttpPortDefault(WebApplicationBuilder builder)
    {
        if (HasExplicitAspNetCoreUrlConfiguration(builder.Configuration))
        {
            return;
        }

        builder.WebHost.UseUrls($"http://127.0.0.1:{Load().ApiHttpPort}");
    }

    private static bool HasExplicitAspNetCoreUrlConfiguration(IConfiguration configuration)
    {
        return HasValue(configuration[WebHostDefaults.ServerUrlsKey]) ||
               HasValue(configuration["URLS"]) ||
               HasValue(configuration["HTTP_PORTS"]) ||
               HasValue(configuration["HTTPS_PORTS"]);
    }

    private static bool HasValue(string? value) => !string.IsNullOrWhiteSpace(value);
}
