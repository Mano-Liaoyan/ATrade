using System.ComponentModel;
using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace ATrade.Analysis.Lean;

public sealed class LeanRuntimeExecutor(
    LeanAnalysisOptions options,
    ILogger<LeanRuntimeExecutor> logger) : ILeanRuntimeExecutor
{
    private const string EngineWorkingDirectory = "/Lean/Launcher/bin/Debug";
    private const string EngineLauncherAssembly = "QuantConnect.Lean.Launcher.dll";
    private const string EngineConfigFileName = "lean-engine-config.json";
    private const string DisablePythonBytecodeEnvironment = "PYTHONDONTWRITEBYTECODE=1";

    private static readonly JsonSerializerOptions EngineConfigJsonOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true,
    };

    public async Task<LeanRuntimeExecutionResult> ExecuteAsync(LeanRuntimeExecutionRequest request, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        Directory.CreateDirectory(request.OutputDirectory);

        var command = BuildCommand(request);
        using var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = command.FileName,
                WorkingDirectory = request.WorkspacePath,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            },
        };

        foreach (var argument in command.Arguments)
        {
            process.StartInfo.ArgumentList.Add(argument);
        }

        try
        {
            if (!process.Start())
            {
                throw new LeanRuntimeUnavailableException($"Unable to start LEAN runtime command '{command.FileName}'.");
            }
        }
        catch (Win32Exception exception)
        {
            throw new LeanRuntimeUnavailableException($"LEAN runtime command '{command.FileName}' is not available. Install the official LEAN CLI or configure the Docker runtime before enabling LEAN analysis.", exception);
        }

        var standardOutput = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var standardError = process.StandardError.ReadToEndAsync(cancellationToken);

        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(request.Timeout);

        try
        {
            await process.WaitForExitAsync(timeout.Token);
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            TryKill(process);
            logger.LogWarning("LEAN runtime command timed out after {TimeoutSeconds} seconds.", request.Timeout.TotalSeconds);
            return new LeanRuntimeExecutionResult(
                ExitCode: -1,
                await CompleteReadAsync(standardOutput),
                await CompleteReadAsync(standardError),
                TimedOut: true);
        }

        return new LeanRuntimeExecutionResult(
            process.ExitCode,
            await standardOutput,
            await standardError,
            TimedOut: false);
    }

    private LeanRuntimeCommand BuildCommand(LeanRuntimeExecutionRequest request)
    {
        if (options.RuntimeMode == LeanRuntimeMode.Docker)
        {
            if (!options.UsesManagedDockerRuntime)
            {
                throw new LeanRuntimeUnavailableException(
                    $"LEAN Docker mode requires the AppHost-managed runtime setting {LeanAnalysisEnvironmentVariables.ManagedContainerName}; start through AppHost with LEAN Docker mode enabled or use CLI mode.");
            }

            var workspacePath = MapHostPathToManagedContainerPath(request.WorkspacePath);
            var outputDirectory = MapHostPathToManagedContainerPath(request.OutputDirectory);
            var engineConfigPath = PrepareManagedDockerEngineConfig(request, workspacePath, outputDirectory);

            return new LeanRuntimeCommand(
                options.DockerCommand,
                new[]
                {
                    "exec",
                    "-e",
                    DisablePythonBytecodeEnvironment,
                    "-w",
                    EngineWorkingDirectory,
                    options.ManagedContainerName!,
                    "dotnet",
                    EngineLauncherAssembly,
                    "--config",
                    engineConfigPath,
                });
        }

        EnsureLeanConfigurationAvailable(request.WorkspacePath);

        return new LeanRuntimeCommand(
            options.CliCommand,
            new[]
            {
                "backtest",
                request.ProjectName,
                "--output",
                request.OutputDirectory,
            });
    }

    private string PrepareManagedDockerEngineConfig(
        LeanRuntimeExecutionRequest request,
        string containerWorkspacePath,
        string containerOutputDirectory)
    {
        var engineConfigPath = Path.Combine(request.WorkspacePath, EngineConfigFileName);
        var containerProjectPath = CombineContainerPath(containerWorkspacePath, request.ProjectName);
        var containerConfig = CreateManagedDockerEngineConfig(containerProjectPath, containerOutputDirectory);
        File.WriteAllText(engineConfigPath, JsonSerializer.Serialize(containerConfig, EngineConfigJsonOptions));
        return MapHostPathToManagedContainerPath(engineConfigPath);
    }

    private static Dictionary<string, object?> CreateManagedDockerEngineConfig(string containerProjectPath, string containerOutputDirectory) => new()
    {
        ["environment"] = "backtesting",
        ["algorithm-type-name"] = "ATradeLeanAnalysisAlgorithm",
        ["algorithm-language"] = "Python",
        ["algorithm-location"] = CombineContainerPath(containerProjectPath, "main.py"),
        ["data-folder"] = "/Lean/Data/",
        ["debugging"] = false,
        ["debugging-method"] = "LocalCmdline",
        ["close-automatically"] = true,
        ["composer-dll-directory"] = ".",
        ["results-destination-folder"] = containerOutputDirectory,
        ["log-handler"] = "QuantConnect.Logging.CompositeLogHandler",
        ["messaging-handler"] = "QuantConnect.Messaging.Messaging",
        ["job-queue-handler"] = "QuantConnect.Queues.JobQueue",
        ["api-handler"] = "QuantConnect.Api.Api",
        ["map-file-provider"] = "QuantConnect.Data.Auxiliary.LocalDiskMapFileProvider",
        ["factor-file-provider"] = "QuantConnect.Data.Auxiliary.LocalDiskFactorFileProvider",
        ["data-provider"] = "QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider",
        ["data-channel-provider"] = "DataChannelProvider",
        ["object-store"] = "QuantConnect.Lean.Engine.Storage.LocalObjectStore",
        ["data-aggregator"] = "QuantConnect.Lean.Engine.DataFeeds.AggregationManager",
        ["show-missing-data-logs"] = false,
        ["force-exchange-always-open"] = false,
        ["transaction-log"] = string.Empty,
        ["job-user-id"] = "0",
        ["api-access-token"] = string.Empty,
        ["job-organization-id"] = string.Empty,
        ["parameters"] = new Dictionary<string, string>(),
        ["environments"] = new Dictionary<string, object?>
        {
            ["backtesting"] = new Dictionary<string, object?>
            {
                ["live-mode"] = false,
                ["setup-handler"] = "QuantConnect.Lean.Engine.Setup.BacktestingSetupHandler",
                ["result-handler"] = "QuantConnect.Lean.Engine.Results.BacktestingResultHandler",
                ["data-feed-handler"] = "QuantConnect.Lean.Engine.DataFeeds.FileSystemDataFeed",
                ["real-time-handler"] = "QuantConnect.Lean.Engine.RealTime.BacktestingRealTimeHandler",
                ["history-provider"] = new[] { "QuantConnect.Lean.Engine.HistoricalData.SubscriptionDataReaderHistoryProvider" },
                ["transaction-handler"] = "QuantConnect.Lean.Engine.TransactionHandlers.BacktestingTransactionHandler",
            },
        },
    };

    private void EnsureLeanConfigurationAvailable(string workspacePath)
    {
        if (FindLeanConfigPath(workspacePath) is not null)
        {
            return;
        }

        var configuredRoot = string.IsNullOrWhiteSpace(options.WorkspaceRoot)
            ? workspacePath
            : options.WorkspaceRoot;

        throw new LeanRuntimeUnavailableException(
            $"LEAN CLI backtests require an initialized LEAN workspace containing lean.json. Run `lean init` in '{Path.GetFullPath(configuredRoot)}' or set {LeanAnalysisEnvironmentVariables.WorkspaceRoot} to a directory at or under an existing initialized LEAN workspace.");
    }

    private static string? FindLeanConfigPath(string startPath)
    {
        var current = Directory.Exists(startPath)
            ? new DirectoryInfo(Path.GetFullPath(startPath))
            : Directory.GetParent(Path.GetFullPath(startPath));

        while (current is not null)
        {
            var leanConfigPath = Path.Combine(current.FullName, "lean.json");
            if (File.Exists(leanConfigPath))
            {
                return leanConfigPath;
            }

            current = current.Parent;
        }

        return null;
    }

    private string MapHostPathToManagedContainerPath(string hostPath)
    {
        if (string.IsNullOrWhiteSpace(options.WorkspaceRoot))
        {
            throw new LeanRuntimeUnavailableException(
                $"Managed LEAN Docker runtime requires {LeanAnalysisEnvironmentVariables.WorkspaceRoot} to map host workspaces into the container.");
        }

        var workspaceRoot = Path.GetFullPath(options.WorkspaceRoot);
        var fullHostPath = Path.GetFullPath(hostPath);
        var relativePath = Path.GetRelativePath(workspaceRoot, fullHostPath);

        if (IsOutsideWorkspaceRoot(relativePath))
        {
            throw new LeanRuntimeUnavailableException(
                $"Managed LEAN Docker runtime cannot execute workspace '{fullHostPath}' because it is outside the configured shared root '{workspaceRoot}'.");
        }

        if (string.Equals(relativePath, ".", StringComparison.Ordinal))
        {
            return options.ContainerWorkspaceRoot;
        }

        return CombineContainerPath(options.ContainerWorkspaceRoot, relativePath);
    }

    private static bool IsOutsideWorkspaceRoot(string relativePath) =>
        Path.IsPathRooted(relativePath) ||
        string.Equals(relativePath, "..", StringComparison.Ordinal) ||
        relativePath.StartsWith($"..{Path.DirectorySeparatorChar}", StringComparison.Ordinal) ||
        relativePath.StartsWith($"..{Path.AltDirectorySeparatorChar}", StringComparison.Ordinal);

    private static string CombineContainerPath(string root, string relativePath)
    {
        var normalizedRoot = root.Replace('\\', '/').TrimEnd('/');
        var normalizedRelativePath = ToContainerRelativePath(relativePath).TrimStart('/');
        return string.IsNullOrWhiteSpace(normalizedRelativePath)
            ? normalizedRoot
            : $"{normalizedRoot}/{normalizedRelativePath}";
    }

    private static string ToContainerRelativePath(string path) => path
        .Replace(Path.DirectorySeparatorChar, '/')
        .Replace(Path.AltDirectorySeparatorChar, '/');

    private static async Task<string> CompleteReadAsync(Task<string> readTask)
    {
        try
        {
            return await readTask;
        }
        catch (OperationCanceledException)
        {
            return string.Empty;
        }
    }

    private static void TryKill(Process process)
    {
        try
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
            }
        }
        catch (InvalidOperationException)
        {
        }
    }

    private sealed record LeanRuntimeCommand(string FileName, IReadOnlyList<string> Arguments);
}
