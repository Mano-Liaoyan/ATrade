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
    int AppHostFrontendHttpPort);

public static class LocalDevelopmentPortContractLoader
{
    public const string ApiHttpPortVariableName = "ATRADE_API_HTTP_PORT";
    public const string FrontendDirectHttpPortVariableName = "ATRADE_FRONTEND_DIRECT_HTTP_PORT";
    public const string AppHostFrontendHttpPortVariableName = "ATRADE_APPHOST_FRONTEND_HTTP_PORT";

    private const int DefaultApiHttpPort = 5181;
    private const int DefaultFrontendDirectHttpPort = 3111;
    private const int DefaultAppHostFrontendHttpPort = 3000;

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
            GetPort(contractValues, ApiHttpPortVariableName, DefaultApiHttpPort),
            GetPort(contractValues, FrontendDirectHttpPortVariableName, DefaultFrontendDirectHttpPort),
            GetPort(contractValues, AppHostFrontendHttpPortVariableName, DefaultAppHostFrontendHttpPort));
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
            if (File.Exists(Path.Combine(current.FullName, "ATrade.sln")) ||
                File.Exists(Path.Combine(current.FullName, ".env.example")))
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

        return Path.Combine(repositoryRoot, ".env.example");
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

    private static int GetPort(IReadOnlyDictionary<string, string> contractValues, string variableName, int fallback)
    {
        var configuredValue = Environment.GetEnvironmentVariable(variableName);
        if (string.IsNullOrWhiteSpace(configuredValue) && contractValues.TryGetValue(variableName, out var fileValue))
        {
            configuredValue = fileValue;
        }

        if (string.IsNullOrWhiteSpace(configuredValue))
        {
            return fallback;
        }

        if (!int.TryParse(configuredValue, out var port) || port is <= 0 or > 65535)
        {
            throw new InvalidOperationException($"{variableName} must be a valid TCP port, but was '{configuredValue}'.");
        }

        return port;
    }
}
