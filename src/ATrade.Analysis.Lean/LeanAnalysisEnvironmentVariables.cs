namespace ATrade.Analysis.Lean;

public static class LeanAnalysisEnvironmentVariables
{
    public const string AnalysisEngine = "ATRADE_ANALYSIS_ENGINE";
    public const string RuntimeMode = "ATRADE_LEAN_RUNTIME_MODE";
    public const string CliCommand = "ATRADE_LEAN_CLI_COMMAND";
    public const string DockerCommand = "ATRADE_LEAN_DOCKER_COMMAND";
    public const string DockerImage = "ATRADE_LEAN_DOCKER_IMAGE";
    public const string WorkspaceRoot = "ATRADE_LEAN_WORKSPACE_ROOT";
    public const string TimeoutSeconds = "ATRADE_LEAN_TIMEOUT_SECONDS";
    public const string KeepWorkspace = "ATRADE_LEAN_KEEP_WORKSPACE";
    public const string ManagedContainerName = "ATRADE_LEAN_MANAGED_CONTAINER_NAME";
    public const string ContainerWorkspaceRoot = "ATRADE_LEAN_CONTAINER_WORKSPACE_ROOT";
}
