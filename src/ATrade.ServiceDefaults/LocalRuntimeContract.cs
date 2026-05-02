using System.Collections;

namespace ATrade.ServiceDefaults;

public enum LocalRuntimeContractValueKind
{
    NonSecret,
    Secret,
}

public sealed record LocalRuntimeContractValue(
    string Name,
    string Value,
    LocalRuntimeContractValueKind Kind)
{
    public bool IsSecret => Kind == LocalRuntimeContractValueKind.Secret;
}

public sealed record LocalRuntimePortSettings(
    int ApiHttpPort,
    int FrontendDirectHttpPort,
    int AppHostFrontendHttpPort,
    int AspireDashboardHttpPort);

public sealed record LocalRuntimeStorageSettings(
    string PostgresDataVolumeName,
    string PostgresPassword,
    string TimescaleDataVolumeName,
    string TimescalePassword);

public sealed record LocalRuntimePaperTradingSettings(
    string BrokerIntegrationEnabled,
    string BrokerAccountMode,
    string GatewayUrl,
    string GatewayPort,
    string GatewayImage,
    string GatewayTimeoutSeconds,
    string IbkrUsername,
    string IbkrPassword,
    string PaperAccountId);

public sealed record LocalRuntimeFrontendSettings(
    string FrontendApiBaseUrl,
    string NextPublicApiBaseUrl);

public sealed record LocalRuntimeMarketDataSettings(
    string CacheFreshnessMinutes);

public sealed record LocalRuntimeLeanSettings(
    string AnalysisEngine,
    string RuntimeMode,
    string CliCommand,
    string DockerCommand,
    string DockerImage,
    string WorkspaceRoot,
    string TimeoutSeconds,
    string KeepWorkspace,
    string ManagedContainerName,
    string ContainerWorkspaceRoot);

public sealed record LocalRuntimeContract(
    string RepositoryRoot,
    string FrontendDirectory,
    string LoadedFromPath,
    LocalRuntimePortSettings Ports,
    LocalRuntimeStorageSettings Storage,
    LocalRuntimePaperTradingSettings PaperTrading,
    LocalRuntimeFrontendSettings Frontend,
    LocalRuntimeMarketDataSettings MarketData,
    LocalRuntimeLeanSettings Lean,
    IReadOnlyDictionary<string, LocalRuntimeContractValue> Values)
{
    public string GetValue(string variableName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(variableName);

        return Values.TryGetValue(variableName, out var value)
            ? value.Value
            : throw new KeyNotFoundException($"The local runtime contract does not define '{variableName}'.");
    }

    public bool IsSecret(string variableName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(variableName);

        return Values.TryGetValue(variableName, out var value) && value.IsSecret;
    }
}

public sealed record LocalRuntimeContractLoadOptions(
    string? RepositoryRoot = null,
    string? ContractPath = null,
    IReadOnlyDictionary<string, string?>? EnvironmentVariables = null);

