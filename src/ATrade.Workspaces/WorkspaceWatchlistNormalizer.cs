namespace ATrade.Workspaces;

internal static class WorkspaceWatchlistNormalizer
{
    public static NormalizedWorkspaceWatchlistSymbolInput Normalize(WorkspaceWatchlistSymbolInput input, int sortOrder = 0)
    {
        ArgumentNullException.ThrowIfNull(input);

        return new NormalizedWorkspaceWatchlistSymbolInput(
            WorkspaceSymbolNormalizer.Normalize(input.Symbol),
            NormalizeText(input.Provider) ?? WorkspaceWatchlistDefaults.ManualProvider,
            NormalizeText(input.ProviderSymbolId),
            input.IbkrConid,
            NormalizeText(input.Name),
            NormalizeText(input.Exchange)?.ToUpperInvariant(),
            NormalizeText(input.Currency)?.ToUpperInvariant() ?? WorkspaceWatchlistDefaults.DefaultCurrency,
            NormalizeText(input.AssetClass)?.ToUpperInvariant() ?? WorkspaceWatchlistDefaults.DefaultAssetClass,
            sortOrder);
    }

    public static IReadOnlyList<NormalizedWorkspaceWatchlistSymbolInput> NormalizeReplacement(IEnumerable<WorkspaceWatchlistSymbolInput> inputs)
    {
        ArgumentNullException.ThrowIfNull(inputs);

        var normalizedSymbols = new List<NormalizedWorkspaceWatchlistSymbolInput>();
        var seenSymbols = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var input in inputs)
        {
            var normalizedInput = Normalize(input, normalizedSymbols.Count);
            if (seenSymbols.Add(normalizedInput.Symbol))
            {
                normalizedSymbols.Add(normalizedInput);
            }
        }

        return normalizedSymbols;
    }

    private static string? NormalizeText(string? value)
    {
        var normalized = value?.Trim();
        return string.IsNullOrWhiteSpace(normalized) ? null : normalized;
    }
}
