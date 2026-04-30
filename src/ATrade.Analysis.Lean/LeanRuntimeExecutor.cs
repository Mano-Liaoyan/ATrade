using System.ComponentModel;
using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace ATrade.Analysis.Lean;

public sealed class LeanRuntimeExecutor(
    LeanAnalysisOptions options,
    ILogger<LeanRuntimeExecutor> logger) : ILeanRuntimeExecutor
{
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

            return new LeanRuntimeCommand(
                options.DockerCommand,
                new[]
                {
                    "exec",
                    "-w",
                    workspacePath,
                    options.ManagedContainerName!,
                    options.CliCommand,
                    "backtest",
                    request.ProjectName,
                    "--output",
                    outputDirectory,
                });
        }

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
