using System.Text.Json;
using ATrade.Analysis;

namespace ATrade.Analysis.Lean;

public sealed record LeanPreparedWorkspace(
    string WorkspacePath,
    string ProjectName,
    string ProjectPath,
    string OutputDirectory,
    LeanInputData Input,
    bool ShouldDelete);

public interface ILeanAnalysisWorkspaceFactory
{
    Task<LeanPreparedWorkspace> CreateAsync(AnalysisRequest request, CancellationToken cancellationToken = default);

    void Cleanup(LeanPreparedWorkspace workspace);
}

public sealed class LeanAnalysisWorkspaceFactory(LeanAnalysisOptions options) : ILeanAnalysisWorkspaceFactory
{
    public const string ProjectName = "ATradeLeanAnalysis";

    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true,
    };

    public async Task<LeanPreparedWorkspace> CreateAsync(AnalysisRequest request, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        var input = LeanInputConverter.FromRequest(request);

        var workspacePath = CreateWorkspacePath();
        var projectPath = Path.Combine(workspacePath, ProjectName);
        var outputDirectory = Path.Combine(workspacePath, "output");

        Directory.CreateDirectory(projectPath);
        Directory.CreateDirectory(outputDirectory);

        await File.WriteAllTextAsync(Path.Combine(projectPath, LeanInputConverter.BarsFileName), LeanInputConverter.ToCsv(input), cancellationToken);
        await File.WriteAllTextAsync(Path.Combine(projectPath, "main.py"), LeanAlgorithmTemplate.Create(input), cancellationToken);
        await File.WriteAllTextAsync(Path.Combine(projectPath, "config.json"), CreateProjectConfig(), cancellationToken);

        return new LeanPreparedWorkspace(
            workspacePath,
            ProjectName,
            projectPath,
            outputDirectory,
            input,
            ShouldDelete: !options.KeepWorkspace);
    }

    public void Cleanup(LeanPreparedWorkspace workspace)
    {
        ArgumentNullException.ThrowIfNull(workspace);

        if (!workspace.ShouldDelete || !Directory.Exists(workspace.WorkspacePath))
        {
            return;
        }

        try
        {
            Directory.Delete(workspace.WorkspacePath, recursive: true);
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }

    private string CreateWorkspacePath()
    {
        var root = string.IsNullOrWhiteSpace(options.WorkspaceRoot)
            ? Path.Combine(Path.GetTempPath(), "atrade-lean-analysis")
            : options.WorkspaceRoot;

        var workspacePath = Path.Combine(root, $"run-{DateTimeOffset.UtcNow:yyyyMMddHHmmss}-{Guid.NewGuid():N}");
        Directory.CreateDirectory(workspacePath);
        return workspacePath;
    }

    private static string CreateProjectConfig()
    {
        var config = new Dictionary<string, object?>
        {
            ["algorithm-type-name"] = "ATradeLeanAnalysisAlgorithm",
            ["algorithm-language"] = "Python",
            ["algorithm-location"] = "main.py",
            ["parameters"] = new Dictionary<string, string>(),
        };

        return JsonSerializer.Serialize(config, JsonOptions);
    }
}