public static class LocalRuntimeEnvironmentVariables
{
    public const string ApiHttpPort = "ATRADE_API_HTTP_PORT";
    public const string FrontendDirectHttpPort = "ATRADE_FRONTEND_DIRECT_HTTP_PORT";
    public const string AppHostFrontendHttpPort = "ATRADE_APPHOST_FRONTEND_HTTP_PORT";
    public const string AspireDashboardHttpPort = "ATRADE_ASPIRE_DASHBOARD_HTTP_PORT";
    public const string PostgresDataVolume = "ATRADE_POSTGRES_DATA_VOLUME";
    public const string PostgresPassword = "ATRADE_POSTGRES_PASSWORD";
    public const string TimescaleDataVolume = "ATRADE_TIMESCALEDB_DATA_VOLUME";
    public const string TimescalePassword = "ATRADE_TIMESCALEDB_PASSWORD";
    public const string BrokerIntegrationEnabled = "ATRADE_BROKER_INTEGRATION_ENABLED";
    public const string BrokerAccountMode = "ATRADE_BROKER_ACCOUNT_MODE";
    public const string IbkrGatewayUrl = "ATRADE_IBKR_GATEWAY_URL";
    public const string IbkrGatewayPort = "ATRADE_IBKR_GATEWAY_PORT";
    public const string IbkrGatewayImage = "ATRADE_IBKR_GATEWAY_IMAGE";
    public const string IbkrGatewayTimeoutSeconds = "ATRADE_IBKR_GATEWAY_TIMEOUT_SECONDS";
    public const string IbkrUsername = "ATRADE_IBKR_USERNAME";
    public const string IbkrPassword = "ATRADE_IBKR_PASSWORD";
    public const string IbkrPaperAccountId = "ATRADE_IBKR_PAPER_ACCOUNT_ID";
    public const string FrontendApiBaseUrl = "ATRADE_FRONTEND_API_BASE_URL";
    public const string NextPublicApiBaseUrl = "NEXT_PUBLIC_ATRADE_API_BASE_URL";
    public const string MarketDataCacheFreshnessMinutes = "ATRADE_MARKET_DATA_CACHE_FRESHNESS_MINUTES";
    public const string AnalysisEngine = "ATRADE_ANALYSIS_ENGINE";
    public const string LeanRuntimeMode = "ATRADE_LEAN_RUNTIME_MODE";
    public const string LeanCliCommand = "ATRADE_LEAN_CLI_COMMAND";
    public const string LeanDockerCommand = "ATRADE_LEAN_DOCKER_COMMAND";
    public const string LeanDockerImage = "ATRADE_LEAN_DOCKER_IMAGE";
    public const string LeanWorkspaceRoot = "ATRADE_LEAN_WORKSPACE_ROOT";
    public const string LeanTimeoutSeconds = "ATRADE_LEAN_TIMEOUT_SECONDS";
    public const string LeanKeepWorkspace = "ATRADE_LEAN_KEEP_WORKSPACE";
    public const string LeanManagedContainerName = "ATRADE_LEAN_MANAGED_CONTAINER_NAME";
    public const string LeanContainerWorkspaceRoot = "ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT";
}

public static class LocalRuntimeContractDefaults
{
    public const int ApiHttpPort = 5181;
    public const int FrontendDirectHttpPort = 3111;
    public const int AppHostFrontendHttpPort = 3000;
    public const int AspireDashboardHttpPort = 0;
    public const string PostgresDataVolume = "atrade-postgres-data";
    public const string PostgresPassword = "ATRADE_POSTGRES_PASSWORD";
    public const string TimescaleDataVolume = "atrade-timescaledb-data";
    public const string TimescalePassword = "ATRADE_TIMESCALEDB_PASSWORD";
    public const string BrokerIntegrationEnabled = "false";
    public const string BrokerAccountMode = "Paper";
    public const string IbkrGatewayUrl = "https://127.0.0.1:5000";
    public const string IbkrGatewayPort = "5000";
    public const string IbkrGatewayImage = "voyz/ibeam:latest";
    public const string IbkrGatewayTimeoutSeconds = "15";
    public const string IbkrUsername = "IBKR_USERNAME";
    public const string IbkrPassword = "IBKR_PASSWORD";
    public const string IbkrPaperAccountId = "IBKR_ACCOUNT_ID";
    public const string FrontendApiBaseUrl = "http://127.0.0.1:5181";
    public const string NextPublicApiBaseUrl = "http://127.0.0.1:5181";
    public const string MarketDataCacheFreshnessMinutes = "30";
    public const string AnalysisEngine = "none";
    public const string LeanRuntimeMode = "cli";
    public const string LeanCliCommand = "lean";
    public const string LeanDockerCommand = "docker";
    public const string LeanDockerImage = "quantconnect/lean:latest";
    public const string LeanWorkspaceRoot = "artifacts/lean-workspaces";
    public const string LeanTimeoutSeconds = "45";
    public const string LeanKeepWorkspace = "false";
    public const string LeanManagedContainerName = "atrade-lean-engine";
    public const string LeanContainerWorkspaceRoot = "/workspace";
}

public static class LocalRuntimeContractLoader
{
    private static readonly Lazy<LocalRuntimeContract> CurrentContract = new(() => Load(new LocalRuntimeContractLoadOptions()));

