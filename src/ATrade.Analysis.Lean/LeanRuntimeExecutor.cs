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
        var projectOutput = Path.GetRelativePath(request.WorkspacePath, request.OutputDirectory).Replace(Path.DirectorySeparatorChar, '/');
        if (options.RuntimeMode == LeanRuntimeMode.Docker)
        {
            return new LeanRuntimeCommand(
                options.DockerCommand,
                new[]
                {
                    "run",
                    "--rm",
                    "-v",
                    $"{request.WorkspacePath}:/workspace",
                    "-w",
                    "/workspace",
                    options.DockerImage,
                    options.CliCommand,
                    "backtest",
                    request.ProjectName,
                    "--output",
                    $"/workspace/{projectOutput}",
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
