namespace ATrade.Analysis;

public interface IAnalysisEngine
{
    AnalysisEngineMetadata Metadata { get; }

    AnalysisEngineCapabilities Capabilities { get; }

    ValueTask<AnalysisResult> AnalyzeAsync(AnalysisRequest request, CancellationToken cancellationToken = default);
}

public interface IAnalysisEngineRegistry
{
    IReadOnlyList<AnalysisEngineDescriptor> GetEngines();

    ValueTask<AnalysisResult> AnalyzeAsync(AnalysisRequest request, CancellationToken cancellationToken = default);
}
