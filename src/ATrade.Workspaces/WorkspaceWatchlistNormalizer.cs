using ATrade.MarketData;

namespace ATrade.Workspaces;

internal static class WorkspaceWatchlistNormalizer
{
    public static NormalizedWorkspaceWatchlistSymbolInput Normalize(WorkspaceWatchlistSymbolInput input, int sortOrder = 0)
    {
        ArgumentNullException.ThrowIfNull(input);

        var normalizedSymbol = WorkspaceSymbolNormalizer.Normalize(input.Symbol);
        var exactIdentity = ExactInstrumentIdentity.Create(
            normalizedSymbol,
            input.Provider,
            input.ProviderSymbolId,
            input.IbkrConid,
            input.Exchange,
            input.Currency,
            input.AssetClass);

        return new NormalizedWorkspaceWatchlistSymbolInput(
            exactIdentity.Symbol,
            exactIdentity.InstrumentKey,
            exactIdentity.Provider,
            exactIdentity.ProviderSymbolId,
            exactIdentity.IbkrConid,
            NormalizeText(input.Name),
            exactIdentity.Exchange,
            exactIdentity.Currency,
            exactIdentity.AssetClass,
            sortOrder);
    }

    public static IReadOnlyList<NormalizedWorkspaceWatchlistSymbolInput> NormalizeReplacement(IEnumerable<WorkspaceWatchlistSymbolInput> inputs)
    {
        ArgumentNullException.ThrowIfNull(inputs);

        var normalizedSymbols = new List<NormalizedWorkspaceWatchlistSymbolInput>();
        var indexByInstrumentKey = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        foreach (var input in inputs)
        {
            var normalizedInput = Normalize(input, normalizedSymbols.Count);
            var duplicateKey = normalizedInput.InstrumentKey;

            if (indexByInstrumentKey.TryGetValue(duplicateKey, out var duplicateIndex))
            {
                var merged = Merge(normalizedSymbols[duplicateIndex], normalizedInput);
                normalizedSymbols[duplicateIndex] = merged;
                indexByInstrumentKey[merged.InstrumentKey] = duplicateIndex;
                continue;
            }

            indexByInstrumentKey[duplicateKey] = normalizedSymbols.Count;
            normalizedSymbols.Add(normalizedInput);
        }

        return normalizedSymbols;
    }

    private static string? NormalizeText(string? value)
    {
        var normalized = value?.Trim();
        return string.IsNullOrWhiteSpace(normalized) ? null : normalized;
    }

    private static NormalizedWorkspaceWatchlistSymbolInput Merge(
        NormalizedWorkspaceWatchlistSymbolInput existing,
        NormalizedWorkspaceWatchlistSymbolInput candidate)
    {
        return existing with
        {
            Name = candidate.Name ?? existing.Name,
            SortOrder = existing.SortOrder,
        };
    }
}
