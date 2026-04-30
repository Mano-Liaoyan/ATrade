using Microsoft.Extensions.Configuration;

namespace ATrade.Analysis.Lean;

public sealed class LeanAnalysisOptions
{
    public const string EngineId = "lean";
    public const string DefaultDisplayName = "LEAN analysis engine";
    public const string DefaultProvider = "LEAN";
    public const string DefaultVersion = "official-runtime";
    public const string DefaultCliCommand = "lean";
    public const string DefaultDockerCommand = "docker";
    public const string DefaultDockerImage = "quantconnect/lean:foundation";
    public const int DefaultTimeoutSeconds = 45;

    public string? SelectedAnalysisEngine { get; set; }

    public LeanRuntimeMode RuntimeMode { get; set; } = LeanRuntimeMode.Cli;

    public string CliCommand { get; set; } = DefaultCliCommand;

    public string DockerCommand { get; set; } = DefaultDockerCommand;

    public string DockerImage { get; set; } = DefaultDockerImage;

    public string? WorkspaceRoot { get; set; }

    public TimeSpan Timeout { get; set; } = TimeSpan.FromSeconds(DefaultTimeoutSeconds);

    public bool KeepWorkspace { get; set; }

    public bool IsLeanSelected => string.Equals(SelectedAnalysisEngine, EngineId, StringComparison.OrdinalIgnoreCase)
        || string.Equals(SelectedAnalysisEngine, DefaultProvider, StringComparison.OrdinalIgnoreCase);

    public string RuntimeDescription => RuntimeMode == LeanRuntimeMode.Docker
        ? $"official LEAN container image '{DockerImage}' via {DockerCommand}"
        : $"official LEAN CLI command '{CliCommand}'";

    public static LeanAnalysisOptions FromConfiguration(IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(configuration);

        var options = new LeanAnalysisOptions
        {
            SelectedAnalysisEngine = NullIfWhiteSpace(configuration[LeanAnalysisEnvironmentVariables.AnalysisEngine]),
        };

        if (Enum.TryParse<LeanRuntimeMode>(configuration[LeanAnalysisEnvironmentVariables.RuntimeMode], ignoreCase: true, out var runtimeMode))
        {
            options.RuntimeMode = runtimeMode;
        }

        options.CliCommand = NullIfWhiteSpace(configuration[LeanAnalysisEnvironmentVariables.CliCommand]) ?? DefaultCliCommand;
        options.DockerCommand = NullIfWhiteSpace(configuration[LeanAnalysisEnvironmentVariables.DockerCommand]) ?? DefaultDockerCommand;
        options.DockerImage = NullIfWhiteSpace(configuration[LeanAnalysisEnvironmentVariables.DockerImage]) ?? DefaultDockerImage;
        options.WorkspaceRoot = NullIfWhiteSpace(configuration[LeanAnalysisEnvironmentVariables.WorkspaceRoot]);

        var configuredTimeoutSeconds = configuration.GetValue<double?>(LeanAnalysisEnvironmentVariables.TimeoutSeconds);
        if (configuredTimeoutSeconds is > 0)
        {
            options.Timeout = TimeSpan.FromSeconds(configuredTimeoutSeconds.Value);
        }

        var configuredKeepWorkspace = configuration.GetValue<bool?>(LeanAnalysisEnvironmentVariables.KeepWorkspace);
        if (configuredKeepWorkspace.HasValue)
        {
            options.KeepWorkspace = configuredKeepWorkspace.Value;
        }

        return options;
    }

    private static string? NullIfWhiteSpace(string? value) => string.IsNullOrWhiteSpace(value)
        ? null
        : value.Trim();
}
