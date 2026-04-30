using System.Globalization;

namespace ATrade.Workspaces;

internal static class WorkspaceWatchlistInstrumentKey
{
    private const int MaxInstrumentKeyLength = 512;

    public static string Create(
        string symbol,
        string provider,
        string? providerSymbolId,
        long? ibkrConid,
        string? exchange,
        string? currency,
        string? assetClass)
    {
        return string.Join(
            '|',
            $"provider={EncodeSegment(provider.ToLowerInvariant())}",
            $"providerSymbolId={EncodeSegment(providerSymbolId)}",
            $"ibkrConid={EncodeSegment(ibkrConid?.ToString(CultureInfo.InvariantCulture))}",
            $"symbol={EncodeSegment(symbol.ToUpperInvariant())}",
            $"exchange={EncodeSegment(exchange?.ToUpperInvariant())}",
            $"currency={EncodeSegment((currency ?? WorkspaceWatchlistDefaults.DefaultCurrency).ToUpperInvariant())}",
            $"assetClass={EncodeSegment((assetClass ?? WorkspaceWatchlistDefaults.DefaultAssetClass).ToUpperInvariant())}");
    }

    public static string NormalizeExistingKey(string? instrumentKey)
    {
        var normalized = instrumentKey?.Trim();
        if (string.IsNullOrWhiteSpace(normalized))
        {
            throw new WorkspaceWatchlistValidationException(
                WorkspaceWatchlistErrorCodes.InvalidInstrumentKey,
                "An instrument key is required.");
        }

        if (normalized.Length > MaxInstrumentKeyLength)
        {
            throw new WorkspaceWatchlistValidationException(
                WorkspaceWatchlistErrorCodes.InvalidInstrumentKey,
                $"Instrument keys must be {MaxInstrumentKeyLength} characters or fewer.");
        }

        return normalized;
    }

    private static string EncodeSegment(string? value)
    {
        return Uri.EscapeDataString(value?.Trim() ?? string.Empty);
    }
}