    private static readonly string[] KnownVariableNames =
    [
        LocalRuntimeEnvironmentVariables.ApiHttpPort,
        LocalRuntimeEnvironmentVariables.FrontendDirectHttpPort,
        LocalRuntimeEnvironmentVariables.AppHostFrontendHttpPort,
        LocalRuntimeEnvironmentVariables.AspireDashboardHttpPort,
        LocalRuntimeEnvironmentVariables.PostgresDataVolume,
        LocalRuntimeEnvironmentVariables.PostgresPassword,
        LocalRuntimeEnvironmentVariables.TimescaleDataVolume,
        LocalRuntimeEnvironmentVariables.TimescalePassword,
        LocalRuntimeEnvironmentVariables.BrokerIntegrationEnabled,
        LocalRuntimeEnvironmentVariables.BrokerAccountMode,
        LocalRuntimeEnvironmentVariables.IbkrGatewayUrl,
        LocalRuntimeEnvironmentVariables.IbkrGatewayPort,
        LocalRuntimeEnvironmentVariables.IbkrGatewayImage,
        LocalRuntimeEnvironmentVariables.IbkrGatewayTimeoutSeconds,
        LocalRuntimeEnvironmentVariables.IbkrUsername,
        LocalRuntimeEnvironmentVariables.IbkrPassword,
        LocalRuntimeEnvironmentVariables.IbkrPaperAccountId,
        LocalRuntimeEnvironmentVariables.FrontendApiBaseUrl,
        LocalRuntimeEnvironmentVariables.NextPublicApiBaseUrl,
        LocalRuntimeEnvironmentVariables.MarketDataCacheFreshnessMinutes,
        LocalRuntimeEnvironmentVariables.AnalysisEngine,
        LocalRuntimeEnvironmentVariables.LeanRuntimeMode,
        LocalRuntimeEnvironmentVariables.LeanCliCommand,
        LocalRuntimeEnvironmentVariables.LeanDockerCommand,
        LocalRuntimeEnvironmentVariables.LeanDockerImage,
        LocalRuntimeEnvironmentVariables.LeanWorkspaceRoot,
        LocalRuntimeEnvironmentVariables.LeanTimeoutSeconds,
        LocalRuntimeEnvironmentVariables.LeanKeepWorkspace,
        LocalRuntimeEnvironmentVariables.LeanManagedContainerName,
        LocalRuntimeEnvironmentVariables.LeanContainerWorkspaceRoot,
    ];

    private static readonly HashSet<string> SecretVariableNames = new(StringComparer.OrdinalIgnoreCase)
    {
        LocalRuntimeEnvironmentVariables.PostgresPassword,
        LocalRuntimeEnvironmentVariables.TimescalePassword,
        LocalRuntimeEnvironmentVariables.IbkrUsername,
        LocalRuntimeEnvironmentVariables.IbkrPassword,
        LocalRuntimeEnvironmentVariables.IbkrPaperAccountId,
    };

    public static LocalRuntimeContract Load() => CurrentContract.Value;

    public static LocalRuntimeContract Load(LocalRuntimeContractLoadOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);

        var repositoryRoot = ResolveRepositoryRoot(options.RepositoryRoot, options.ContractPath);
        var loadedFromPath = ResolveLoadedFromPath(repositoryRoot, options.ContractPath);
        var configuredValues = LoadFileValues(repositoryRoot, loadedFromPath);
        Overlay(configuredValues, NormalizeEnvironmentValues(options.EnvironmentVariables ?? CaptureProcessEnvironment()));

