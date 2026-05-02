using ATrade.ServiceDefaults;

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
    public const string AnalysisEngineVariableName = LocalRuntimeEnvironmentVariables.AnalysisEngine;
    public const string RuntimeModeVariableName = LocalRuntimeEnvironmentVariables.LeanRuntimeMode;
    public const string CliCommandVariableName = LocalRuntimeEnvironmentVariables.LeanCliCommand;
    public const string DockerCommandVariableName = LocalRuntimeEnvironmentVariables.LeanDockerCommand;
    public const string DockerImageVariableName = LocalRuntimeEnvironmentVariables.LeanDockerImage;
    public const string WorkspaceRootVariableName = LocalRuntimeEnvironmentVariables.LeanWorkspaceRoot;
    public const string TimeoutSecondsVariableName = LocalRuntimeEnvironmentVariables.LeanTimeoutSeconds;
    public const string KeepWorkspaceVariableName = LocalRuntimeEnvironmentVariables.LeanKeepWorkspace;
    public const string ManagedContainerNameVariableName = LocalRuntimeEnvironmentVariables.LeanManagedContainerName;
    public const string ContainerWorkspaceRootVariableName = LocalRuntimeEnvironmentVariables.LeanContainerWorkspaceRoot;

    public const string EngineNone = LocalRuntimeContractDefaults.AnalysisEngine;
    public const string EngineLean = "Lean";
    public const string RuntimeModeCli = LocalRuntimeContractDefaults.LeanRuntimeMode;
    public const string RuntimeModeDocker = "docker";
    public const string DefaultCliCommand = LocalRuntimeContractDefaults.LeanCliCommand;
    public const string DefaultDockerCommand = LocalRuntimeContractDefaults.LeanDockerCommand;
    public const string DefaultDockerImage = LocalRuntimeContractDefaults.LeanDockerImage;
    public const string DefaultTimeoutSeconds = LocalRuntimeContractDefaults.LeanTimeoutSeconds;
    public const string DefaultKeepWorkspace = LocalRuntimeContractDefaults.LeanKeepWorkspace;
    public const string DefaultManagedContainerName = LocalRuntimeContractDefaults.LeanManagedContainerName;
    public const string DefaultContainerWorkspaceRoot = LocalRuntimeContractDefaults.LeanContainerWorkspaceRoot;
    public const string DefaultWorkspaceRootRelativePath = LocalRuntimeContractDefaults.LeanWorkspaceRoot;

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

        return Load(LocalRuntimeContractLoader.Load(new LocalRuntimeContractLoadOptions(
            RepositoryRoot: repositoryRoot,
            ContractPath: contractPath)));
    }

    public static LeanAnalysisRuntimeContract Load(LocalRuntimeContract runtimeContract)
    {
        ArgumentNullException.ThrowIfNull(runtimeContract);

        var lean = runtimeContract.Lean;
        return new LeanAnalysisRuntimeContract(
            AnalysisEngine: lean.AnalysisEngine,
            RuntimeMode: lean.RuntimeMode,
            CliCommand: lean.CliCommand,
            DockerCommand: lean.DockerCommand,
            DockerImage: lean.DockerImage,
            WorkspaceRoot: lean.WorkspaceRoot,
            TimeoutSeconds: lean.TimeoutSeconds,
            KeepWorkspace: lean.KeepWorkspace,
            ManagedContainerName: lean.ManagedContainerName,
            ContainerWorkspaceRoot: lean.ContainerWorkspaceRoot);
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
}
