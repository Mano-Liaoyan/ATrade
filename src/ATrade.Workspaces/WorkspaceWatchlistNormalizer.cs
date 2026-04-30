using System.Globalization;

namespace ATrade.Workspaces;

internal static class WorkspaceWatchlistNormalizer
{
    public static NormalizedWorkspaceWatchlistSymbolInput Normalize(WorkspaceWatchlistSymbolInput input, int sortOrder = 0)
    {
        ArgumentNullException.ThrowIfNull(input);

        var normalizedProvider = NormalizeProvider(input.Provider, input.IbkrConid);
        var normalizedProviderSymbolId = NormalizeText(input.ProviderSymbolId)
            ?? (input.IbkrConid.HasValue ? input.IbkrConid.Value.ToString(CultureInfo.InvariantCulture) : null);

        return new NormalizedWorkspaceWatchlistSymbolInput(
            WorkspaceSymbolNormalizer.Normalize(input.Symbol),
            normalizedProvider,
            normalizedProviderSymbolId,
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
        var indexByDuplicateKey = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        var indexBySymbol = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        foreach (var input in inputs)
        {
            var normalizedInput = Normalize(input, normalizedSymbols.Count);
            var duplicateKey = GetDuplicateKey(normalizedInput);

            if (indexByDuplicateKey.TryGetValue(duplicateKey, out var duplicateIndex)
                || indexBySymbol.TryGetValue(normalizedInput.Symbol, out duplicateIndex))
            {
                var merged = Merge(normalizedSymbols[duplicateIndex], normalizedInput);
                normalizedSymbols[duplicateIndex] = merged;
                indexByDuplicateKey[GetDuplicateKey(merged)] = duplicateIndex;
                indexBySymbol[merged.Symbol] = duplicateIndex;
                continue;
            }

            indexByDuplicateKey[duplicateKey] = normalizedSymbols.Count;
            indexBySymbol[normalizedInput.Symbol] = normalizedSymbols.Count;
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

    private static string GetDuplicateKey(NormalizedWorkspaceWatchlistSymbolInput symbol)
    {
        if (!string.IsNullOrWhiteSpace(symbol.Provider) && !string.IsNullOrWhiteSpace(symbol.ProviderSymbolId))
        {
            return $"provider:{symbol.Provider}:id:{symbol.ProviderSymbolId.Trim().ToUpperInvariant()}";
        }

        if (!string.IsNullOrWhiteSpace(symbol.Provider) && symbol.IbkrConid.HasValue)
        {
            return $"provider:{symbol.Provider}:ibkr-conid:{symbol.IbkrConid.Value.ToString(CultureInfo.InvariantCulture)}";
        }

        return $"symbol:{symbol.Symbol}";
    }

    private static NormalizedWorkspaceWatchlistSymbolInput Merge(
        NormalizedWorkspaceWatchlistSymbolInput existing,
        NormalizedWorkspaceWatchlistSymbolInput candidate)
    {
        var candidateHasProviderIdentity = HasProviderIdentity(candidate);
        return existing with
        {
            Provider = candidateHasProviderIdentity ? candidate.Provider : existing.Provider,
            ProviderSymbolId = candidate.ProviderSymbolId ?? existing.ProviderSymbolId,
            IbkrConid = candidate.IbkrConid ?? existing.IbkrConid,
            Name = candidate.Name ?? existing.Name,
            Exchange = candidate.Exchange ?? existing.Exchange,
            Currency = candidate.Currency ?? existing.Currency,
            AssetClass = candidate.AssetClass ?? existing.AssetClass,
        };
    }

    private static bool HasProviderIdentity(NormalizedWorkspaceWatchlistSymbolInput symbol)
    {
        return !string.Equals(symbol.Provider, WorkspaceWatchlistDefaults.ManualProvider, StringComparison.OrdinalIgnoreCase)
            || !string.IsNullOrWhiteSpace(symbol.ProviderSymbolId)
            || symbol.IbkrConid.HasValue;
    }
}
