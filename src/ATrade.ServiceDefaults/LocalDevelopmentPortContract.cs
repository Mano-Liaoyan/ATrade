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
    public const string ApiHttpPortVariableName = "ATRADE_API_HTTP_PORT";
    public const string FrontendDirectHttpPortVariableName = "ATRADE_FRONTEND_DIRECT_HTTP_PORT";
    public const string AppHostFrontendHttpPortVariableName = "ATRADE_APPHOST_FRONTEND_HTTP_PORT";
    public const string AspireDashboardHttpPortVariableName = "ATRADE_ASPIRE_DASHBOARD_HTTP_PORT";

    private static readonly Lazy<LocalDevelopmentPortContract> CurrentContract = new(CreateCurrentContract);

    public static LocalDevelopmentPortContract Load() => CurrentContract.Value;

    public static void ApplyApiHttpPortDefault(WebApplicationBuilder builder)
    {
        if (HasExplicitAspNetCoreUrlConfiguration(builder.Configuration))
        {
            return;
        }

        builder.WebHost.UseUrls($"http://127.0.0.1:{Load().ApiHttpPort}");
    }

    private static LocalDevelopmentPortContract CreateCurrentContract()
    {
        var repositoryRoot = ResolveRepositoryRoot();
        var loadedFromPath = ResolveContractPath(repositoryRoot);
        var contractValues = File.Exists(loadedFromPath)
            ? ParseEnvironmentFile(loadedFromPath)
            : new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        return new LocalDevelopmentPortContract(
            repositoryRoot,
            Path.Combine(repositoryRoot, "frontend"),
            loadedFromPath,
            GetRequiredPort(contractValues, ApiHttpPortVariableName, loadedFromPath),
            GetRequiredPort(contractValues, FrontendDirectHttpPortVariableName, loadedFromPath),
            GetRequiredPort(contractValues, AppHostFrontendHttpPortVariableName, loadedFromPath),
            GetOptionalPort(contractValues, AspireDashboardHttpPortVariableName, defaultValue: 0));
    }

    private static string ResolveRepositoryRoot()
    {
        foreach (var startPath in new[] { Directory.GetCurrentDirectory(), AppContext.BaseDirectory })
        {
            var candidate = FindRepositoryRoot(startPath);
            if (candidate is not null)
            {
                return candidate;
            }
        }

        throw new InvalidOperationException("Failed to locate the ATrade repository root from the current execution context.");
    }

    private static string? FindRepositoryRoot(string startPath)
    {
        var current = new DirectoryInfo(Path.GetFullPath(startPath));
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "ATrade.slnx")) ||
                File.Exists(Path.Combine(current.FullName, "ATrade.sln")) ||
                File.Exists(Path.Combine(current.FullName, ".env.template")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        return null;
    }

    private static string ResolveContractPath(string repositoryRoot)
    {
        var preferredPath = Path.Combine(repositoryRoot, ".env");
        if (File.Exists(preferredPath))
        {
            return preferredPath;
        }

        return Path.Combine(repositoryRoot, ".env.template");
    }

    private static bool HasExplicitAspNetCoreUrlConfiguration(IConfiguration configuration)
    {
        return HasValue(configuration[WebHostDefaults.ServerUrlsKey]) ||
               HasValue(configuration["URLS"]) ||
               HasValue(configuration["HTTP_PORTS"]) ||
               HasValue(configuration["HTTPS_PORTS"]);
    }

    private static bool HasValue(string? value) => !string.IsNullOrWhiteSpace(value);

    private static Dictionary<string, string> ParseEnvironmentFile(string path)
    {
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (var rawLine in File.ReadAllLines(path))
        {
            var line = rawLine.Trim();
            if (string.IsNullOrWhiteSpace(line) || line.StartsWith('#'))
            {
                continue;
            }

            var separatorIndex = line.IndexOf('=');
            if (separatorIndex <= 0)
            {
                continue;
            }

            var key = line[..separatorIndex].Trim();
            var value = line[(separatorIndex + 1)..].Trim().Trim('"', '\'');
            values[key] = value;
        }

        return values;
    }

    private static int GetRequiredPort(IReadOnlyDictionary<string, string> contractValues, string variableName, string loadedFromPath)
    {
        var configuredValue = GetConfiguredValue(contractValues, variableName);

        if (string.IsNullOrWhiteSpace(configuredValue))
        {
            throw new InvalidOperationException($"{variableName} must be provided either through the environment or the local port contract at '{loadedFromPath}'.");
        }

        return ParsePort(variableName, configuredValue, allowZero: false);
    }

    private static int GetOptionalPort(
        IReadOnlyDictionary<string, string> contractValues,
        string variableName,
        int defaultValue)
    {
        var configuredValue = GetConfiguredValue(contractValues, variableName);
        if (string.IsNullOrWhiteSpace(configuredValue))
        {
            return defaultValue;
        }

        return ParsePort(variableName, configuredValue, allowZero: true);
    }

    private static string? GetConfiguredValue(IReadOnlyDictionary<string, string> contractValues, string variableName)
    {
        var configuredValue = Environment.GetEnvironmentVariable(variableName);
        if (string.IsNullOrWhiteSpace(configuredValue) && contractValues.TryGetValue(variableName, out var fileValue))
        {
            configuredValue = fileValue;
        }

        return configuredValue;
    }

    private static int ParsePort(string variableName, string configuredValue, bool allowZero)
    {
        if (!int.TryParse(configuredValue, out var port) || port > 65535 || port < (allowZero ? 0 : 1))
        {
            var validRange = allowZero ? "0..65535" : "1..65535";
            throw new InvalidOperationException($"{variableName} must be a valid TCP port in the range {validRange}, but was '{configuredValue}'.");
        }

        return port;
    }
}