        return CreateContract(repositoryRoot, loadedFromPath, configuredValues);
    }

    private static LocalRuntimeContract CreateContract(
        string repositoryRoot,
        string loadedFromPath,
        IReadOnlyDictionary<string, string> configuredValues)
    {
        var resolvedValues = new Dictionary<string, LocalRuntimeContractValue>(StringComparer.OrdinalIgnoreCase);
        var apiHttpPort = ResolvePort(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.ApiHttpPort, LocalRuntimeContractDefaults.ApiHttpPort, allowZero: false);
        var frontendDirectHttpPort = ResolvePort(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.FrontendDirectHttpPort, LocalRuntimeContractDefaults.FrontendDirectHttpPort, allowZero: false);
        var appHostFrontendHttpPort = ResolvePort(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.AppHostFrontendHttpPort, LocalRuntimeContractDefaults.AppHostFrontendHttpPort, allowZero: false);
        var aspireDashboardHttpPort = ResolvePort(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.AspireDashboardHttpPort, LocalRuntimeContractDefaults.AspireDashboardHttpPort, allowZero: true);
        var postgresDataVolume = ResolveVolumeName(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.PostgresDataVolume, LocalRuntimeContractDefaults.PostgresDataVolume);
        var postgresPassword = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.PostgresPassword, LocalRuntimeContractDefaults.PostgresPassword);
        var timescaleDataVolume = ResolveVolumeName(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.TimescaleDataVolume, LocalRuntimeContractDefaults.TimescaleDataVolume);
        var timescalePassword = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.TimescalePassword, LocalRuntimeContractDefaults.TimescalePassword);
        var brokerIntegrationEnabled = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.BrokerIntegrationEnabled, LocalRuntimeContractDefaults.BrokerIntegrationEnabled);
        var brokerAccountMode = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.BrokerAccountMode, LocalRuntimeContractDefaults.BrokerAccountMode);
        var gatewayUrl = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.IbkrGatewayUrl, LocalRuntimeContractDefaults.IbkrGatewayUrl);
        var gatewayPort = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.IbkrGatewayPort, LocalRuntimeContractDefaults.IbkrGatewayPort);
        var gatewayImage = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.IbkrGatewayImage, LocalRuntimeContractDefaults.IbkrGatewayImage);
        var gatewayTimeoutSeconds = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.IbkrGatewayTimeoutSeconds, LocalRuntimeContractDefaults.IbkrGatewayTimeoutSeconds);
        var ibkrUsername = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.IbkrUsername, LocalRuntimeContractDefaults.IbkrUsername);
        var ibkrPassword = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.IbkrPassword, LocalRuntimeContractDefaults.IbkrPassword);
        var paperAccountId = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.IbkrPaperAccountId, LocalRuntimeContractDefaults.IbkrPaperAccountId);
        var frontendApiBaseUrl = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.FrontendApiBaseUrl, $"http://127.0.0.1:{apiHttpPort}");
        var nextPublicApiBaseUrl = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.NextPublicApiBaseUrl, frontendApiBaseUrl);
        var marketDataCacheFreshnessMinutes = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.MarketDataCacheFreshnessMinutes, LocalRuntimeContractDefaults.MarketDataCacheFreshnessMinutes);
        var analysisEngine = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.AnalysisEngine, LocalRuntimeContractDefaults.AnalysisEngine);
        var leanRuntimeMode = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.LeanRuntimeMode, LocalRuntimeContractDefaults.LeanRuntimeMode);
        var leanCliCommand = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.LeanCliCommand, LocalRuntimeContractDefaults.LeanCliCommand);
        var leanDockerCommand = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.LeanDockerCommand, LocalRuntimeContractDefaults.LeanDockerCommand);
        var leanDockerImage = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.LeanDockerImage, LocalRuntimeContractDefaults.LeanDockerImage);
        var leanWorkspaceRoot = ResolveWorkspaceRoot(
            ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.LeanWorkspaceRoot, LocalRuntimeContractDefaults.LeanWorkspaceRoot),
            repositoryRoot);
        SetResolvedValue(resolvedValues, LocalRuntimeEnvironmentVariables.LeanWorkspaceRoot, leanWorkspaceRoot);
        var leanTimeoutSeconds = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.LeanTimeoutSeconds, LocalRuntimeContractDefaults.LeanTimeoutSeconds);
        var leanKeepWorkspace = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.LeanKeepWorkspace, LocalRuntimeContractDefaults.LeanKeepWorkspace);
        var leanManagedContainerName = ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.LeanManagedContainerName, LocalRuntimeContractDefaults.LeanManagedContainerName);
        var leanContainerWorkspaceRoot = NormalizeContainerWorkspaceRoot(
            ResolveString(configuredValues, resolvedValues, LocalRuntimeEnvironmentVariables.LeanContainerWorkspaceRoot, LocalRuntimeContractDefaults.LeanContainerWorkspaceRoot));
        SetResolvedValue(resolvedValues, LocalRuntimeEnvironmentVariables.LeanContainerWorkspaceRoot, leanContainerWorkspaceRoot);

        return new LocalRuntimeContract(
            repositoryRoot,
            Path.Combine(repositoryRoot, "frontend"),
            loadedFromPath,
            new LocalRuntimePortSettings(apiHttpPort, frontendDirectHttpPort, appHostFrontendHttpPort, aspireDashboardHttpPort),
            new LocalRuntimeStorageSettings(postgresDataVolume, postgresPassword, timescaleDataVolume, timescalePassword),
            new LocalRuntimePaperTradingSettings(
                brokerIntegrationEnabled,
                brokerAccountMode,
                gatewayUrl,
                gatewayPort,
                gatewayImage,
                gatewayTimeoutSeconds,
                ibkrUsername,
                ibkrPassword,
                paperAccountId),
            new LocalRuntimeFrontendSettings(frontendApiBaseUrl, nextPublicApiBaseUrl),
            new LocalRuntimeMarketDataSettings(marketDataCacheFreshnessMinutes),
            new LocalRuntimeLeanSettings(
                analysisEngine,
                leanRuntimeMode,
                leanCliCommand,
                leanDockerCommand,
                leanDockerImage,
                leanWorkspaceRoot,
                leanTimeoutSeconds,
                leanKeepWorkspace,
                leanManagedContainerName,
                leanContainerWorkspaceRoot),
            resolvedValues);
    }

    private static Dictionary<string, string> LoadFileValues(string repositoryRoot, string loadedFromPath)
    {
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var templatePath = Path.Combine(repositoryRoot, ".env.template");

        if (File.Exists(templatePath))
        {
            Overlay(values, ParseEnvironmentFile(templatePath));
        }

        if (File.Exists(loadedFromPath) && !PathsEqual(templatePath, loadedFromPath))
        {
            Overlay(values, ParseEnvironmentFile(loadedFromPath));
        }

        return values;
    }

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
            if (!string.IsNullOrWhiteSpace(key))
            {
                values[key] = value;
            }
        }

        return values;
    }

    private static IReadOnlyDictionary<string, string?> CaptureProcessEnvironment()
    {
        var environment = new Dictionary<string, string?>(StringComparer.OrdinalIgnoreCase);
        foreach (DictionaryEntry entry in Environment.GetEnvironmentVariables())
        {
            if (entry.Key is string key)
            {
                environment[key] = entry.Value?.ToString();
            }
        }

        return environment;
    }

    private static Dictionary<string, string> NormalizeEnvironmentValues(IReadOnlyDictionary<string, string?> environmentVariables)
    {
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var variableName in KnownVariableNames)
        {
            if (environmentVariables.TryGetValue(variableName, out var value) && !string.IsNullOrWhiteSpace(value))
            {
                values[variableName] = value.Trim();
            }
        }

        return values;
    }

    private static void Overlay(IDictionary<string, string> destination, IReadOnlyDictionary<string, string> source)
    {
        foreach (var pair in source)
        {
            destination[pair.Key] = pair.Value;
        }
    }

    private static int ResolvePort(
        IReadOnlyDictionary<string, string> configuredValues,
        IDictionary<string, LocalRuntimeContractValue> resolvedValues,
        string variableName,
        int defaultValue,
        bool allowZero)
    {
        var value = ResolveRawString(configuredValues, variableName, defaultValue.ToString());
        var port = ParsePort(variableName, value, allowZero);
        SetResolvedValue(resolvedValues, variableName, port.ToString());
        return port;
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

    private static string ResolveVolumeName(
        IReadOnlyDictionary<string, string> configuredValues,
        IDictionary<string, LocalRuntimeContractValue> resolvedValues,
        string variableName,
        string defaultValue)
    {
        var value = ResolveRawString(configuredValues, variableName, defaultValue);
        var normalized = NormalizeVolumeName(value, variableName, defaultValue);
        SetResolvedValue(resolvedValues, variableName, normalized);
        return normalized;
    }

    private static string NormalizeVolumeName(string value, string variableName, string defaultValue)
    {
        var trimmed = value.Trim();
        if (string.IsNullOrWhiteSpace(trimmed))
        {
            return defaultValue;
        }

        if (trimmed.Length > 128 || !char.IsLetterOrDigit(trimmed[0]) || trimmed.Any(character => !char.IsLetterOrDigit(character) && character is not '.' and not '_' and not '-'))
        {
            throw new InvalidOperationException(
                $"{variableName} must be a Docker-compatible named volume using letters, digits, '.', '_', or '-', and must start with a letter or digit; value was '{value}'.");
        }

        return trimmed;
    }

    private static string ResolveString(
        IReadOnlyDictionary<string, string> configuredValues,
        IDictionary<string, LocalRuntimeContractValue> resolvedValues,
        string variableName,
        string defaultValue)
    {
        var value = ResolveRawString(configuredValues, variableName, defaultValue);
        SetResolvedValue(resolvedValues, variableName, value);
        return value;
    }

    private static string ResolveRawString(IReadOnlyDictionary<string, string> configuredValues, string variableName, string defaultValue)
    {
        return configuredValues.TryGetValue(variableName, out var configuredValue) && !string.IsNullOrWhiteSpace(configuredValue)
            ? configuredValue.Trim()
            : defaultValue;
    }

    private static string ResolveWorkspaceRoot(string configuredWorkspaceRoot, string repositoryRoot)
    {
        var rawWorkspaceRoot = string.IsNullOrWhiteSpace(configuredWorkspaceRoot)
            ? LocalRuntimeContractDefaults.LeanWorkspaceRoot
            : configuredWorkspaceRoot.Trim();

        return Path.IsPathRooted(rawWorkspaceRoot)
            ? Path.GetFullPath(rawWorkspaceRoot)
            : Path.GetFullPath(Path.Combine(repositoryRoot, rawWorkspaceRoot));
    }

    private static string NormalizeContainerWorkspaceRoot(string value)
    {
        var trimmed = value.Trim().Replace('\\', '/').TrimEnd('/');
        if (string.IsNullOrWhiteSpace(trimmed))
        {
            return LocalRuntimeContractDefaults.LeanContainerWorkspaceRoot;
        }

        return trimmed.StartsWith("/", StringComparison.Ordinal)
            ? trimmed
            : $"/{trimmed}";
    }

    private static void SetResolvedValue(
        IDictionary<string, LocalRuntimeContractValue> resolvedValues,
        string variableName,
        string value)
    {
        var kind = SecretVariableNames.Contains(variableName)
            ? LocalRuntimeContractValueKind.Secret
            : LocalRuntimeContractValueKind.NonSecret;
        resolvedValues[variableName] = new LocalRuntimeContractValue(variableName, value, kind);
    }

    private static string ResolveRepositoryRoot(string? configuredRepositoryRoot, string? contractPath)
    {
        if (!string.IsNullOrWhiteSpace(configuredRepositoryRoot))
        {
            return Path.GetFullPath(configuredRepositoryRoot);
        }

        if (!string.IsNullOrWhiteSpace(contractPath))
        {
            return Path.GetDirectoryName(Path.GetFullPath(contractPath))
                ?? throw new InvalidOperationException($"Failed to resolve the local runtime contract directory for '{contractPath}'.");
        }

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

    private static string ResolveLoadedFromPath(string repositoryRoot, string? contractPath)
    {
        if (!string.IsNullOrWhiteSpace(contractPath))
        {
            return Path.GetFullPath(contractPath);
        }

        var preferredPath = Path.Combine(repositoryRoot, ".env");
        if (File.Exists(preferredPath))
        {
            return preferredPath;
        }

        return Path.Combine(repositoryRoot, ".env.template");
    }

    private static bool PathsEqual(string left, string right) =>
        Path.GetFullPath(left).Equals(Path.GetFullPath(right), StringComparison.OrdinalIgnoreCase);
}
