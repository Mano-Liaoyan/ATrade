namespace ATrade.Analysis;

public sealed class AnalysisEngineRegistry(
    IEnumerable<IAnalysisEngine> engines,
    NoConfiguredAnalysisEngine noConfiguredAnalysisEngine) : IAnalysisEngineRegistry
{
    private readonly IReadOnlyList<IAnalysisEngine> configuredEngines = engines
        .Where(engine => engine is not NoConfiguredAnalysisEngine)
        .OrderBy(engine => engine.Metadata.EngineId, StringComparer.OrdinalIgnoreCase)
        .ToArray();

    public IReadOnlyList<AnalysisEngineDescriptor> GetEngines()
    {
        var enginesToDescribe = configuredEngines.Count == 0
            ? new[] { noConfiguredAnalysisEngine }
            : configuredEngines;

        return enginesToDescribe
            .Select(engine => new AnalysisEngineDescriptor(engine.Metadata, engine.Capabilities))
            .ToArray();
    }

    public ValueTask<AnalysisResult> AnalyzeAsync(AnalysisRequest request, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);

        var engine = ResolveEngine(request.EngineId);
        return engine.AnalyzeAsync(request, cancellationToken);
    }

    private IAnalysisEngine ResolveEngine(string? engineId)
    {
        if (configuredEngines.Count == 0)
        {
            return noConfiguredAnalysisEngine;
        }

        if (string.IsNullOrWhiteSpace(engineId))
        {
            return configuredEngines[0];
        }

        return configuredEngines.FirstOrDefault(engine => string.Equals(engine.Metadata.EngineId, engineId, StringComparison.OrdinalIgnoreCase))
            ?? noConfiguredAnalysisEngine;
    }
}
