namespace ATrade.AppHost;

public sealed record LeanAnalysisRuntimeContract(
    string AnalysisEngine,
    string RuntimeMode,
    string CliCommand,
    string DockerCommand,
    string DockerImage,
    string WorkspaceRoot,
    string TimeoutSeconds,
    string KeepWorkspace,
    string ManagedContainerName,
    string ContainerWorkspaceRoot)
{
    public const string AnalysisEngineVariableName = "ATRADE_ANALYSIS_ENGINE";
    public const string RuntimeModeVariableName = "ATRADE_LEAN_RUNTIME_MODE";
    public const string CliCommandVariableName = "ATRADE_LEAN_CLI_COMMAND";
    public const string DockerCommandVariableName = "ATRADE_LEAN_DOCKER_COMMAND";
    public const string DockerImageVariableName = "ATRADE_LEAN_DOCKER_IMAGE";
    public const string WorkspaceRootVariableName = "ATRADE_LEAN_WORKSPACE_ROOT";
    public const string TimeoutSecondsVariableName = "ATRADE_LEAN_TIMEOUT_SECONDS";
    public const string KeepWorkspaceVariableName = "ATRADE_LEAN_KEEP_WORKSPACE";
    public const string ManagedContainerNameVariableName = "ATRADE_LEAN_MANAGED_CONTAINER_NAME";
    public const string ContainerWorkspaceRootVariableName = "ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT";

    public const string EngineNone = "none";
    public const string EngineLean = "Lean";
    public const string RuntimeModeCli = "cli";
    public const string RuntimeModeDocker = "docker";
    public const string DefaultCliCommand = "lean";
    public const string DefaultDockerCommand = "docker";
    public const string DefaultDockerImage = "quantconnect/lean:latest";
    public const string DefaultTimeoutSeconds = "45";
    public const string DefaultKeepWorkspace = "false";
    public const string DefaultManagedContainerName = "atrade-lean-engine";
    public const string DefaultContainerWorkspaceRoot = "/workspace";
    public const string DefaultWorkspaceRootRelativePath = "artifacts/lean-workspaces";

    public bool IsLeanSelected => string.Equals(AnalysisEngine, EngineLean, StringComparison.OrdinalIgnoreCase)
        || string.Equals(AnalysisEngine, "lean", StringComparison.OrdinalIgnoreCase);

    public bool IsDockerMode => string.Equals(RuntimeMode, RuntimeModeDocker, StringComparison.OrdinalIgnoreCase);

    public IReadOnlyDictionary<string, string> ToApiEnvironment() => new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
    {
        [AnalysisEngineVariableName] = AnalysisEngine,
        [RuntimeModeVariableName] = RuntimeMode,
        [CliCommandVariableName] = CliCommand,
        [DockerCommandVariableName] = DockerCommand,
        [DockerImageVariableName] = DockerImage,
        [WorkspaceRootVariableName] = WorkspaceRoot,
        [TimeoutSecondsVariableName] = TimeoutSeconds,
        [KeepWorkspaceVariableName] = KeepWorkspace,
        [ManagedContainerNameVariableName] = ManagedContainerName,
        [ContainerWorkspaceRootVariableName] = ContainerWorkspaceRoot,
    };

    public static LeanAnalysisRuntimeContract Load(string contractPath, string repositoryRoot)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(contractPath);
        ArgumentException.ThrowIfNullOrWhiteSpace(repositoryRoot);

        var values = LoadMergedContractValues(contractPath);
        var workspaceRoot = ResolveWorkspaceRoot(
            ResolveOptionalValue(values, WorkspaceRootVariableName),
            repositoryRoot);

        return new LeanAnalysisRuntimeContract(
            AnalysisEngine: ResolveOptionalValue(values, AnalysisEngineVariableName) ?? EngineNone,
            RuntimeMode: ResolveOptionalValue(values, RuntimeModeVariableName) ?? RuntimeModeCli,
            CliCommand: ResolveOptionalValue(values, CliCommandVariableName) ?? DefaultCliCommand,
            DockerCommand: ResolveOptionalValue(values, DockerCommandVariableName) ?? DefaultDockerCommand,
            DockerImage: ResolveOptionalValue(values, DockerImageVariableName) ?? DefaultDockerImage,
            WorkspaceRoot: workspaceRoot,
            TimeoutSeconds: ResolveOptionalValue(values, TimeoutSecondsVariableName) ?? DefaultTimeoutSeconds,
            KeepWorkspace: ResolveOptionalValue(values, KeepWorkspaceVariableName) ?? DefaultKeepWorkspace,
            ManagedContainerName: ResolveOptionalValue(values, ManagedContainerNameVariableName) ?? DefaultManagedContainerName,
            ContainerWorkspaceRoot: NormalizeContainerWorkspaceRoot(
                ResolveOptionalValue(values, ContainerWorkspaceRootVariableName) ?? DefaultContainerWorkspaceRoot));
    }

    public bool TryGetDockerImageReference(out string image, out string tag)
    {
        image = string.Empty;
        tag = string.Empty;

        if (!IsLeanSelected || !IsDockerMode || string.IsNullOrWhiteSpace(DockerImage))
        {
            return false;
        }

        var lastSlash = DockerImage.LastIndexOf('/');
        var lastColon = DockerImage.LastIndexOf(':');

        if (lastColon > lastSlash)
        {
            image = DockerImage[..lastColon];
            tag = DockerImage[(lastColon + 1)..];
            return true;
        }

        image = DockerImage;
        tag = "latest";
        return true;
    }

    private static string ResolveWorkspaceRoot(string? configuredWorkspaceRoot, string repositoryRoot)
    {
        var rawWorkspaceRoot = string.IsNullOrWhiteSpace(configuredWorkspaceRoot)
            ? DefaultWorkspaceRootRelativePath
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
            return DefaultContainerWorkspaceRoot;
        }

        return trimmed.StartsWith("/", StringComparison.Ordinal)
            ? trimmed
            : $"/{trimmed}";
    }

    private static Dictionary<string, string> LoadMergedContractValues(string contractPath)
    {
        var contractDirectory = Path.GetDirectoryName(contractPath)
            ?? throw new InvalidOperationException($"Failed to resolve the local LEAN runtime contract directory for '{contractPath}'.");
        var templatePath = Path.Combine(contractDirectory, ".env.template");
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        if (File.Exists(templatePath) &&
            !Path.GetFullPath(templatePath).Equals(Path.GetFullPath(contractPath), StringComparison.OrdinalIgnoreCase))
        {
            Overlay(values, ParseEnvironmentFile(templatePath));
        }

        Overlay(values, ParseEnvironmentFile(contractPath));
        return values;
    }

    private static void Overlay(IDictionary<string, string> destination, IReadOnlyDictionary<string, string> source)
    {
        foreach (var pair in source)
        {
            destination[pair.Key] = pair.Value;
        }
    }

    private static Dictionary<string, string> ParseEnvironmentFile(string path)
    {
        if (!File.Exists(path))
        {
            throw new InvalidOperationException($"Failed to load the local LEAN runtime contract file at '{path}'.");
        }

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

    private static string? ResolveOptionalValue(IReadOnlyDictionary<string, string> values, string key)
    {
        var environmentValue = Environment.GetEnvironmentVariable(key);
        if (!string.IsNullOrWhiteSpace(environmentValue))
        {
            return environmentValue.Trim();
        }

        return values.TryGetValue(key, out var fileValue) && !string.IsNullOrWhiteSpace(fileValue)
            ? fileValue.Trim()
            : null;
    }
}
