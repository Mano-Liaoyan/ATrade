using System.Diagnostics;
using ATrade.Analysis;
using ATrade.Analysis.Lean;
using ATrade.MarketData;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;

namespace ATrade.Analysis.Lean.Tests;

public sealed class LeanAnalysisEngineTests
{
    [Fact]
    public void InputConverterSortsNormalizedBarsAndWritesLeanCsv()
    {
        var request = CreateRequest(barCount: 3, reverseBars: true);

        var input = LeanInputConverter.FromRequest(request);
        var csv = LeanInputConverter.ToCsv(input);

        Assert.Equal(request.Symbol, input.Symbol);
        Assert.Equal(MarketDataTimeframes.OneDay, input.Timeframe);
        Assert.Equal(input.Bars.OrderBy(bar => bar.TimeUtc).ToArray(), input.Bars);
        Assert.StartsWith("time,open,high,low,close,volume", csv, StringComparison.Ordinal);
        Assert.Contains("2026-04-01T00:00:00.0000000+00:00,100,101,99,100.5,1000000", csv, StringComparison.Ordinal);
    }

    [Fact]
    public void OptionsReadSafeLeanRuntimeConfiguration()
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                [LeanAnalysisEnvironmentVariables.AnalysisEngine] = "Lean",
                [LeanAnalysisEnvironmentVariables.RuntimeMode] = "Docker",
                [LeanAnalysisEnvironmentVariables.CliCommand] = "lean",
                [LeanAnalysisEnvironmentVariables.DockerImage] = "quantconnect/lean:latest",
                [LeanAnalysisEnvironmentVariables.WorkspaceRoot] = "/tmp/atrade-lean",
                [LeanAnalysisEnvironmentVariables.TimeoutSeconds] = "12",
                [LeanAnalysisEnvironmentVariables.KeepWorkspace] = "true",
                [LeanAnalysisEnvironmentVariables.ManagedContainerName] = "atrade-lean-engine",
                [LeanAnalysisEnvironmentVariables.ContainerWorkspaceRoot] = "workspace",
            })
            .Build();

        var options = LeanAnalysisOptions.FromConfiguration(configuration);

        Assert.True(options.IsLeanSelected);
        Assert.Equal(LeanRuntimeMode.Docker, options.RuntimeMode);
        Assert.Equal("lean", options.CliCommand);
        Assert.Equal("quantconnect/lean:latest", options.DockerImage);
        Assert.Equal("/tmp/atrade-lean", options.WorkspaceRoot);
        Assert.Equal(TimeSpan.FromSeconds(12), options.Timeout);
        Assert.True(options.KeepWorkspace);
        Assert.Equal("atrade-lean-engine", options.ManagedContainerName);
        Assert.Equal("/workspace", options.ContainerWorkspaceRoot);
        Assert.True(options.UsesManagedDockerRuntime);
    }

    [Fact]
    public void ServiceRegistrationKeepsNoEngineFallbackUntilLeanIsSelected()
    {
        var disabledRegistry = new ServiceCollection()
            .AddLogging()
            .AddAnalysisModule()
            .AddLeanAnalysisEngine(new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
            {
                [LeanAnalysisEnvironmentVariables.AnalysisEngine] = "none",
            }).Build())
            .BuildServiceProvider()
            .GetRequiredService<IAnalysisEngineRegistry>();

        Assert.Equal(NoConfiguredAnalysisEngine.EngineId, Assert.Single(disabledRegistry.GetEngines()).Metadata.EngineId);

        var enabledRegistry = new ServiceCollection()
            .AddLogging()
            .AddAnalysisModule()
            .AddLeanAnalysisEngine(new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
            {
                [LeanAnalysisEnvironmentVariables.AnalysisEngine] = "Lean",
                [LeanAnalysisEnvironmentVariables.TimeoutSeconds] = "1",
            }).Build())
            .BuildServiceProvider()
            .GetRequiredService<IAnalysisEngineRegistry>();

        var descriptor = Assert.Single(enabledRegistry.GetEngines());
        Assert.Equal(LeanAnalysisOptions.EngineId, descriptor.Metadata.EngineId);
        Assert.True(descriptor.Capabilities.SupportsBacktests);
        Assert.True(descriptor.Capabilities.RequiresExternalRuntime);
    }

    [Fact]
    public async Task RuntimeExecutorPreservesCliExecutionStrategy()
    {
        var command = CreateExecutableScript("printf '%s\\n' \"$@\"\n");
        var root = Directory.CreateTempSubdirectory("atrade-lean-cli-");
        WriteLeanConfig(root.FullName);
        var workspace = Path.Combine(root.FullName, "run-1");
        var output = Path.Combine(workspace, "output");
        Directory.CreateDirectory(output);
        var executor = new LeanRuntimeExecutor(
            new LeanAnalysisOptions
            {
                RuntimeMode = LeanRuntimeMode.Cli,
                CliCommand = command,
            },
            NullLogger<LeanRuntimeExecutor>.Instance);

        var result = await executor.ExecuteAsync(new LeanRuntimeExecutionRequest(
            workspace,
            LeanAnalysisWorkspaceFactory.ProjectName,
            output,
            TimeSpan.FromSeconds(5)));

        Assert.Equal(0, result.ExitCode);
        Assert.False(result.TimedOut);
        Assert.Equal(
            $"backtest\n{LeanAnalysisWorkspaceFactory.ProjectName}\n--output\n{output}\n",
            result.StandardOutput.ReplaceLineEndings("\n"));
    }

    [Fact]
    public async Task RuntimeExecutorRejectsCliModeWithoutLeanConfiguration()
    {
        var command = CreateExecutableScript("printf 'runtime should not be called'\n");
        var root = Directory.CreateTempSubdirectory("atrade-lean-no-config-");
        var workspace = Path.Combine(root.FullName, "run-1");
        var output = Path.Combine(workspace, "output");
        Directory.CreateDirectory(output);
        var executor = new LeanRuntimeExecutor(
            new LeanAnalysisOptions
            {
                RuntimeMode = LeanRuntimeMode.Cli,
                CliCommand = command,
                WorkspaceRoot = root.FullName,
            },
            NullLogger<LeanRuntimeExecutor>.Instance);

        var exception = await Assert.ThrowsAsync<LeanRuntimeUnavailableException>(() => executor.ExecuteAsync(new LeanRuntimeExecutionRequest(
            workspace,
            LeanAnalysisWorkspaceFactory.ProjectName,
            output,
            TimeSpan.FromSeconds(5))));

        Assert.Contains("lean.json", exception.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("lean init", exception.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Contains(LeanAnalysisEnvironmentVariables.WorkspaceRoot, exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task RuntimeExecutorUsesManagedDockerExecWithSharedWorkspaceMapping()
    {
        var command = CreateExecutableScript("printf '%s\\n' \"$@\"\n");
        var root = Directory.CreateTempSubdirectory("atrade-lean-managed-");
        WriteLeanConfig(root.FullName);
        var workspace = Path.Combine(root.FullName, "run-1");
        var output = Path.Combine(workspace, "output");
        Directory.CreateDirectory(output);
        var executor = new LeanRuntimeExecutor(
            new LeanAnalysisOptions
            {
                RuntimeMode = LeanRuntimeMode.Docker,
                DockerCommand = command,
                CliCommand = "lean",
                WorkspaceRoot = root.FullName,
                ManagedContainerName = "atrade-lean-engine",
                ContainerWorkspaceRoot = "/workspace",
            },
            NullLogger<LeanRuntimeExecutor>.Instance);

        var result = await executor.ExecuteAsync(new LeanRuntimeExecutionRequest(
            workspace,
            LeanAnalysisWorkspaceFactory.ProjectName,
            output,
            TimeSpan.FromSeconds(5)));

        Assert.Equal(0, result.ExitCode);
        Assert.False(result.TimedOut);
        Assert.Equal(
            "exec\n-e\nPYTHONDONTWRITEBYTECODE=1\n-w\n/Lean/Launcher/bin/Debug\natrade-lean-engine\ndotnet\nQuantConnect.Lean.Launcher.dll\n--config\n/workspace/run-1/lean-engine-config.json\n",
            result.StandardOutput.ReplaceLineEndings("\n"));

        var engineConfig = File.ReadAllText(Path.Combine(workspace, "lean-engine-config.json"));
        Assert.Contains("\"algorithm-location\": \"/workspace/run-1/ATradeLeanAnalysis/main.py\"", engineConfig, StringComparison.Ordinal);
        Assert.Contains("\"live-mode\": false", engineConfig, StringComparison.Ordinal);
    }

    [Fact]
    public async Task RuntimeExecutorRejectsDockerModeWithoutManagedContainer()
    {
        var command = CreateExecutableScript("printf 'runtime should not be called'\n");
        var root = Directory.CreateTempSubdirectory("atrade-lean-unmanaged-");
        var workspace = Path.Combine(root.FullName, "run-1");
        var output = Path.Combine(workspace, "output");
        Directory.CreateDirectory(output);
        var executor = new LeanRuntimeExecutor(
            new LeanAnalysisOptions
            {
                RuntimeMode = LeanRuntimeMode.Docker,
                DockerCommand = command,
                WorkspaceRoot = root.FullName,
            },
            NullLogger<LeanRuntimeExecutor>.Instance);

        var exception = await Assert.ThrowsAsync<LeanRuntimeUnavailableException>(() => executor.ExecuteAsync(new LeanRuntimeExecutionRequest(
            workspace,
            LeanAnalysisWorkspaceFactory.ProjectName,
            output,
            TimeSpan.FromSeconds(5))));

        Assert.Contains(LeanAnalysisEnvironmentVariables.ManagedContainerName, exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task EngineReturnsUnavailableWhenManagedDockerContainerIsUnavailable()
    {
        var command = CreateExecutableScript("printf 'No such container: atrade-lean-engine\\n' >&2\nexit 1\n");
        var root = Directory.CreateTempSubdirectory("atrade-lean-missing-container-");
        WriteLeanConfig(root.FullName);
        var options = new LeanAnalysisOptions
        {
            SelectedAnalysisEngine = "Lean",
            RuntimeMode = LeanRuntimeMode.Docker,
            DockerCommand = command,
            WorkspaceRoot = root.FullName,
            ManagedContainerName = "atrade-lean-engine",
            ContainerWorkspaceRoot = "/workspace",
            Timeout = TimeSpan.FromSeconds(5),
        };
        var engine = new LeanAnalysisEngine(
            options,
            new LeanRuntimeExecutor(options, NullLogger<LeanRuntimeExecutor>.Instance),
            new LeanAnalysisWorkspaceFactory(options),
            NullLogger<LeanAnalysisEngine>.Instance);

        var result = await engine.AnalyzeAsync(CreateRequest(barCount: 25));

        Assert.Equal(AnalysisResultStatuses.Failed, result.Status);
        Assert.Equal(AnalysisEngineErrorCodes.EngineUnavailable, result.Error?.Code);
        Assert.Contains("No such container", result.Error?.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Empty(result.Signals);
        Assert.Empty(result.Metrics);
        Assert.Null(result.Backtest);
    }

    [Fact]
    public void ParserMapsLeanMarkerPayloadToProviderNeutralResult()
    {
        var request = CreateRequest(barCount: 25);
        var input = LeanInputConverter.FromRequest(request);
        var execution = new LeanRuntimeExecutionResult(
            0,
            "noise\nATRADE_ANALYSIS_RESULT:{\"generatedAtUtc\":\"2026-04-30T10:00:00Z\",\"signals\":[{\"time\":\"2026-04-25T00:00:00Z\",\"kind\":\"moving-average-crossover\",\"direction\":\"bullish\",\"confidence\":0.72,\"rationale\":\"cross\"}],\"metrics\":[{\"name\":\"total-return\",\"value\":12.34,\"unit\":\"percent\"}],\"backtest\":{\"startUtc\":\"2026-04-01T00:00:00Z\",\"endUtc\":\"2026-04-25T00:00:00Z\",\"initialCapital\":100000,\"finalEquity\":112340,\"totalReturnPercent\":12.34,\"tradeCount\":1,\"winRatePercent\":100}}",
            string.Empty,
            TimedOut: false);

        var result = LeanAnalysisResultParser.Parse(
            execution,
            request,
            input,
            CreateMetadata(),
            new AnalysisDataSource("LEAN", "unit-test", DateTimeOffset.UtcNow));

        Assert.Equal(AnalysisResultStatuses.Completed, result.Status);
        Assert.Equal(LeanAnalysisOptions.EngineId, result.Engine.EngineId);
        Assert.Equal(request.Symbol, result.Symbol);
        Assert.Equal("moving-average-crossover", Assert.Single(result.Signals).Kind);
        Assert.Equal("total-return", Assert.Single(result.Metrics).Name);
        Assert.Equal(112340m, result.Backtest?.FinalEquity);
        Assert.Null(result.Error);
    }

    [Fact]
    public async Task EngineReturnsUnavailableResultWhenLeanRuntimeTimesOut()
    {
        var options = new LeanAnalysisOptions
        {
            SelectedAnalysisEngine = "Lean",
            Timeout = TimeSpan.FromSeconds(1),
        };
        var engine = new LeanAnalysisEngine(
            options,
            new FakeLeanRuntimeExecutor(_ => new LeanRuntimeExecutionResult(-1, string.Empty, string.Empty, TimedOut: true)),
            new LeanAnalysisWorkspaceFactory(options),
            NullLogger<LeanAnalysisEngine>.Instance);

        var result = await engine.AnalyzeAsync(CreateRequest(barCount: 25));

        Assert.Equal(AnalysisResultStatuses.Failed, result.Status);
        Assert.Equal(AnalysisEngineErrorCodes.EngineUnavailable, result.Error?.Code);
        Assert.Contains("timed out", result.Error?.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task EngineIncludesRuntimeStandardOutputOnFailure()
    {
        var options = new LeanAnalysisOptions
        {
            SelectedAnalysisEngine = "Lean",
            RuntimeMode = LeanRuntimeMode.Cli,
            Timeout = TimeSpan.FromSeconds(1),
        };
        var engine = new LeanAnalysisEngine(
            options,
            new FakeLeanRuntimeExecutor(_ => new LeanRuntimeExecutionResult(
                1,
                "This command requires a Lean configuration file, run `lean init` in an empty directory to create one.",
                string.Empty,
                TimedOut: false)),
            new LeanAnalysisWorkspaceFactory(options),
            NullLogger<LeanAnalysisEngine>.Instance);

        var result = await engine.AnalyzeAsync(CreateRequest(barCount: 25));

        Assert.Equal(AnalysisResultStatuses.Failed, result.Status);
        Assert.Equal(AnalysisEngineErrorCodes.EngineUnavailable, result.Error?.Code);
        Assert.Contains("stdout:", result.Error?.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("lean init", result.Error?.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("lean.json", result.Error?.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task EngineExplainsCommandNotFoundRuntimeExit()
    {
        var options = new LeanAnalysisOptions
        {
            SelectedAnalysisEngine = "Lean",
            RuntimeMode = LeanRuntimeMode.Docker,
            CliCommand = "lean",
            DockerImage = "quantconnect/lean:latest",
            ManagedContainerName = "atrade-lean-engine",
            Timeout = TimeSpan.FromSeconds(1),
        };
        var engine = new LeanAnalysisEngine(
            options,
            new FakeLeanRuntimeExecutor(_ => new LeanRuntimeExecutionResult(127, string.Empty, string.Empty, TimedOut: false)),
            new LeanAnalysisWorkspaceFactory(options),
            NullLogger<LeanAnalysisEngine>.Instance);

        var result = await engine.AnalyzeAsync(CreateRequest(barCount: 25));

        Assert.Equal(AnalysisResultStatuses.Failed, result.Status);
        Assert.Equal(AnalysisEngineErrorCodes.EngineUnavailable, result.Error?.Code);
        Assert.Contains("command not found", result.Error?.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("engine image", result.Error?.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Contains(LeanAnalysisEnvironmentVariables.DockerImage, result.Error?.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task EngineReturnsProviderNeutralResultFromLeanRuntimeMarker()
    {
        var options = new LeanAnalysisOptions
        {
            SelectedAnalysisEngine = "Lean",
            Timeout = TimeSpan.FromSeconds(1),
        };
        var engine = new LeanAnalysisEngine(
            options,
            new FakeLeanRuntimeExecutor(_ => new LeanRuntimeExecutionResult(
                0,
                "ATRADE_ANALYSIS_RESULT:{\"generatedAtUtc\":\"2026-04-30T10:00:00Z\",\"signals\":[],\"metrics\":[{\"name\":\"signal-count\",\"value\":0,\"unit\":\"count\"}],\"backtest\":{\"startUtc\":\"2026-04-01T00:00:00Z\",\"endUtc\":\"2026-04-25T00:00:00Z\",\"initialCapital\":100000,\"finalEquity\":101000,\"totalReturnPercent\":1,\"tradeCount\":0,\"winRatePercent\":0}}",
                string.Empty,
                TimedOut: false)),
            new LeanAnalysisWorkspaceFactory(options),
            NullLogger<LeanAnalysisEngine>.Instance);

        var result = await engine.AnalyzeAsync(CreateRequest(barCount: 25));

        Assert.Equal(AnalysisResultStatuses.Completed, result.Status);
        Assert.Equal("signal-count", Assert.Single(result.Metrics).Name);
        Assert.Equal(101000m, result.Backtest?.FinalEquity);
        Assert.Null(result.Error);
    }

    [Fact]
    public async Task EngineReturnsInvalidRequestForEmptyBars()
    {
        var options = new LeanAnalysisOptions { SelectedAnalysisEngine = "Lean" };
        var engine = new LeanAnalysisEngine(
            options,
            new FakeLeanRuntimeExecutor(_ => throw new InvalidOperationException("runtime should not be called")),
            new LeanAnalysisWorkspaceFactory(options),
            NullLogger<LeanAnalysisEngine>.Instance);

        var result = await engine.AnalyzeAsync(CreateRequest(barCount: 0));

        Assert.Equal(AnalysisResultStatuses.Failed, result.Status);
        Assert.Equal(AnalysisEngineErrorCodes.InvalidRequest, result.Error?.Code);
    }

    [Fact]
    public void AlgorithmTemplateStaysAnalysisOnlyAndRejectsTradingCalls()
    {
        var algorithm = LeanAlgorithmTemplate.Create(LeanInputConverter.FromRequest(CreateRequest(barCount: 25)));

        Assert.DoesNotContain("MarketOrder(", algorithm, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("SetBrokerageModel", algorithm, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("/api/orders", algorithm, StringComparison.OrdinalIgnoreCase);
        Assert.Throws<LeanAnalysisOnlyViolationException>(() => LeanAnalysisGuardrails.EnsureAnalysisOnly("self.MarketOrder(\"SPY\", 1)"));
    }

    private static AnalysisEngineMetadata CreateMetadata() => new(
        LeanAnalysisOptions.EngineId,
        LeanAnalysisOptions.DefaultDisplayName,
        LeanAnalysisOptions.DefaultProvider,
        LeanAnalysisOptions.DefaultVersion,
        AnalysisEngineStates.Available);

    private static void WriteLeanConfig(string directory) => File.WriteAllText(Path.Combine(directory, "lean.json"), "{}\n");

    private static string CreateExecutableScript(string body)
    {
        if (OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("LEAN runtime executor command-construction tests require a Unix-like shell.");
        }

        var directory = Directory.CreateTempSubdirectory("atrade-lean-runtime-command-");
        var path = Path.Combine(directory.FullName, "fake-runtime.sh");
        File.WriteAllText(path, $"#!/usr/bin/env bash\nset -euo pipefail\n{body}");

        var chmodStartInfo = new ProcessStartInfo
        {
            FileName = "chmod",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        chmodStartInfo.ArgumentList.Add("+x");
        chmodStartInfo.ArgumentList.Add(path);
        using var chmod = Process.Start(chmodStartInfo);
        chmod?.WaitForExit();
        if (chmod is null || chmod.ExitCode != 0)
        {
            throw new InvalidOperationException($"Failed to make fake runtime command executable at '{path}'.");
        }

        return path;
    }

    private static AnalysisRequest CreateRequest(int barCount, bool reverseBars = false)
    {
        var bars = Enumerable.Range(0, barCount)
            .Select(index => new OhlcvCandle(
                new DateTimeOffset(2026, 4, 1, 0, 0, 0, TimeSpan.Zero).AddDays(index),
                Open: 100m + index,
                High: 101m + index,
                Low: 99m + index,
                Close: 100.5m + index,
                Volume: 1_000_000 + index))
            .ToArray();

        if (reverseBars)
        {
            Array.Reverse(bars);
        }

        return new AnalysisRequest(
            new MarketDataSymbolIdentity("AAPL", "ibkr", "265598", MarketDataAssetClasses.Stock, "NASDAQ", "USD"),
            MarketDataTimeframes.OneDay,
            DateTimeOffset.UtcNow,
            bars,
            EngineId: LeanAnalysisOptions.EngineId,
            StrategyName: "unit-test-moving-average-crossover");
    }

    private sealed class FakeLeanRuntimeExecutor(Func<LeanRuntimeExecutionRequest, LeanRuntimeExecutionResult> execute) : ILeanRuntimeExecutor
    {
        public Task<LeanRuntimeExecutionResult> ExecuteAsync(LeanRuntimeExecutionRequest request, CancellationToken cancellationToken = default) =>
            Task.FromResult(execute(request));
    }
}
