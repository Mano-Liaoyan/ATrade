using System.Globalization;

namespace ATrade.Workspaces;

internal static class WorkspaceWatchlistNormalizer
{
    public static NormalizedWorkspaceWatchlistSymbolInput Normalize(WorkspaceWatchlistSymbolInput input, int sortOrder = 0)
    {
        ArgumentNullException.ThrowIfNull(input);

        var normalizedSymbol = WorkspaceSymbolNormalizer.Normalize(input.Symbol);
        var normalizedProvider = NormalizeProvider(input.Provider, input.IbkrConid);
        var normalizedProviderSymbolId = NormalizeText(input.ProviderSymbolId)
            ?? (input.IbkrConid.HasValue ? input.IbkrConid.Value.ToString(CultureInfo.InvariantCulture) : null);
        var normalizedExchange = NormalizeText(input.Exchange)?.ToUpperInvariant();
        var normalizedCurrency = NormalizeText(input.Currency)?.ToUpperInvariant() ?? WorkspaceWatchlistDefaults.DefaultCurrency;
        var normalizedAssetClass = NormalizeText(input.AssetClass)?.ToUpperInvariant() ?? WorkspaceWatchlistDefaults.DefaultAssetClass;
        var instrumentKey = WorkspaceWatchlistInstrumentKey.Create(
            normalizedSymbol,
            normalizedProvider,
            normalizedProviderSymbolId,
            input.IbkrConid,
            normalizedExchange,
            normalizedCurrency,
            normalizedAssetClass);

        return new NormalizedWorkspaceWatchlistSymbolInput(
            normalizedSymbol,
            instrumentKey,
            normalizedProvider,
            normalizedProviderSymbolId,
            input.IbkrConid,
            NormalizeText(input.Name),
            normalizedExchange,
            normalizedCurrency,
            normalizedAssetClass,
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

    private static string NormalizeProvider(string? provider, long? ibkrConid)
    {
        var normalized = NormalizeText(provider)?.ToLowerInvariant();
        if (!string.IsNullOrWhiteSpace(normalized))
        {
            return normalized;
        }

        return ibkrConid.HasValue ? WorkspaceWatchlistDefaults.IbkrProvider : WorkspaceWatchlistDefaults.ManualProvider;
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
